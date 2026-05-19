"""
telegram_handler.py — Handler del Bot de Telegram vía n8n
¿Dónde comemos hoy?

Este módulo procesa los mensajes que llegan desde n8n (el bot de Telegram)
y gestiona el flujo conversacional para recoger el perfil de cada integrante
del grupo y lanzar la recomendación.

── Cómo conectar con n8n ────────────────────────────────────────────────────

1. En n8n, crea un flujo:
   [Telegram Trigger] → [HTTP Request → /telegram/mensaje] → [Telegram → enviar respuesta]

2. El nodo "HTTP Request" hace POST a:
   http://TU_SERVIDOR:5000/telegram/mensaje

3. Body del POST (n8n lo arma automáticamente con el trigger de Telegram):
   {
     "chat_id":    {{ $json.message.chat.id }},
     "user_id":    {{ $json.message.from.id }},
     "username":   {{ $json.message.from.first_name }},
     "texto":      {{ $json.message.text }}
   }

4. La respuesta incluye:
   {
     "respuesta": "Texto para enviar al usuario",
     "sesion_id": "uuid",
     "listo": true/false
   }

5. Conecta la respuesta al nodo "Telegram → Send Message" con:
   Chat ID:  {{ $json.chat_id }}
   Text:     {{ $json.respuesta }}

── Flujo conversacional ──────────────────────────────────────────────────────

INICIO → NOMBRE → PICANTE → DULCE → SALADO → VEGETARIANO → CARNE
      → PRESUPUESTO → RESTRICCIONES → ESPERAR_GRUPO → RECOMENDAR

"""

import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, request, jsonify, Blueprint
from core.motor_recomendacion import MotorRecomendacionGrupal, PerfilUsuario, DIMS
from data.base_datos import (
    cargar_restaurantes, crear_grupo, agregar_miembro_grupo,
    guardar_recomendacion, obtener_o_crear_usuario, guardar_sesion
)

telegram_bp = Blueprint('telegram', __name__)

# ─────────────────────────────────────────────────────────────────
# ESTADO DE SESIONES EN MEMORIA
# (En producción, usar Redis o la tabla sesiones de Supabase)
# ─────────────────────────────────────────────────────────────────
_sesiones: dict[int, dict] = {}  # chat_id → estado de conversación

PASOS = [
    'inicio', 'recoger_nombre_grupo', 'recoger_integrantes',
    'recoger_perfil_picante', 'recoger_perfil_dulce', 'recoger_perfil_salado',
    'recoger_perfil_vegetariano', 'recoger_perfil_carne',
    'recoger_presupuesto', 'recoger_restricciones',
    'confirmar_integrante', 'mas_integrantes', 'recomendar', 'listo'
]

EMOJIS_DIMS = {
    'picante': '🌶️', 'dulce': '🍰', 'salado': '🧂',
    'vegetariano': '🥗', 'carne': '🥩'
}

# ─────────────────────────────────────────────────────────────────
# PROCESADOR DE MENSAJES
# ─────────────────────────────────────────────────────────────────

def procesar_mensaje(chat_id: int, user_id: int, username: str, texto: str) -> dict:
    """
    Procesa un mensaje de Telegram y retorna la respuesta a enviar.

    Returns:
        {respuesta: str, listo: bool, datos_para_recomendar: dict|None}
    """
    texto = texto.strip()

    # Obtener o crear sesión
    if chat_id not in _sesiones or texto.lower() in ['/start', '/nuevo', 'nuevo']:
        _sesiones[chat_id] = _nueva_sesion(chat_id)

    sesion = _sesiones[chat_id]
    paso = sesion['paso']

    # ── Comandos globales ──────────────────────────────────────
    if texto.lower() == '/ayuda':
        return _resp(_ayuda(), chat_id)
    if texto.lower() == '/cancelar':
        del _sesiones[chat_id]
        return _resp("❌ Sesión cancelada. Escribe /start para comenzar de nuevo.", chat_id)

    # ── Máquina de estados ─────────────────────────────────────
    if paso == 'inicio':
        sesion['paso'] = 'recoger_nombre_grupo'
        return _resp(
            "🍽️ *¡Bienvenidos a ¿Dónde comemos hoy?!*\n\n"
            "Los ayudo a encontrar el restaurante perfecto para el grupo.\n\n"
            "📝 ¿Cómo se llama el grupo o cuál es la ocasión?\n"
            "_Ej: Almuerzo de trabajo, Cumpleaños de Sofía, Los de siempre..._",
            chat_id
        )

    elif paso == 'recoger_nombre_grupo':
        sesion['nombre_grupo'] = texto
        sesion['integrantes'] = []
        sesion['integrante_actual'] = {}
        sesion['paso'] = 'recoger_integrantes'
        return _resp(
            f"✅ Grupo: *{texto}*\n\n"
            f"👥 ¿Cuántas personas van? _(mínimo 1, máximo 8)_",
            chat_id
        )

    elif paso == 'recoger_integrantes':
        try:
            n = int(texto)
            assert 1 <= n <= 8
        except:
            return _resp("Por favor escribe un número entre 1 y 8 🙏", chat_id)
        sesion['num_integrantes'] = n
        sesion['paso'] = 'recoger_perfil_nombre'
        return _resp(
            f"Perfecto, {n} persona(s) 👍\n\n"
            f"*Integrante 1 de {n}*\n"
            f"¿Cuál es su nombre?",
            chat_id
        )

    elif paso == 'recoger_perfil_nombre':
        sesion['integrante_actual'] = {'nombre': texto, 'vector': [], 'restricciones': []}
        sesion['paso'] = 'recoger_perfil_picante'
        return _resp(
            f"Hola *{texto}* 👋\n\n"
            f"Voy a hacerte {len(DIMS)} preguntas rápidas sobre tus gustos.\n"
            f"Responde con un número del *1 al 10*.\n\n"
            f"🌶️ ¿Cuánto te gusta lo *picante*?\n"
            f"_1 = nada de picante · 10 = entre más pique mejor_",
            chat_id
        )

    elif paso in ['recoger_perfil_picante', 'recoger_perfil_dulce', 'recoger_perfil_salado',
                  'recoger_perfil_vegetariano', 'recoger_perfil_carne']:
        try:
            val = float(texto.replace(',', '.'))
            assert 1 <= val <= 10
        except:
            dim_actual = paso.replace('recoger_perfil_', '')
            return _resp(f"Por favor escribe un número entre 1 y 10 {EMOJIS_DIMS.get(dim_actual, '')} 🙏", chat_id)

        sesion['integrante_actual']['vector'].append(round(val, 1))
        idx = len(sesion['integrante_actual']['vector']) - 1
        preguntas_siguientes = {
            'recoger_perfil_picante':     ('recoger_perfil_dulce',       f"🍰 ¿Qué tanto disfrutas sabores *dulces*?\n_1 = no me llama · 10 = me encanta_"),
            'recoger_perfil_dulce':       ('recoger_perfil_salado',      f"🧂 ¿Te gustan las comidas *saladas e intensas*?\n_1 = prefiero suave · 10 = muy sazonado_"),
            'recoger_perfil_salado':      ('recoger_perfil_vegetariano', f"🥗 ¿Qué tan importante es para ti tener *opciones vegetarianas* o con muchos vegetales?\n_1 = no me importa · 10 = muy importante_"),
            'recoger_perfil_vegetariano': ('recoger_perfil_carne',       f"🥩 ¿Cuánto disfrutas la *carne* (res, pollo, cerdo)?\n_1 = no como carne · 10 = soy carnívoro_"),
            'recoger_perfil_carne':       ('recoger_presupuesto',        None),
        }
        siguiente_paso, preg_sig = preguntas_siguientes[paso]
        sesion['paso'] = siguiente_paso

        if siguiente_paso == 'recoger_presupuesto':
            return _resp(
                f"💰 ¿Cuánto estás dispuesto a gastar por persona?\n"
                f"_Escribe solo el número en pesos COP_\n"
                f"_Ej: 20000 · 35000 · 50000_",
                chat_id
            )
        return _resp(preg_sig, chat_id)

    elif paso == 'recoger_presupuesto':
        try:
            presupuesto = int(texto.replace('.', '').replace(',', '').replace('$', '').strip())
            assert presupuesto >= 5000
        except:
            return _resp("Por favor escribe el presupuesto en pesos, solo números. Ej: 25000 💰", chat_id)
        sesion['integrante_actual']['presupuesto'] = presupuesto
        sesion['paso'] = 'recoger_restricciones'
        return _resp(
            f"⚠️ ¿Tienes alguna *restricción alimentaria*?\n\n"
            f"Escribe las que apliquen separadas por coma, o *ninguna*:\n"
            f"• vegetariano\n• vegano\n• sin gluten\n• sin lactosa\n• sin mariscos",
            chat_id
        )

    elif paso == 'recoger_restricciones':
        if texto.lower() in ['ninguna', 'no', 'n', 'ninguno', '-']:
            restricciones = []
        else:
            mapa = {
                'vegetariano': 'vegetariano', 'vegano': 'vegano',
                'sin gluten': 'sin_gluten', 'gluten': 'sin_gluten',
                'sin lactosa': 'sin_lactosa', 'lactosa': 'sin_lactosa',
                'sin mariscos': 'sin_mariscos', 'mariscos': 'sin_mariscos',
            }
            restricciones = []
            for parte in texto.lower().split(','):
                parte = parte.strip()
                if parte in mapa:
                    restricciones.append(mapa[parte])

        sesion['integrante_actual']['restricciones'] = restricciones
        sesion['integrantes'].append(dict(sesion['integrante_actual']))
        num_actual = len(sesion['integrantes'])
        num_total  = sesion['num_integrantes']

        nombre = sesion['integrante_actual']['nombre']
        resumen = (
            f"✅ *{nombre}* registrado:\n"
            f"   Perfil: {sesion['integrante_actual']['vector']}\n"
            f"   Presupuesto: ${sesion['integrante_actual']['presupuesto']:,}\n"
        )
        if restricciones:
            resumen += f"   Restricciones: {', '.join(restricciones)}\n"

        if num_actual < num_total:
            sesion['paso'] = 'recoger_perfil_nombre'
            return _resp(
                resumen + f"\n*Integrante {num_actual + 1} de {num_total}*\n¿Cuál es su nombre?",
                chat_id
            )
        else:
            # Grupo completo → recomendar
            sesion['paso'] = 'recomendar'
            resultado = _ejecutar_recomendacion(sesion)
            del _sesiones[chat_id]  # limpiar sesión
            return {
                'respuesta': resumen + '\n' + resultado,
                'chat_id': chat_id,
                'listo': True,
            }

    # Estado desconocido — reiniciar
    del _sesiones[chat_id]
    return _resp("Algo salió mal 😕 Escribe /start para comenzar de nuevo.", chat_id)


def _ejecutar_recomendacion(sesion: dict) -> str:
    """Ejecuta el motor de recomendación con los datos de la sesión."""
    try:
        perfiles = []
        for it in sesion['integrantes']:
            perfiles.append(PerfilUsuario(
                nombre=it['nombre'],
                vector=it['vector'],
                presupuesto_max=it.get('presupuesto', 30000),
                restricciones=it.get('restricciones', []),
            ))

        restaurantes = cargar_restaurantes()
        motor = MotorRecomendacionGrupal(restaurantes)
        resultado = motor.recomendar_automatico(perfiles, top_k=3)

        # Guardar en Supabase
        grupo_id = crear_grupo(
            nombre=sesion.get('nombre_grupo', 'Grupo Telegram'),
            canal='telegram',
            metodo=resultado.metodo_usado
        )
        guardar_recomendacion(grupo_id, resultado)

        # Formatear respuesta para Telegram
        metodo_labels = {
            'promedio': '🤝 Promedio (grupo homogéneo)',
            'minima_miseria': '🛡️ Mínima miseria (hay restricciones)',
            'maximo_placer': '⭐ Máximo placer (total acuerdo)',
            'media_satisfaccion': '📊 Media satisfacción',
            'mayoria_ponderada': '🗳️ Mayoría ponderada (grupo diverso)',
        }

        texto = (
            f"🎉 *¡Aquí están las recomendaciones para {sesion.get('nombre_grupo', 'el grupo')}!*\n"
            f"_Método: {metodo_labels.get(resultado.metodo_usado, resultado.metodo_usado)}_\n\n"
        )

        if resultado.advertencias:
            for adv in resultado.advertencias:
                texto += f"_{adv}_\n"
            texto += "\n"

        for i, r in enumerate(resultado.restaurantes, 1):
            rest = r['restaurante']
            emojis = ['🥇', '🥈', '🥉']
            texto += (
                f"{emojis[i-1]} *{rest.nombre}*\n"
                f"   📍 {', '.join(rest.tipo_cocina[:2]) if rest.tipo_cocina else 'Varios'}\n"
                f"   💰 ~${rest.precio_promedio:,}/persona\n"
                f"   ⭐ {rest.rating} · Score grupo: {r['score_grupo']:.0%}\n"
                f"   {r['justificacion']}\n\n"
            )

        texto += (
            f"_💬 ¿Fueron? Cuéntenos cómo les fue escribiendo /feedback_\n"
            f"_Para una nueva búsqueda escribe /nuevo_"
        )
        return texto

    except Exception as e:
        return f"❌ Ocurrió un error al buscar restaurantes: {str(e)}\nIntenta de nuevo con /nuevo"


def _nueva_sesion(chat_id: int) -> dict:
    return {
        'chat_id': chat_id,
        'paso': 'inicio',
        'nombre_grupo': '',
        'num_integrantes': 1,
        'integrantes': [],
        'integrante_actual': {},
    }


def _resp(texto: str, chat_id: int) -> dict:
    return {'respuesta': texto, 'chat_id': chat_id, 'listo': False}


def _ayuda() -> str:
    return (
        "🍽️ *¿Dónde comemos hoy?* — Comandos:\n\n"
        "/start   → Comenzar nueva búsqueda grupal\n"
        "/nuevo   → Lo mismo que /start\n"
        "/ayuda   → Mostrar esta ayuda\n"
        "/cancelar → Cancelar sesión actual\n\n"
        "Cuéntame cuántos son en el grupo, qué les gusta "
        "comer y les recomiendo el mejor restaurante 🎯"
    )


# ─────────────────────────────────────────────────────────────────
# ENDPOINT PARA REGISTRAR EN app.py / servidor.py
# ─────────────────────────────────────────────────────────────────

@telegram_bp.route('/telegram/mensaje', methods=['POST'])
def recibir_mensaje_telegram():
    """
    Endpoint llamado por n8n cuando llega un mensaje de Telegram.

    n8n envía:
    {
      "chat_id": 123456789,
      "user_id": 987654321,
      "username": "Juan",
      "texto": "/start"
    }

    Retorna:
    {
      "respuesta": "Texto markdown para enviar",
      "chat_id": 123456789,
      "listo": false
    }
    """
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'Body vacío'}), 400

    chat_id  = datos.get('chat_id', 0)
    user_id  = datos.get('user_id', chat_id)
    username = datos.get('username', 'Usuario')
    texto    = datos.get('texto', '')

    if not texto:
        return jsonify({'error': 'Campo "texto" vacío'}), 400

    respuesta = procesar_mensaje(int(chat_id), int(user_id), username, texto)
    return jsonify(respuesta)
