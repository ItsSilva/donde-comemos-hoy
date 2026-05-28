"""
servidor.py — API REST con Flask
¿Dónde comemos hoy? · Conector WEB

Endpoints:
  POST /recomendar          — Recomienda restaurantes para un grupo
  POST /recomendar/auto     — Selección automática de método
  POST /comparar-metodos    — Compara los 5 métodos para el mismo grupo
  POST /feedback            — Recibe feedback post-visita
  GET  /restaurantes        — Lista restaurantes disponibles
  GET  /salud               — Healthcheck

Estructura del body para /recomendar:
{
  "grupo": [
    {
      "nombre": "Camila",
      "vector": [3, 7, 6, 8, 4],        ← [picante,dulce,salado,vegetariano,carne]
      "presupuesto_max": 25000,
      "restricciones": ["vegetariano"],
      "peso_voto": 1.0
    },
    ...
  ],
  "metodo": "mayoria_ponderada",         ← opcional, default: auto
  "top_k": 5
}

── Integración Web (n8n / frontend) ────────────────────────────
  Cuando el portal web capture el formulario del grupo, hace POST
  a este servidor. El frontend puede ser una SPA (React/HTML) o
  un flujo n8n con nodo HTTP Request apuntando a /recomendar.

── Integración Telegram (n8n bot) ──────────────────────────────
  El bot de Telegram conversa con los usuarios (n8n), acumula los
  datos en un objeto JSON y hace POST a /recomendar cuando el grupo
  está completo. Ver scripts/n8n_webhook.md para el flujo completo.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, request, jsonify, send_from_directory
from core.motor_recomendacion import MotorRecomendacionGrupal, PerfilUsuario, DIMS
from data.base_datos import (
    cargar_restaurantes, crear_grupo, guardar_integrantes_grupo,
    guardar_recomendacion, obtener_o_crear_usuario, guardar_sesion, guardar_feedback
)

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _parsear_perfiles(grupo_json: list) -> list[PerfilUsuario]:
    """Convierte el JSON del request en objetos PerfilUsuario."""
    perfiles = []
    for p in grupo_json:
        perfiles.append(PerfilUsuario(
            nombre=p.get('nombre', 'Anónimo'),
            vector=p.get('vector', [5, 5, 5, 5, 5]),
            presupuesto_max=p.get('presupuesto_max', 30000),
            distancia_max=p.get('distancia_max', 2000),
            restricciones=p.get('restricciones', []),
            peso_voto=p.get('peso_voto', 1.0),
        ))
    return perfiles


def _serializar_resultado(resultado) -> dict:
    """Convierte ResultadoRecomendacion a dict JSON-serializable."""
    restaurantes_json = []
    for r in resultado.restaurantes:
        rest = r['restaurante']
        restaurantes_json.append({
            'id': rest.id,
            'nombre': rest.nombre,
            'descripcion': rest.descripcion,
            'tipo_cocina': rest.tipo_cocina,
            'precio_promedio_cop': rest.precio_promedio,
            'rating': rest.rating,
            'tiene_vegetariano': rest.tiene_vegetariano,
            'tiene_vegano': rest.tiene_vegano,
            'hace_delivery': rest.hace_delivery,
            'score_grupo': r['score_grupo'],
            'score_min': r['score_min'],
            'score_promedio': r['score_promedio'],
            'satisfaccion_por_persona': r['satisfaccion_por_persona'],
            'justificacion': r['justificacion'],
        })
    return {
        'grupo': resultado.grupo,
        'metodo_usado': resultado.metodo_usado,
        'perfil_n': dict(zip(DIMS, resultado.perfil_n)),
        'restaurantes': restaurantes_json,
        'advertencias': resultado.advertencias,
        'estadisticas': resultado.estadisticas,
    }


def _adjuntar_ids_recomendacion(respuesta: dict, recomendaciones_guardadas: list[dict]) -> dict:
    """Pone el id de la fila recomendaciones dentro de cada restaurante del response."""
    ids_por_restaurante = {
        str(r.get('restaurante_id')): r.get('id')
        for r in recomendaciones_guardadas
        if r.get('restaurante_id') and r.get('id')
    }

    for restaurante in respuesta.get('restaurantes', []):
        restaurante['recomendacion_id'] = ids_por_restaurante.get(str(restaurante.get('id')))

    return respuesta


# ─────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────


@app.route('/', methods=['GET'])
def portal_web():
    """Sirve el frontend visual del portal web."""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/salud', methods=['GET'])
def salud():
    """Healthcheck — verifica que el servidor está vivo."""
    return jsonify({'estado': 'ok', 'sistema': '¿Dónde comemos hoy?', 'version': '1.0'})


@app.route('/restaurantes', methods=['GET'])
def listar_restaurantes():
    """Retorna la lista de restaurantes disponibles."""
    restaurantes = cargar_restaurantes()
    return jsonify([{
        'id': r.id,
        'nombre': r.nombre,
        'tipo_cocina': r.tipo_cocina,
        'precio_promedio_cop': r.precio_promedio,
        'tiene_vegetariano': r.tiene_vegetariano,
        'tiene_vegano': r.tiene_vegano,
        'hace_delivery': r.hace_delivery,
        'rating': r.rating,
    } for r in restaurantes])


@app.route('/recomendar', methods=['POST'])
def recomendar():
    """
    Endpoint principal de recomendación.

    Body JSON:
    {
      "grupo": [{nombre, vector, presupuesto_max, restricciones, peso_voto}, ...],
      "metodo": "mayoria_ponderada",  (opcional)
      "top_k": 5                      (opcional)
    }
    """
    datos = request.get_json()
    if not datos or 'grupo' not in datos:
        return jsonify({'error': 'Se requiere el campo "grupo" con al menos un integrante.'}), 400

    grupo_json = datos['grupo']
    if len(grupo_json) < 1:
        return jsonify({'error': 'El grupo debe tener al menos 1 integrante.'}), 400

    metodo = datos.get('metodo', 'mayoria_ponderada')
    top_k  = min(int(datos.get('top_k', 5)), 10)

    try:
        perfiles    = _parsear_perfiles(grupo_json)
        restaurantes = cargar_restaurantes()
        motor       = MotorRecomendacionGrupal(restaurantes)
        resultado   = motor.recomendar(perfiles, metodo=metodo, top_k=top_k)

        # Persistir sesión completa en Supabase:
        # grupos + usuarios + perfiles_usuario + grupo_miembros + recomendaciones + sesiones
        grupo_id = crear_grupo(canal='web', metodo=metodo)

        usuarios_guardados = guardar_integrantes_grupo(grupo_id, perfiles, canal='web')
        recomendaciones_guardadas = guardar_recomendacion(grupo_id, resultado, top_k=top_k)
        sesion_id = guardar_sesion(
            grupo_id=grupo_id,
            usuario_id=None,
            canal='web',
            estado='recomendacion_generada',
            contexto={
                'grupo': grupo_json,
                'metodo': metodo,
                'top_k': top_k,
                'usuarios_guardados': usuarios_guardados,
                'resultado': {
                    'metodo_usado': resultado.metodo_usado,
                    'perfil_n': resultado.perfil_n,
                    'restaurantes': [r['restaurante'].nombre for r in resultado.restaurantes],
                },
            },
        )

        respuesta = _serializar_resultado(resultado)
        respuesta = _adjuntar_ids_recomendacion(respuesta, recomendaciones_guardadas)
        respuesta['grupo_id'] = grupo_id
        respuesta['sesion_id'] = sesion_id
        respuesta['usuarios_guardados'] = usuarios_guardados
        return jsonify(respuesta)

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Error interno: {str(e)}'}), 500


@app.route('/recomendar/auto', methods=['POST'])
def recomendar_auto():
    """
    Como /recomendar pero selecciona el método automáticamente
    según la homogeneidad del grupo.
    """
    datos = request.get_json()
    if not datos or 'grupo' not in datos:
        return jsonify({'error': 'Se requiere el campo "grupo".'}), 400

    top_k = min(int(datos.get('top_k', 5)), 10)

    try:
        perfiles    = _parsear_perfiles(datos['grupo'])
        restaurantes = cargar_restaurantes()
        motor       = MotorRecomendacionGrupal(restaurantes)
        resultado   = motor.recomendar_automatico(perfiles, top_k=top_k)

        grupo_id = crear_grupo(canal='web', metodo=resultado.metodo_usado)

        usuarios_guardados = guardar_integrantes_grupo(grupo_id, perfiles, canal='web')
        recomendaciones_guardadas = guardar_recomendacion(grupo_id, resultado, top_k=top_k)
        sesion_id = guardar_sesion(
            grupo_id=grupo_id,
            usuario_id=None,
            canal='web',
            estado='recomendacion_generada_auto',
            contexto={
                'grupo': datos['grupo'],
                'metodo': resultado.metodo_usado,
                'top_k': top_k,
                'usuarios_guardados': usuarios_guardados,
                'resultado': {
                    'metodo_usado': resultado.metodo_usado,
                    'perfil_n': resultado.perfil_n,
                    'restaurantes': [r['restaurante'].nombre for r in resultado.restaurantes],
                },
            },
        )

        respuesta = _serializar_resultado(resultado)
        respuesta = _adjuntar_ids_recomendacion(respuesta, recomendaciones_guardadas)
        respuesta['grupo_id'] = grupo_id
        respuesta['sesion_id'] = sesion_id
        respuesta['usuarios_guardados'] = usuarios_guardados
        return jsonify(respuesta)

    except Exception as e:
        return jsonify({'error': f'Error interno: {str(e)}'}), 500


@app.route('/comparar-metodos', methods=['POST'])
def comparar_metodos():
    """
    Compara los 5 métodos de agregación para el mismo grupo.
    Útil para la reflexión crítica del proyecto.
    """
    datos = request.get_json()
    if not datos or 'grupo' not in datos:
        return jsonify({'error': 'Se requiere el campo "grupo".'}), 400

    try:
        perfiles    = _parsear_perfiles(datos['grupo'])
        restaurantes = cargar_restaurantes()
        motor       = MotorRecomendacionGrupal(restaurantes)
        comparativa = motor.comparar_metodos(perfiles)
        return jsonify({'comparativa': comparativa, 'dims': DIMS})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/feedback', methods=['POST'])
def recibir_feedback():
    """
    Recibe feedback post-visita para mejorar futuras recomendaciones.

    Body JSON:
    {
      "recomendacion_id": "uuid",
      "usuario_nombre": "Camila",
      "fue_al_restaurante": true,
      "calificacion": 4,
      "comentario": "Muy rico pero un poco caro"
    }
    """
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'Body vacío.'}), 400

    try:
        usuario = obtener_o_crear_usuario(
            nombre=datos.get('usuario_nombre', 'Anónimo'),
            canal='web'
        )
        exito = guardar_feedback(
            recomendacion_id=datos.get('recomendacion_id', ''),
            usuario_id=usuario['id'] if usuario else '',
            fue=datos.get('fue_al_restaurante', False),
            calificacion=datos.get('calificacion', 3),
            comentario=datos.get('comentario', ''),
        )
        return jsonify({'guardado': exito, 'mensaje': 'Gracias por tu feedback 🙏'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────
# ARRANCAR SERVIDOR
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'true').lower() == 'true'
    print(f"\n🍽️  ¿Dónde comemos hoy? — Servidor corriendo en http://localhost:{port}")
    print(f"   Endpoints disponibles:")
    print(f"   GET  /salud")
    print(f"   GET  /restaurantes")
    print(f"   POST /recomendar")
    print(f"   POST /recomendar/auto")
    print(f"   POST /comparar-metodos")
    print(f"   POST /feedback\n")
    app.run(host='0.0.0.0', port=port, debug=debug)
