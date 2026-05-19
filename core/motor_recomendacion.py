"""
╔══════════════════════════════════════════════════════════════════╗
║  motor_recomendacion.py                                          ║
║  Motor de recomendación grupal — ¿Dónde comemos hoy?            ║
║                                                                  ║
║  Basado en similitud coseno + 5 métodos de agregación grupal:    ║
║   M1. Promedio naive (democrático)                               ║
║   M2. Mínima miseria (protege al menos satisfecho)               ║
║   M3. Máximo placer (solo dimensiones donde todos están de acuerdo)║
║   M4. Media σ baja (consenso real, no forzado)                   ║
║   M5. Mayoría ponderada (propio — voto ponderado + tolerancia)   ║
║                                                                  ║
║  Conectores disponibles:                                         ║
║   - Web (Flask API — ver api/servidor.py)                        ║
║   - Telegram Bot (n8n webhook — ver scripts/n8n_webhook.md)      ║
╚══════════════════════════════════════════════════════════════════╝
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────
# CONSTANTES — Dimensiones del espacio vectorial
# ─────────────────────────────────────────────────────────────────
DIMS = ['picante', 'dulce', 'salado', 'vegetariano', 'carne']
N_DIMS = len(DIMS)


# ─────────────────────────────────────────────────────────────────
# ESTRUCTURAS DE DATOS
# ─────────────────────────────────────────────────────────────────

@dataclass
class PerfilUsuario:
    """Perfil de preferencias de un integrante del grupo."""
    nombre: str
    vector: list[float]          # [picante, dulce, salado, vegetariano, carne] (1-10)
    presupuesto_max: int = 30000  # COP por persona
    distancia_max: int = 2000     # metros
    restricciones: list[str] = field(default_factory=list)
    # Restricciones: 'vegetariano','vegano','sin_gluten','sin_lactosa','sin_mariscos'
    peso_voto: float = 1.0        # para método M5 ponderado

    def __post_init__(self):
        assert len(self.vector) == N_DIMS, \
            f"El vector debe tener {N_DIMS} dimensiones: {DIMS}"
        self.vector = [float(v) for v in self.vector]


@dataclass
class Restaurante:
    """Restaurante con su vector de características."""
    id: str
    nombre: str
    vector: list[float]          # mismo espacio que PerfilUsuario
    precio_promedio: int = 25000  # COP
    ciudad: str = "Cali"
    tipo_cocina: list[str] = field(default_factory=list)
    tiene_vegetariano: bool = False
    tiene_vegano: bool = False
    tiene_sin_gluten: bool = False
    hace_delivery: bool = True
    rating: float = 4.0
    descripcion: str = ""

    def cumple_restricciones(self, restricciones: list[str]) -> bool:
        """Verifica si el restaurante puede atender las restricciones del grupo."""
        mapa = {
            'vegetariano': self.tiene_vegetariano,
            'vegano': self.tiene_vegano,
            'sin_gluten': self.tiene_sin_gluten,
            'sin_mariscos': 'mariscos' not in self.tipo_cocina,
        }
        return all(mapa.get(r, True) for r in restricciones)


@dataclass
class ResultadoRecomendacion:
    """Resultado completo de una sesión de recomendación grupal."""
    grupo: list[str]
    metodo_usado: str
    perfil_n: list[float]
    restaurantes: list[dict]     # [{restaurante, score, score_min, justificacion}]
    advertencias: list[str] = field(default_factory=list)
    estadisticas: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────
# SIMILITUD — núcleo matemático
# ─────────────────────────────────────────────────────────────────

def similitud_coseno(a: list, b: list) -> float:
    """
    Similitud del coseno entre dos vectores (rango [0, 1]).
    Retorna 0 si algún vector es nulo.
    """
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    norma_a = np.linalg.norm(a)
    norma_b = np.linalg.norm(b)
    if norma_a == 0 or norma_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norma_a * norma_b))


def score_satisfaccion_grupo(perfil_n: list, perfiles: list[PerfilUsuario],
                              restaurante: Restaurante) -> dict:
    """
    Calcula scores individuales de satisfacción para saber quién queda más
    y menos contento con una recomendación.

    Returns:
        dict con 'promedio', 'minimo', 'maximo', 'por_persona'
    """
    scores = {}
    for p in perfiles:
        scores[p.nombre] = round(similitud_coseno(p.vector, restaurante.vector), 4)
    valores = list(scores.values())
    return {
        'por_persona': scores,
        'promedio': round(float(np.mean(valores)), 4),
        'minimo': round(float(np.min(valores)), 4),
        'maximo': round(float(np.max(valores)), 4),
    }


# ─────────────────────────────────────────────────────────────────
# MÉTODOS DE AGREGACIÓN
# ─────────────────────────────────────────────────────────────────

def m1_promedio(perfiles: list[PerfilUsuario]) -> np.ndarray:
    """
    M1 — Promedio naive.
    Democrático: cada miembro pesa igual.
    ✔ Siempre da resultado  ✘ Aplana preferencias fuertes
    """
    vectores = [np.array(p.vector) for p in perfiles]
    return np.mean(vectores, axis=0)


def m2_minima_miseria(perfiles: list[PerfilUsuario], umbral: float = 4.0) -> np.ndarray:
    """
    M2 — Least misery (mínima miseria).
    Solo activa dimensiones donde TODOS los miembros superan el umbral.
    ✔ Protege al menos satisfecho  ✘ Puede devolver vector casi vacío
    """
    vectores = [np.array(p.vector) for p in perfiles]
    promedio = np.mean(vectores, axis=0)
    minimos  = np.min(vectores, axis=0)
    mascara  = (minimos >= umbral).astype(float)
    return promedio * mascara


def m3_maximo_placer(perfiles: list[PerfilUsuario], umbral: float = 7.0) -> np.ndarray:
    """
    M3 — Maximum pleasure.
    Solo dimensiones donde TODOS los miembros tienen preferencia alta.
    ✔ Máxima satisfacción consensuada  ✘ Muy restrictivo, suele dar vector vacío
    """
    vectores = [np.array(p.vector) for p in perfiles]
    promedio = np.mean(vectores, axis=0)
    minimos  = np.min(vectores, axis=0)
    mascara  = (minimos >= umbral).astype(float)
    return promedio * mascara


def m4_media_satisfaccion(perfiles: list[PerfilUsuario], umbral_sigma: float = 3.0) -> np.ndarray:
    """
    M4 — Media satisfacción (baja desviación estándar).
    Activa solo dimensiones donde el grupo COINCIDE (σ baja).
    ✔ Busca verdadero acuerdo  ✘ Ignora magnitud, solo desacuerdo
    """
    vectores = [np.array(p.vector) for p in perfiles]
    promedio = np.mean(vectores, axis=0)
    sigma    = np.std(vectores, axis=0)
    mascara  = (sigma <= umbral_sigma).astype(float)
    return promedio * mascara


def m5_mayoria_ponderada(perfiles: list[PerfilUsuario],
                          fraccion: float = 0.6,
                          umbral: float = 4.5) -> np.ndarray:
    """
    M5 — Mayoría ponderada (método propio).

    Filosofía: no hace falta unanimidad, basta con que la MAYORÍA
    (fraccion %) supere un umbral, pero los pesos de voto permiten
    dar más relevancia a quien más cedió en sesiones anteriores.

    ✔ Equilibra flexibilidad y representación
    ✔ Respeta el historial de cesiones del grupo
    ✔ Siempre produce resultado (fraccion ajustable)
    """
    vectores  = [np.array(p.vector) for p in perfiles]
    pesos     = np.array([p.peso_voto for p in perfiles], dtype=float)
    pesos     = pesos / pesos.sum()                     # normalizar a 1

    # Promedio ponderado
    promedio_ponderado = np.average(vectores, axis=0, weights=pesos)

    n = len(perfiles)
    mascara = np.array([
        np.sum([v[i] >= umbral for v in vectores]) >= fraccion * n
        for i in range(N_DIMS)
    ], dtype=float)

    # Si la máscara es todo ceros (grupo muy diverso), usar promedio completo
    if mascara.sum() == 0:
        return promedio_ponderado

    return promedio_ponderado * mascara


METODOS = {
    'promedio':          (m1_promedio,         {}),
    'minima_miseria':    (m2_minima_miseria,    {'umbral': 4.0}),
    'maximo_placer':     (m3_maximo_placer,     {'umbral': 7.0}),
    'media_satisfaccion':(m4_media_satisfaccion,{'umbral_sigma': 3.0}),
    'mayoria_ponderada': (m5_mayoria_ponderada, {'fraccion': 0.6, 'umbral': 4.5}),
}


# ─────────────────────────────────────────────────────────────────
# FILTROS DE PRESUPUESTO, DISTANCIA Y RESTRICCIONES
# ─────────────────────────────────────────────────────────────────

def filtrar_restaurantes(restaurantes: list[Restaurante],
                         perfiles: list[PerfilUsuario]) -> tuple[list[Restaurante], list[str]]:
    """
    Aplica filtros duros antes de la recomendación:
      1. Precio: dentro del presupuesto mínimo del grupo
      2. Restricciones: unión de todas las restricciones del grupo

    Returns:
        (lista filtrada, advertencias)
    """
    advertencias = []

    # Presupuesto más restrictivo del grupo
    presupuesto_min = min(p.presupuesto_max for p in perfiles)

    # Unión de todas las restricciones
    todas_restricciones = set()
    for p in perfiles:
        todas_restricciones.update(p.restricciones)

    filtrados = []
    for r in restaurantes:
        if r.precio_promedio > presupuesto_min:
            continue
        if not r.cumple_restricciones(list(todas_restricciones)):
            continue
        filtrados.append(r)

    if not filtrados:
        advertencias.append(
            f"⚠️ Ningún restaurante cumple todas las restricciones y presupuesto "
            f"(${presupuesto_min:,} COP). Se amplía la búsqueda sin restricciones duras."
        )
        # Fallback: solo filtrar por restricciones críticas (vegetariano/vegano)
        criticas = todas_restricciones & {'vegetariano', 'vegano'}
        filtrados = [r for r in restaurantes if r.cumple_restricciones(list(criticas))]

    if len(filtrados) < 3:
        advertencias.append(
            f"⚠️ Solo se encontraron {len(filtrados)} restaurante(s) compatibles. "
            f"Considera ampliar el presupuesto o relajar restricciones."
        )

    return filtrados, advertencias


# ─────────────────────────────────────────────────────────────────
# MOTOR PRINCIPAL
# ─────────────────────────────────────────────────────────────────

class MotorRecomendacionGrupal:
    """
    Motor principal del sistema ¿Dónde comemos hoy?

    Uso básico:
        motor = MotorRecomendacionGrupal(restaurantes)
        resultado = motor.recomendar(perfiles_grupo, metodo='mayoria_ponderada')

    Uso con selección automática de método:
        resultado = motor.recomendar_automatico(perfiles_grupo)
    """

    def __init__(self, restaurantes: list[Restaurante]):
        self.restaurantes = restaurantes

    def recomendar(self,
                   perfiles: list[PerfilUsuario],
                   metodo: str = 'mayoria_ponderada',
                   top_k: int = 5) -> ResultadoRecomendacion:
        """
        Recomienda los top_k restaurantes para el grupo.

        Args:
            perfiles: lista de PerfilUsuario con preferencias y restricciones
            metodo:   clave del método de agregación a usar
            top_k:    cuántas recomendaciones retornar

        Returns:
            ResultadoRecomendacion con ranking, justificaciones y estadísticas
        """
        if metodo not in METODOS:
            raise ValueError(f"Método '{metodo}' no existe. Opciones: {list(METODOS)}")

        # 1. Filtrado duro (presupuesto + restricciones)
        candidatos, advertencias = filtrar_restaurantes(self.restaurantes, perfiles)

        if not candidatos:
            return ResultadoRecomendacion(
                grupo=[p.nombre for p in perfiles],
                metodo_usado=metodo,
                perfil_n=[0.0] * N_DIMS,
                restaurantes=[],
                advertencias=advertencias + ["❌ No hay restaurantes disponibles para este grupo."]
            )

        # 2. Calcular perfil N del grupo
        fn, kwargs = METODOS[metodo]
        perfil_n = fn(perfiles, **kwargs)

        # Fallback si el perfil N es todo ceros
        if np.sum(perfil_n) == 0:
            advertencias.append(
                f"⚠️ El método '{metodo}' produjo un perfil vacío (grupo muy diverso). "
                f"Se usó 'promedio' como respaldo."
            )
            perfil_n = m1_promedio(perfiles)

        # 3. Ranking por similitud coseno
        scores_restaurantes = []
        for restaurante in candidatos:
            sim = similitud_coseno(list(perfil_n), restaurante.vector)
            sat = score_satisfaccion_grupo(list(perfil_n), perfiles, restaurante)
            scores_restaurantes.append({
                'restaurante': restaurante,
                'score_grupo': round(sim, 4),
                'score_min':   sat['minimo'],
                'score_promedio': sat['promedio'],
                'satisfaccion_por_persona': sat['por_persona'],
                'justificacion': self._generar_justificacion(restaurante, perfiles, sat),
            })

        scores_restaurantes.sort(key=lambda x: (x['score_grupo'], x['score_min']), reverse=True)
        top = scores_restaurantes[:top_k]

        # 4. Estadísticas de la sesión
        estadisticas = self._calcular_estadisticas(perfiles, metodo)

        return ResultadoRecomendacion(
            grupo=[p.nombre for p in perfiles],
            metodo_usado=metodo,
            perfil_n=list(perfil_n.round(2)),
            restaurantes=top,
            advertencias=advertencias,
            estadisticas=estadisticas,
        )

    def recomendar_automatico(self,
                               perfiles: list[PerfilUsuario],
                               top_k: int = 5) -> ResultadoRecomendacion:
        """
        Selecciona automáticamente el mejor método según la homogeneidad del grupo.

        Lógica:
          - Grupo homogéneo (σ < 2.5): promedio (todos coinciden)
          - Grupo con restricciones: minima_miseria (respetar al más delicado)
          - Grupo heterogéneo (σ ≥ 2.5): mayoria_ponderada (nuestro método)
        """
        vectores = [np.array(p.vector) for p in perfiles]
        sigma_global = float(np.mean(np.std(vectores, axis=0)))

        tiene_restricciones = any(p.restricciones for p in perfiles)

        if tiene_restricciones:
            metodo = 'minima_miseria'
        elif sigma_global < 2.5:
            metodo = 'promedio'
        else:
            metodo = 'mayoria_ponderada'

        resultado = self.recomendar(perfiles, metodo, top_k)
        resultado.estadisticas['sigma_grupal'] = round(sigma_global, 3)
        resultado.estadisticas['metodo_seleccionado_auto'] = metodo
        resultado.estadisticas['razon_seleccion'] = (
            "restricciones dietarias en el grupo" if tiene_restricciones
            else ("grupo homogéneo" if sigma_global < 2.5 else "grupo heterogéneo")
        )
        return resultado

    def comparar_metodos(self,
                         perfiles: list[PerfilUsuario],
                         top_k: int = 3) -> dict:
        """
        Compara los 5 métodos para el mismo grupo.
        Útil para análisis y reflexión crítica.
        """
        comparativa = {}
        for metodo in METODOS:
            resultado = self.recomendar(perfiles, metodo, top_k)
            comparativa[metodo] = {
                'perfil_n': resultado.perfil_n,
                'top_1': resultado.restaurantes[0]['restaurante'].nombre
                         if resultado.restaurantes else '∅',
                'score_top_1': resultado.restaurantes[0]['score_grupo']
                               if resultado.restaurantes else 0,
                'score_min_top_1': resultado.restaurantes[0]['score_min']
                                   if resultado.restaurantes else 0,
                'advertencias': resultado.advertencias,
            }
        return comparativa

    # ── Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _generar_justificacion(restaurante: Restaurante,
                                perfiles: list[PerfilUsuario],
                                satisfaccion: dict) -> str:
        """Genera una explicación legible de por qué se recomienda este restaurante."""
        nombre_min = min(satisfaccion['por_persona'], key=satisfaccion['por_persona'].get)
        nombre_max = max(satisfaccion['por_persona'], key=satisfaccion['por_persona'].get)
        partes = [
            f"Buena opción para el grupo ({len(perfiles)} personas).",
        ]
        if restaurante.tipo_cocina:
            partes.append(f"Cocina {', '.join(restaurante.tipo_cocina[:2])}.")
        partes.append(
            f"El más contento sería {nombre_max} "
            f"(score {satisfaccion['por_persona'][nombre_max]:.2f}) y "
            f"el menos contento {nombre_min} "
            f"(score {satisfaccion['por_persona'][nombre_min]:.2f})."
        )
        if restaurante.precio_promedio:
            partes.append(f"Precio aprox. ${restaurante.precio_promedio:,} COP/persona.")
        return " ".join(partes)

    @staticmethod
    def _calcular_estadisticas(perfiles: list[PerfilUsuario], metodo: str) -> dict:
        vectores = [np.array(p.vector) for p in perfiles]
        return {
            'num_integrantes': len(perfiles),
            'metodo': metodo,
            'sigma_grupal': round(float(np.mean(np.std(vectores, axis=0))), 3),
            'diversidad': round(float(np.mean(np.std(vectores, axis=0)) / 9.0), 3),
            'dims': DIMS,
        }
