"""
telegram_handler.py — Handler del Bot de Telegram vía n8n
¿Dónde comemos hoy? · v2

Mejoras sobre v1:
  - /modificar  → reconfigura un integrante ya registrado
  - /ver        → muestra el grupo acumulado hasta ahora
  - Confirmación explícita antes de recomendar
  - Flujo de feedback post-visita
  - Limpieza correcta de integrante_actual entre personas

── Flujo conversacional ──────────────────────────────────────────
  /start
    → recoger_nombre_grupo
    → recoger_num_integrantes
    → [para cada integrante]
         recoger_perfil_nombre
         recoger_perfil_picante
         recoger_perfil_dulce
         recoger_perfil_salado
         recoger_perfil_vegetariano
         recoger_perfil_carne
         recoger_presupuesto
         recoger_restricciones
    → confirmar_grupo          ← NUEVO: muestra resumen + pide OK
    → recomendar
    → [post-visita] /feedback
         feedback_seleccionar_restaurante
         feedback_calificacion
         feedback_comentario
"""

import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import request, jsonify, Blueprint
from core.motor_recomendacion import MotorRecomendacionGrupal, PerfilUsuario, DIMS
from data.base_datos import (
    cargar_restaurantes, crear_grupo, guardar_recomendacion,
    guardar_feedback, obtener_o_crear_usuario, guardar_sesion,
)

telegram_bp = Blueprint('telegram', __name__)

# ─────────────────────────────────────────────────────────────────
# ESTADO EN MEMORIA  (en producción → Redis / tabla sesiones)
# ─────────────────────────────────────────────────────────────────
_sesiones: dict[int, dict] = {}

EMOJIS_DIMS = {
    'picante': '🌶️', 'dulce': '🍰', 'salado': '🧂',
    'vegetariano': '🥗', 'carne': '🥩',
}

PREGUNTAS_DIMS = {
    'picante':     "🌶️ ¿Cuánto te gusta lo *picante*?\n_1 = nada · 10 = entre más pique mejor_",
    'dulce':       "🍰 ¿Qué tanto disfrutas los sabores *dulces*?\n_1 = no me llama · 10 = me encanta_",
    'salado':      "🧂 ¿Te gustan las comidas *saladas e intensas*?\n_1 = prefiero suave · 10 = muy sazonado_",
    'vegetariano': "🥗 ¿Qué tan importante son las *opciones vegetarianas* para ti?\n_1 = no me importa · 10 = muy importante_",
    'carne':       "🥩 ¿Cuánto disfrutas la *carne* (res, pollo, cerdo)?\n_1 = no como · 10 = soy carnívoro_",
}

ORDEN_DIMS = ['picante', 'dulce', 'salado', 'vegetariano', 'carne']


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _nueva_sesion(chat_id: int) -> dict:
    return {
        'chat_id': chat_id,
        'paso': 'inicio',
        'nombre_grupo': '',
        'num_integrantes': 1,
        'integrantes': [],           # lista de dicts completados
        'integrante_actual': None,   # dict en construcción
        'dim_idx': 0,                # índice de la dimensión que se está recogiendo
        'ultima_recomendacion': None,# guarda los resultados para feedback
    }

def _resp(texto: str, chat_id: int, listo: bool = False) -> dict:
    return {'respuesta': texto, 'chat_id': chat_id, 'listo': listo}

def _num_integrante_actual(sesion: dict) -> int:
    """Número ordinal (1-based) del integrante que se está registrando."""
    return len(sesion['integrantes']) + 1

def _resumen_integrante(it: dict) -> str:
    vec = it.get('vector', [])
    partes = [f"👤 *{it['nombre']}*"]
    for dim, val in zip(ORDEN_DIMS, vec):
        partes.append(f"   {EMOJIS_DIMS[dim]} {dim}: {val}")
    partes.append(f"   💰 Presupuesto: ${it.get('presupuesto', 30000):,}")
    restr = it.get('restricciones', [])
    if restr:
        partes.append(f"   ⚠️ Restricciones: {', '.join(restr)}")
    return "\n".join(partes)

def _resumen_grupo(sesion: dict) -> str:
    lineas = [f"📋 *Grupo: {sesion['nombre_grupo']}* ({len(sesion['integrantes'])} personas)\n"]
    for it in sesion['integrantes']:
        lineas.append(_resumen_integrante(it))
        lineas.append("")
    return "\n".join(lineas)

def _parsear_numero(texto: str, minval: float, maxval: float):
    """Parsea un número y valida rango. Retorna (valor, error_msg)."""
    try:
        val = float(texto.replace(',', '.').replace('$', '').replace('.', '', texto.count('.') - 1).strip())
        if not (minval <= val <= maxval):
            raise ValueError
        return val, None
    except:
        return None, f"Por favor escribe un número entre {int(minval)} y {int(maxval)} 🙏"


# ─────────────────────────────────────────────────────────────────
# MOTOR DE RECOMENDACIÓN
# ─────────────────────────────────────────────────────────────────

def _ejecutar_recomendacion(sesion: dict) -> tuple[str, dict | None]:
    """
    Corre el motor y retorna (texto_respuesta, datos_para_feedback).
    datos_para_feedback = {restaurante_nombre: recomendacion_id, ...}
    """
    try:
        perfiles = [
            PerfilUsuario(
                nombre=it['nombre'],
                vector=it['vector'],
                presupuesto_max=it.get('presupuesto', 30000),
                restricciones=it.get('restricciones', []),
            )
            for it in sesion['integrantes']
        ]

        restaurantes = cargar_restaurantes()
        motor = MotorRecomendacionGrupal(restaurantes)
        resultado = motor.recomendar_automatico(perfiles, top_k=3)

        # Persistir
        grupo_id = crear_grupo(
            nombre=sesion.get('nombre_grupo', 'Grupo Telegram'),
            canal='telegram',
            metodo=resultado.metodo_usado,
        )
        filas = guardar_recomendacion(grupo_id, resultado)

        # Mapa nombre_restaurante → recomendacion_id para feedback
        mapa_feedback = {}
        for fila in filas:
            rid = fila.get('restaurante_id')
            for r in resultado.restaurantes:
                if r['restaurante'].id == rid:
                    mapa_feedback[r['restaurante'].nombre] = fila.get('id')

        guardar_sesion(
            grupo_id=grupo_id, usuario_id=None, canal='telegram',
            estado='recomendacion_generada',
            contexto={'grupo': sesion['nombre_grupo'], 'metodo': resultado.metodo_usado},
        )

        # Formatear texto
        metodo_labels = {
            'promedio':           '🤝 Promedio (grupo homogéneo)',
            'minima_miseria':     '🛡️ Mínima miseria (hay restricciones)',
            'maximo_placer':      '⭐ Máximo placer (todos coinciden)',
            'media_satisfaccion': '📊 Media satisfacción',
            'mayoria_ponderada':  '🗳️ Mayoría ponderada (grupo diverso)',
        }

        texto = (
            f"🎉 *¡Recomendaciones para {sesion.get('nombre_grupo', 'el grupo')}!*\n"
            f"_Método: {metodo_labels.get(resultado.metodo_usado, resultado.metodo_usado)}_\n\n"
        )

        if resultado.advertencias:
            for adv in resultado.advertencias:
                texto += f"_{adv}_\n"
            texto += "\n"

        emojis = ['🥇', '🥈', '🥉']
        for i, r in enumerate(resultado.restaurantes, 1):
            rest = r['restaurante']
            texto += (
                f"{emojis[i-1]} *{rest.nombre}*\n"
                f"   🍽️ {', '.join(rest.tipo_cocina[:2]) if rest.tipo_cocina else 'Varios'}\n"
                f"   💰 ~${rest.precio_promedio:,}/persona\n"
                f"   ⭐ {rest.rating} · Compatibilidad: {r['score_grupo']:.0%}\n"
                f"   👥 {r['justificacion']}\n\n"
            )

        texto += (
            "💬 ¿Fueron al restaurante? Cuéntenme cómo les fue:\n"
            "Escribe */feedback* para dejar una reseña\n\n"
            "_Para una nueva búsqueda escribe /nuevo_"
        )

        return texto, mapa_feedback

    except Exception as e:
        return f"❌ Error al buscar restaurantes: {str(e)}\nIntenta de nuevo con /nuevo", None


# ─────────────────────────────────────────────────────────────────
# MÁQUINA DE ESTADOS
# ─────────────────────────────────────────────────────────────────

def procesar_mensaje(chat_id: int, user_id: int, username: str, texto: str) -> dict:
    texto_raw = texto.strip()
    texto = texto_raw.lower()

    # ── Comandos que reinician ─────────────────────────────────
    if texto in ['/start', '/nuevo', 'nuevo', 'start']:
        _sesiones[chat_id] = _nueva_sesion(chat_id)
        sesion = _sesiones[chat_id]
        sesion['paso'] = 'recoger_nombre_grupo'
        return _resp(
            "🍽️ *¡Bienvenidos a ¿Dónde comemos hoy?!*\n\n"
            "Los ayudo a encontrar el restaurante perfecto para su grupo. "
            "Sin peleas, sin vueltas.\n\n"
            "📝 ¿Cómo se llama el grupo o cuál es la ocasión?\n"
            "_Ej: Almuerzo de trabajo, Cumpleaños de Sofía, Los de siempre..._",
            chat_id,
        )

    # Obtener sesión existente o crear una
    if chat_id not in _sesiones:
        _sesiones[chat_id] = _nueva_sesion(chat_id)

    sesion = _sesiones[chat_id]
    paso = sesion['paso']

    # ── Comandos globales ──────────────────────────────────────
    if texto == '/ayuda':
        return _resp(_ayuda(), chat_id)

    if texto == '/cancelar':
        del _sesiones[chat_id]
        return _resp("❌ Sesión cancelada. Escribe /start para comenzar de nuevo.", chat_id)

    if texto == '/ver':
        if not sesion['integrantes']:
            return _resp("Aún no hay integrantes registrados. Continúa el flujo 👇", chat_id)
        return _resp(_resumen_grupo(sesion), chat_id)

    # ── /modificar ────────────────────────────────────────────
    # Permite reconfiguar un integrante ya registrado.
    # Uso: /modificar Camila  →  reinicia el flujo de ese integrante
    if texto.startswith('/modificar'):
        partes = texto_raw.split(maxsplit=1)
        if len(partes) < 2:
            nombres = [it['nombre'] for it in sesion['integrantes']]
            lista = "\n".join(f"  • {n}" for n in nombres) if nombres else "  (ninguno aún)"
            return _resp(
                f"✏️ *Modificar integrante*\n\n"
                f"Escribe el nombre del integrante que quieres editar:\n{lista}\n\n"
                f"Ej: `/modificar Camila`",
                chat_id,
            )
        nombre_buscar = partes[1].strip()
        idx = next(
            (i for i, it in enumerate(sesion['integrantes'])
             if it['nombre'].lower() == nombre_buscar.lower()),
            None,
        )
        if idx is None:
            return _resp(
                f"No encontré a *{nombre_buscar}* en el grupo. "
                f"Usa /ver para ver los nombres exactos.",
                chat_id,
            )
        # Sacar el integrante de la lista y volver a recoger su perfil
        sesion['integrante_actual'] = sesion['integrantes'].pop(idx)
        sesion['integrante_actual']['vector'] = []  # resetear vector
        sesion['integrante_actual']['restricciones'] = []
        sesion['dim_idx'] = 0
        sesion['paso'] = 'recoger_perfil_picante'
        return _resp(
            f"✏️ Vamos a actualizar el perfil de *{sesion['integrante_actual']['nombre']}*.\n\n"
            + PREGUNTAS_DIMS['picante'],
            chat_id,
        )

    # ── /feedback ─────────────────────────────────────────────
    if texto == '/feedback':
        ultima = sesion.get('ultima_recomendacion')
        if not ultima:
            return _resp(
                "No tengo una recomendación reciente para evaluar.\n"
                "Usa /nuevo para hacer una búsqueda primero.",
                chat_id,
            )
        nombres = list(ultima.keys())
        lista = "\n".join(f"  {i+1}. {n}" for i, n in enumerate(nombres))
        sesion['paso'] = 'feedback_seleccionar_restaurante'
        sesion['feedback_nombres'] = nombres
        return _resp(
            f"⭐ *Feedback post-visita*\n\n"
            f"¿A cuál restaurante fueron?\n{lista}\n\n"
            f"Escribe el número:",
            chat_id,
        )

    # ─────────────────────────────────────────────────────────
    # MÁQUINA DE ESTADOS PRINCIPAL
    # ─────────────────────────────────────────────────────────

    if paso == 'inicio':
        sesion['paso'] = 'recoger_nombre_grupo'
        return _resp(
            "📝 ¿Cómo se llama el grupo o cuál es la ocasión?\n"
            "_Ej: Almuerzo de trabajo, Cumpleaños de Sofía..._",
            chat_id,
        )

    elif paso == 'recoger_nombre_grupo':
        sesion['nombre_grupo'] = texto_raw
        sesion['integrantes'] = []
        sesion['paso'] = 'recoger_num_integrantes'
        return _resp(
            f"✅ Grupo: *{texto_raw}*\n\n"
            f"👥 ¿Cuántas personas van? _(1 a 8)_",
            chat_id,
        )

    elif paso == 'recoger_num_integrantes':
        val, err = _parsear_numero(texto, 1, 8)
        if err:
            return _resp("Por favor escribe un número entre 1 y 8 🙏", chat_id)
        sesion['num_integrantes'] = int(val)
        sesion['paso'] = 'recoger_perfil_nombre'
        n = int(val)
        return _resp(
            f"Perfecto, *{n} persona{'s' if n > 1 else ''}* 👍\n\n"
            f"*Integrante 1 de {n}*\n"
            f"¿Cuál es su nombre?",
            chat_id,
        )

    elif paso == 'recoger_perfil_nombre':
        num = _num_integrante_actual(sesion)
        total = sesion['num_integrantes']
        sesion['integrante_actual'] = {
            'nombre': texto_raw,
            'vector': [],
            'presupuesto': 30000,
            'restricciones': [],
        }
        sesion['dim_idx'] = 0
        sesion['paso'] = 'recoger_perfil_dim'
        return _resp(
            f"Hola *{texto_raw}* 👋  ({num}/{total})\n\n"
            f"Voy a hacerte {len(DIMS)} preguntas rápidas. "
            f"Responde con un número del *1 al 10*.\n\n"
            + PREGUNTAS_DIMS[ORDEN_DIMS[0]],
            chat_id,
        )

    elif paso == 'recoger_perfil_dim':
        dim_actual = ORDEN_DIMS[sesion['dim_idx']]
        val, err = _parsear_numero(texto, 1, 10)
        if err:
            return _resp(
                f"Por favor escribe un número entre 1 y 10 "
                f"{EMOJIS_DIMS[dim_actual]} 🙏",
                chat_id,
            )

        sesion['integrante_actual']['vector'].append(round(val, 1))
        sesion['dim_idx'] += 1

        if sesion['dim_idx'] < len(ORDEN_DIMS):
            siguiente = ORDEN_DIMS[sesion['dim_idx']]
            return _resp(PREGUNTAS_DIMS[siguiente], chat_id)
        else:
            # Terminamos las 5 dimensiones → pedir presupuesto
            sesion['paso'] = 'recoger_presupuesto'
            return _resp(
                "💰 ¿Cuánto estás dispuesto a gastar *por persona*?\n"
                "_Solo el número en pesos COP_\n"
                "_Ej: 20000 · 35000 · 50000_",
                chat_id,
            )

    elif paso == 'recoger_presupuesto':
        texto_limpio = texto.replace('.', '').replace(',', '').replace('$', '').strip()
        val, err = _parsear_numero(texto_limpio, 5000, 500000)
        if err:
            return _resp(
                "Por favor escribe el presupuesto en pesos (solo números).\n"
                "Ej: 25000 💰",
                chat_id,
            )
        sesion['integrante_actual']['presupuesto'] = int(val)
        sesion['paso'] = 'recoger_restricciones'
        return _resp(
            "⚠️ ¿Tienes alguna *restricción alimentaria*?\n\n"
            "Escribe las que apliquen (separadas por coma) o escribe *ninguna*:\n"
            "• vegetariano\n• vegano\n• sin gluten\n• sin lactosa\n• sin mariscos",
            chat_id,
        )

    elif paso == 'recoger_restricciones':
        mapa = {
            'vegetariano': 'vegetariano',
            'vegano': 'vegano',
            'sin gluten': 'sin_gluten', 'gluten': 'sin_gluten',
            'sin lactosa': 'sin_lactosa', 'lactosa': 'sin_lactosa',
            'sin mariscos': 'sin_mariscos', 'mariscos': 'sin_mariscos',
        }
        if texto in ['ninguna', 'no', 'n', 'ninguno', '-', 'nada']:
            restricciones = []
        else:
            restricciones = []
            for parte in texto.split(','):
                p = parte.strip()
                if p in mapa:
                    restricciones.append(mapa[p])

        sesion['integrante_actual']['restricciones'] = restricciones

        # Confirmar integrante y decidir si seguir o mostrar resumen
        it = sesion['integrante_actual']
        sesion['integrantes'].append(dict(it))
        sesion['integrante_actual'] = None

        num_actual = len(sesion['integrantes'])
        total = sesion['num_integrantes']

        resumen = _resumen_integrante(it) + "\n✅ Registrado\n"

        if num_actual < total:
            sesion['paso'] = 'recoger_perfil_nombre'
            return _resp(
                resumen + f"\n*Integrante {num_actual + 1} de {total}*\n"
                          f"¿Cuál es su nombre?",
                chat_id,
            )
        else:
            # Todos registrados → mostrar resumen y pedir confirmación
            sesion['paso'] = 'confirmar_grupo'
            return _resp(
                resumen + "\n" + _resumen_grupo(sesion) +
                "\n¿Quieres que busque restaurantes con este grupo?\n\n"
                "Responde *sí* para recomendar, o:\n"
                "• /modificar [nombre] — para editar un integrante\n"
                "• /ver — para ver el grupo completo",
                chat_id,
            )

    elif paso == 'confirmar_grupo':
        if texto in ['si', 'sí', 's', 'yes', 'ok', 'dale', 'bueno', 'listo', '✅']:
            sesion['paso'] = 'recomendar'
            texto_resultado, mapa_feedback = _ejecutar_recomendacion(sesion)
            if mapa_feedback:
                sesion['ultima_recomendacion'] = mapa_feedback
            sesion['paso'] = 'listo'
            return _resp(texto_resultado, chat_id, listo=True)
        else:
            return _resp(
                "Escribe *sí* cuando quieras recomendar.\n\n"
                "Comandos disponibles:\n"
                "• /modificar [nombre] — editar un integrante\n"
                "• /ver — ver el grupo\n"
                "• /cancelar — empezar de cero",
                chat_id,
            )

    # ── FEEDBACK ──────────────────────────────────────────────

    elif paso == 'feedback_seleccionar_restaurante':
        val, err = _parsear_numero(texto, 1, len(sesion.get('feedback_nombres', ['x'])))
        if err:
            return _resp(f"Escribe el número del restaurante (1, 2 o 3) 🙏", chat_id)
        idx = int(val) - 1
        nombre = sesion['feedback_nombres'][idx]
        sesion['feedback_restaurante_nombre'] = nombre
        sesion['feedback_recomendacion_id'] = sesion['ultima_recomendacion'].get(nombre)
        sesion['paso'] = 'feedback_calificacion'
        return _resp(
            f"Bien, *{nombre}*.\n\n"
            f"⭐ ¿Cómo calificarías la visita?\n"
            f"_1 = muy mala · 5 = excelente_",
            chat_id,
        )

    elif paso == 'feedback_calificacion':
        val, err = _parsear_numero(texto, 1, 5)
        if err:
            return _resp("Escribe un número entre 1 y 5 ⭐", chat_id)
        sesion['feedback_calificacion'] = int(val)
        sesion['paso'] = 'feedback_comentario'
        return _resp(
            "💬 ¿Algún comentario sobre la experiencia?\n"
            "_Escribe lo que quieras o di *saltar* si no tienes comentarios_",
            chat_id,
        )

    elif paso == 'feedback_comentario':
        comentario = "" if texto in ['saltar', 'skip', 'no', '-'] else texto_raw

        try:
            usuario = obtener_o_crear_usuario(
                nombre=sesion['integrantes'][0]['nombre'] if sesion['integrantes'] else 'Usuario Telegram',
                telegram_id=None,
                canal='telegram',
            )
            recomendacion_id = sesion.get('feedback_recomendacion_id', '')
            if recomendacion_id and usuario:
                guardar_feedback(
                    recomendacion_id=recomendacion_id,
                    usuario_id=usuario['id'],
                    fue=True,
                    calificacion=sesion.get('feedback_calificacion', 3),
                    comentario=comentario,
                )
            msg_ok = "✅ ¡Gracias por tu feedback! Nos ayuda a mejorar las recomendaciones 🙏"
        except Exception as e:
            msg_ok = f"Gracias por el feedback (no se pudo guardar: {e})"

        sesion['paso'] = 'listo'
        return _resp(
            msg_ok + "\n\n_Escribe /nuevo para una nueva búsqueda_",
            chat_id,
        )

    # Estado desconocido
    del _sesiones[chat_id]
    return _resp(
        "Algo salió mal 😕 Escribe /start para comenzar de nuevo.",
        chat_id,
    )


def _ayuda() -> str:
    return (
        "🍽️ *¿Dónde comemos hoy?* — Comandos\n\n"
        "/start     → Comenzar nueva búsqueda grupal\n"
        "/nuevo     → Lo mismo que /start\n"
        "/ver       → Ver el grupo actual\n"
        "/modificar [nombre] → Editar un integrante ya registrado\n"
        "/feedback  → Dejar reseña después de visitar el restaurante\n"
        "/cancelar  → Cancelar sesión\n"
        "/ayuda     → Esta pantalla"
    )


# ─────────────────────────────────────────────────────────────────
# ENDPOINT FLASK
# ─────────────────────────────────────────────────────────────────

@telegram_bp.route('/telegram/mensaje', methods=['POST'])
def recibir_mensaje_telegram():
    """
    Endpoint llamado por n8n cuando llega un mensaje de Telegram.

    Body esperado:
    {
      "chat_id":  123456789,
      "user_id":  987654321,
      "username": "Juan",
      "texto":    "/start"
    }

    Respuesta:
    {
      "respuesta": "Texto markdown para Telegram",
      "chat_id":   123456789,
      "listo":     false
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