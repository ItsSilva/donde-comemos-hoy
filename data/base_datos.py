"""
base_datos.py — Capa de persistencia con Supabase
Guarda y recupera usuarios, grupos, recomendaciones y feedback.
"""

import os
import uuid
import json
from typing import Optional
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_DISPONIBLE = True
except ImportError:
    SUPABASE_DISPONIBLE = False

# Importar estructuras del motor
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.motor_recomendacion import PerfilUsuario, Restaurante, DIMS


# ─────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://mkzkqdqhalavvnxisbqi.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_Zxj5YOuJ7qNFo7qxiubm0w_vnJRxOzG")


def _get_cliente() -> Optional["Client"]:
    """Retorna cliente Supabase o None si no está disponible."""
    if not SUPABASE_DISPONIBLE:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"[BD] No se pudo conectar a Supabase: {e}")
        return None


# ─────────────────────────────────────────────────────────────────
# USUARIOS
# ─────────────────────────────────────────────────────────────────

def obtener_o_crear_usuario(nombre: str,
                             telegram_id: Optional[int] = None,
                             canal: str = 'web') -> Optional[dict]:
    """
    Busca un usuario por telegram_id o nombre; lo crea si no existe.
    Retorna el dict del usuario o None si falla.
    """
    cliente = _get_cliente()
    if not cliente:
        return {'id': str(uuid.uuid4()), 'nombre': nombre, 'canal_origen': canal}

    try:
        # Buscar por telegram_id si está disponible
        if telegram_id:
            res = cliente.table('usuarios').select('*').eq('telegram_id', telegram_id).execute()
            if res.data:
                return res.data[0]

        # Crear nuevo usuario
        nuevo = {
            'nombre': nombre,
            'canal_origen': canal,
        }
        if telegram_id:
            nuevo['telegram_id'] = telegram_id

        res = cliente.table('usuarios').insert(nuevo).execute()
        return res.data[0] if res.data else None

    except Exception as e:
        print(f"[BD] Error en obtener_o_crear_usuario: {e}")
        return {'id': str(uuid.uuid4()), 'nombre': nombre}


def guardar_perfil_usuario(usuario_id: str, perfil: PerfilUsuario) -> bool:
    """Guarda o actualiza el perfil de preferencias de un usuario."""
    cliente = _get_cliente()
    if not cliente:
        return False

    datos = {
        'usuario_id': usuario_id,
        'picante':     perfil.vector[0],
        'dulce':       perfil.vector[1],
        'salado':      perfil.vector[2],
        'vegetariano': perfil.vector[3],
        'carne':       perfil.vector[4],
        'precio_max_cop': perfil.presupuesto_max,
        'distancia_max_m': perfil.distancia_max,
        'es_vegetariano': 'vegetariano' in perfil.restricciones,
        'es_vegano':      'vegano'      in perfil.restricciones,
        'sin_gluten':     'sin_gluten'  in perfil.restricciones,
        'sin_lactosa':    'sin_lactosa' in perfil.restricciones,
        'sin_mariscos':   'sin_mariscos' in perfil.restricciones,
    }

    try:
        # Upsert por usuario_id
        res = cliente.table('perfiles_usuario').upsert(datos, on_conflict='usuario_id').execute()
        return bool(res.data)
    except Exception as e:
        print(f"[BD] Error al guardar perfil: {e}")
        return False


def cargar_perfil_usuario(usuario_id: str) -> Optional[PerfilUsuario]:
    """Carga el perfil de un usuario desde Supabase."""
    cliente = _get_cliente()
    if not cliente:
        return None

    try:
        res = cliente.table('perfiles_usuario').select('*').eq('usuario_id', usuario_id).execute()
        if not res.data:
            return None

        d = res.data[0]
        restricciones = []
        if d.get('es_vegetariano'): restricciones.append('vegetariano')
        if d.get('es_vegano'):      restricciones.append('vegano')
        if d.get('sin_gluten'):     restricciones.append('sin_gluten')
        if d.get('sin_lactosa'):    restricciones.append('sin_lactosa')
        if d.get('sin_mariscos'):   restricciones.append('sin_mariscos')

        return PerfilUsuario(
            nombre=usuario_id,
            vector=[d['picante'], d['dulce'], d['salado'], d['vegetariano'], d['carne']],
            presupuesto_max=d.get('precio_max_cop', 30000),
            distancia_max=d.get('distancia_max_m', 2000),
            restricciones=restricciones,
        )
    except Exception as e:
        print(f"[BD] Error al cargar perfil: {e}")
        return None


# ─────────────────────────────────────────────────────────────────
# GRUPOS
# ─────────────────────────────────────────────────────────────────

def crear_grupo(nombre: Optional[str] = None,
                canal: str = 'web',
                chat_id: Optional[int] = None,
                metodo: str = 'mayoria_ponderada') -> Optional[str]:
    """Crea un grupo nuevo y retorna su UUID."""
    cliente = _get_cliente()
    nuevo_id = str(uuid.uuid4())
    if not cliente:
        return nuevo_id

    try:
        datos = {
            'nombre': nombre or f"Grupo {datetime.now().strftime('%d/%m %H:%M')}",
            'canal_origen': canal,
            'metodo_agregacion': metodo,
        }
        if chat_id:
            datos['chat_id'] = chat_id

        res = cliente.table('grupos').insert(datos).execute()
        return res.data[0]['id'] if res.data else nuevo_id
    except Exception as e:
        print(f"[BD] Error al crear grupo: {e}")
        return nuevo_id


def agregar_miembro_grupo(grupo_id: str, usuario_id: str,
                           presupuesto: Optional[int] = None,
                           peso_voto: float = 1.0) -> bool:
    """Agrega un usuario a un grupo."""
    cliente = _get_cliente()
    if not cliente:
        return True  # Modo sin BD

    try:
        datos = {
            'grupo_id': grupo_id,
            'usuario_id': usuario_id,
            'peso_voto': peso_voto,
        }
        if presupuesto:
            datos['presupuesto_sesion'] = presupuesto

        cliente.table('grupo_miembros').upsert(
            datos, on_conflict='grupo_id,usuario_id').execute()
        return True
    except Exception as e:
        print(f"[BD] Error al agregar miembro: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
# RESTAURANTES
# ─────────────────────────────────────────────────────────────────

def cargar_restaurantes() -> list[Restaurante]:
    """Carga todos los restaurantes activos desde Supabase."""
    cliente = _get_cliente()
    if not cliente:
        return _restaurantes_fallback()

    try:
        res = cliente.table('restaurantes').select('*').eq('activo', True).execute()
        restaurantes = []
        for d in res.data:
            restaurantes.append(Restaurante(
                id=d['id'],
                nombre=d['nombre'],
                vector=[d['picante'], d['dulce'], d['salado'],
                        d['vegetariano'], d['carne']],
                precio_promedio=d.get('precio_promedio_cop', 25000),
                ciudad=d.get('ciudad', 'Cali'),
                tipo_cocina=d.get('tipo_cocina') or [],
                tiene_vegetariano=d.get('tiene_opciones_vegetarianas', False),
                tiene_vegano=d.get('tiene_opciones_veganas', False),
                tiene_sin_gluten=d.get('tiene_sin_gluten', False),
                hace_delivery=d.get('hace_delivery', True),
                rating=float(d.get('rating_google') or 4.0),
                descripcion=d.get('descripcion', ''),
            ))
        if not restaurantes:
            return _restaurantes_fallback()
        return restaurantes
    except Exception as e:
        print(f"[BD] Error al cargar restaurantes: {e}. Usando datos locales.")
        return _restaurantes_fallback()


def _restaurantes_fallback() -> list[Restaurante]:
    """
    Datos de restaurantes embebidos como respaldo cuando no hay conexión a BD.
    Permite que el sistema funcione offline para demos y desarrollo.
    """
    datos = [
        ("rest-001", "La Estación de los Carros",  [3,2,8,2,10], 45000, ["colombiana","parrilla"],   False, False, False),
        ("rest-002", "Verde Vital",                 [2,5,5,10,1], 22000, ["vegana","saludable"],      True,  True,  False),
        ("rest-003", "El Buen Gusto",               [4,4,7,5,8],  18000, ["colombiana"],              True,  False, False),
        ("rest-004", "Sushi Maki Cali",             [4,6,7,6,6],  38000, ["japonesa","sushi"],        True,  False, False),
        ("rest-005", "Picante & Fuego",             [9,3,7,6,7],  28000, ["mexicana"],                True,  False, False),
        ("rest-006", "La Cucina di Roma",           [2,5,7,7,6],  35000, ["italiana"],                True,  False, False),
        ("rest-007", "Fogón Vallecaucano",          [3,3,8,4,9],  16000, ["colombiana","regional"],   False, False, False),
        ("rest-008", "Dulce Mar",                   [5,2,8,3,7],  32000, ["mariscos","pescado"],      False, False, False),
        ("rest-009", "Street Burger Co.",           [4,4,8,3,9],  24000, ["hamburguesas"],            False, False, False),
        ("rest-010", "Namaste India",               [8,5,6,8,5],  30000, ["india"],                   True,  True,  False),
        ("rest-011", "El Rincón del Taco",          [7,2,8,5,8],  20000, ["mexicana","tacos"],        True,  False, False),
        ("rest-012", "Terracita Mediterránea",      [3,4,7,8,6],  29000, ["mediterranea","arabe"],    True,  True,  False),
        ("rest-013", "Wok House",                   [6,5,7,7,6],  26000, ["asiatica","thai"],         True,  False, False),
        ("rest-014", "Grillmaster",                 [3,2,9,1,10], 40000, ["parrilla","americana"],    False, False, False),
        ("rest-015", "Café Botánico",               [1,6,5,9,3],  22000, ["saludable","brunch"],      True,  True,  False),
        ("rest-016", "Pizzería Nápoles",            [2,5,7,6,7],  27000, ["italiana","pizza"],        True,  False, False),
        ("rest-017", "Thai Garden",                 [7,6,6,7,6],  31000, ["thai"],                    True,  False, False),
        ("rest-018", "Asadero El Criollo",          [3,2,8,3,9],  15000, ["colombiana","asadero"],    False, False, False),
        ("rest-019", "Crepes & Pancakes",           [2,8,5,7,4],  23000, ["francesa","crepes"],       True,  False, False),
        ("rest-020", "El Samán Grill",              [2,2,8,2,10], 65000, ["parrilla","premium"],      False, False, False),
    ]
    return [
        Restaurante(id=d[0], nombre=d[1], vector=d[2], precio_promedio=d[3],
                    tipo_cocina=d[4], tiene_vegetariano=d[5],
                    tiene_vegano=d[6], tiene_sin_gluten=d[7])
        for d in datos
    ]


# ─────────────────────────────────────────────────────────────────
# RECOMENDACIONES Y FEEDBACK
# ─────────────────────────────────────────────────────────────────

def guardar_recomendacion(grupo_id: str,
                           resultado,  # ResultadoRecomendacion
                           top_k: int = 3) -> bool:
    """Persiste las recomendaciones generadas para una sesión grupal."""
    cliente = _get_cliente()
    if not cliente:
        return True

    try:
        registros = []
        for i, r in enumerate(resultado.restaurantes[:top_k], 1):
            registros.append({
                'grupo_id': grupo_id,
                'restaurante_id': r['restaurante'].id,
                'posicion_ranking': i,
                'score_similitud': r['score_grupo'],
                'score_satisfaccion_min': r['score_min'],
                'metodo_usado': resultado.metodo_usado,
                'perfil_n_usado': json.dumps(resultado.perfil_n),
            })
        if registros:
            cliente.table('recomendaciones').insert(registros).execute()
        return True
    except Exception as e:
        print(f"[BD] Error al guardar recomendaciones: {e}")
        return False


def guardar_feedback(recomendacion_id: str,
                     usuario_id: str,
                     fue: bool,
                     calificacion: int,
                     comentario: str = "") -> bool:
    """
    Guarda feedback del usuario y actualiza su perfil implícitamente.
    La calificación alta (4-5) refuerza el vector actual del usuario
    hacia el restaurante visitado.
    """
    cliente = _get_cliente()
    if not cliente:
        return True

    try:
        datos = {
            'recomendacion_id': recomendacion_id,
            'usuario_id': usuario_id,
            'fue_al_restaurante': fue,
            'calificacion': calificacion,
            'comentario': comentario,
        }
        cliente.table('feedback').upsert(
            datos, on_conflict='recomendacion_id,usuario_id').execute()
        return True
    except Exception as e:
        print(f"[BD] Error al guardar feedback: {e}")
        return False


def guardar_sesion(grupo_id: Optional[str],
                   usuario_id: Optional[str],
                   canal: str,
                   estado: str,
                   contexto: dict) -> Optional[str]:
    """Guarda o actualiza el estado de conversación (útil para Telegram/n8n)."""
    cliente = _get_cliente()
    sesion_id = str(uuid.uuid4())
    if not cliente:
        return sesion_id

    try:
        datos = {
            'canal': canal,
            'estado_conversacion': estado,
            'contexto_json': json.dumps(contexto, ensure_ascii=False),
        }
        if grupo_id:   datos['grupo_id'] = grupo_id
        if usuario_id: datos['usuario_id'] = usuario_id

        res = cliente.table('sesiones').insert(datos).execute()
        return res.data[0]['id'] if res.data else sesion_id
    except Exception as e:
        print(f"[BD] Error al guardar sesión: {e}")
        return sesion_id
