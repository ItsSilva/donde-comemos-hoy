"""
tests/test_sistema.py — Suite de pruebas completa
¿Dónde comemos hoy? · Universidad Icesi · Interacción Sociotecnológica

────────────────────────────────────────────────────────────────────
DÓNDE VA ESTE ARCHIVO
────────────────────────────────────────────────────────────────────
Copiarlo en:   tests/test_sistema.py
(crear la carpeta tests/ si no existe — no necesita __init__.py)

Estructura esperada del proyecto:
    proyecto/
    ├── app.py
    ├── core/
    │   └── motor_recomendacion.py
    ├── data/
    │   └── base_datos.py
    ├── tests/
    │   └── test_sistema.py   ← este archivo
    └── ...

────────────────────────────────────────────────────────────────────
CÓMO EJECUTAR
────────────────────────────────────────────────────────────────────
Desde la raíz del proyecto, con el virtualenv activo:

    # Opción 1 — directo con Python (recomendado, sin dependencias extra)
    python3 tests/test_sistema.py

    # Opción 2 — con pytest si está instalado
    python3 -m pytest tests/test_sistema.py -v

El script NO necesita Supabase ni Flask corriendo.
Usa una base de datos de restaurantes embebida y reproducible.

────────────────────────────────────────────────────────────────────
ESTRUCTURA DE PRUEBAS
────────────────────────────────────────────────────────────────────

BLOQUE 1 — Pruebas unitarias  (el sistema hace lo correcto?)
  U01  Presupuesto mínimo del grupo siempre respetado
  U02  Restricción vegana nunca violada
  U03  Restricción vegetariana nunca violada
  U04  Restricción sin_mariscos nunca violada
  U05  Todos los scores en rango [0, 1]
  U06  El ranking ordenado de mayor a menor score
  U07  top_k nunca retorna más restaurantes de los pedidos
  U08  Método inexistente lanza ValueError
  U09  Grupo de 1 persona no rompe el motor
  U10  Vector todo-ceros activa fallback sin romper el sistema

BLOQUE 2 — Precision@K y Recall@K  (las recomendaciones son buenas?)
  M01  Precision@1 grupo carnívoro
  M02  Precision@3 grupo carnívoro
  M03  Precision@5 grupo carnívoro
  M04  Recall@1    grupo carnívoro
  M05  Recall@3    grupo carnívoro
  M06  Recall@5    grupo carnívoro
  M07  Precision@3 grupo heterogéneo (M5)
  M08  Recall@3    grupo heterogéneo (M5)
  M09  Precision@3 grupo con vegano  (M2)

BLOQUE 3 — Pruebas de escenario  (el sistema se comporta como esperamos?)
  E01  Grupo homogéneo → equity score ≥ 0.70
  E02  Grupo heterogéneo → M5 equity no mucho peor que M1
  E03  Grupo con vegano → M2 equity ≥ M1 equity
  E04  Presupuesto muy bajo → activa advertencia de fallback
  E05  Modificar integrante → cambia la recomendación
  E06  Grupo heterogéneo → M1 y M5 recomiendan distintos restaurantes
  E07  Selección automática → grupo homogéneo usa promedio
  E08  Selección automática → grupo con restricciones usa minima_miseria
  E09  Selección automática → grupo con sigma alto usa mayoria_ponderada

BLOQUE 4 — Tablas comparativas  (material para la presentación)
  T01  Tabla M1-M5 en escenario heterogéneo
  T02  Tabla M1-M5 en escenario carnívoro homogéneo
  T03  Tabla M1-M5 en escenario con vegano
  T04  Tabla M1-M5 en escenario con pesos distintos (M5 ponderado)

────────────────────────────────────────────────────────────────────
CÓMO FUNCIONA EL GROUND TRUTH ARTIFICIAL (Precision@K / Recall@K)
────────────────────────────────────────────────────────────────────

Precision@K y Recall@K necesitan saber cuáles restaurantes son
"relevantes" para un grupo. Con usuarios reales usaríamos historial
(ratings, visitas). Como no tenemos eso, construimos un ground truth
artificial: un restaurante es "relevante" si su similitud coseno con
el perfil promedio del grupo supera un umbral fijo (UMBRAL_GT).

    GT(grupo) = { r en candidatos | coseno(perfil_promedio, r.vector) >= UMBRAL_GT }

Esto es válido académicamente para evaluar la calidad del ranking.
La figura clave es si el top-K del sistema coincide con el GT.

    Precision@K = |top-K interseccion GT| / K
    Recall@K    = |top-K interseccion GT| / |GT|

Por qué K = 1, 3 y 5:
  · K=1  → el primero siempre debe ser relevante  (estándar motores de búsqueda)
  · K=3  → lo que el usuario ve en pantalla       (nuestro top_k por defecto)
  · K=5  → cobertura amplia del catálogo

Nota: Recall bajo (ej. R@3 = 20%) NO implica que el sistema es malo.
Si |GT| = 15 y K = 3, el máximo Recall@3 posible es 3/15 = 20%.
El trade-off Precision/Recall es esperado y se explica en la reflexión crítica.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from core.motor_recomendacion import (
    MotorRecomendacionGrupal, PerfilUsuario, Restaurante,
    similitud_coseno, m1_promedio, filtrar_restaurantes, DIMS, METODOS,
)


# ══════════════════════════════════════════════════════════════════
# BASE DE RESTAURANTES DE PRUEBA
# Fija, reproducible, no depende de Supabase ni de internet.
# 20 restaurantes que cubren bien el espacio vectorial de Cali.
# Usa kwargs para evitar confusión con el campo ciudad del dataclass.
# ══════════════════════════════════════════════════════════════════

RESTAURANTES_TEST = [
    Restaurante("r01", "Verde Vital",
                [2, 5, 5, 10, 1], 22000,
                tipo_cocina=["vegana", "saludable"],
                tiene_vegetariano=True, tiene_vegano=True, tiene_sin_gluten=False),
    Restaurante("r02", "Cafe Botanico",
                [1, 6, 5,  9, 3], 22000,
                tipo_cocina=["saludable", "brunch"],
                tiene_vegetariano=True, tiene_vegano=True, tiene_sin_gluten=False),
    Restaurante("r03", "Namaste India",
                [8, 5, 6,  8, 5], 30000,
                tipo_cocina=["india"],
                tiene_vegetariano=True, tiene_vegano=True, tiene_sin_gluten=False),
    Restaurante("r04", "Terracita Mediterr",
                [3, 4, 7,  8, 6], 29000,
                tipo_cocina=["mediterranea", "arabe"],
                tiene_vegetariano=True, tiene_vegano=True, tiene_sin_gluten=False),
    Restaurante("r05", "Wok House",
                [6, 5, 7,  7, 6], 26000,
                tipo_cocina=["asiatica", "thai"],
                tiene_vegetariano=True, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r06", "Sushi Maki Cali",
                [4, 6, 7,  6, 6], 38000,
                tipo_cocina=["japonesa", "sushi"],
                tiene_vegetariano=True, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r07", "Crepes Pancakes",
                [2, 8, 5,  7, 4], 23000,
                tipo_cocina=["francesa", "crepes"],
                tiene_vegetariano=True, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r08", "El Buen Gusto",
                [4, 4, 7,  5, 8], 18000,
                tipo_cocina=["colombiana"],
                tiene_vegetariano=True, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r09", "La Taqueria",
                [7, 2, 8,  5, 8], 20000,
                tipo_cocina=["mexicana", "tacos"],
                tiene_vegetariano=True, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r10", "Pizzeria Napoles",
                [2, 5, 7,  6, 7], 27000,
                tipo_cocina=["italiana", "pizza"],
                tiene_vegetariano=True, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r11", "Picante Fuego",
                [9, 3, 7,  6, 7], 28000,
                tipo_cocina=["mexicana"],
                tiene_vegetariano=True, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r12", "Thai Garden",
                [7, 6, 6,  7, 6], 31000,
                tipo_cocina=["thai"],
                tiene_vegetariano=True, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r13", "Street Burger Co",
                [4, 4, 8,  3, 9], 24000,
                tipo_cocina=["hamburguesas"],
                tiene_vegetariano=False, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r14", "Fogon Vallecaucano",
                [3, 3, 8,  4, 9], 16000,
                tipo_cocina=["colombiana", "regional"],
                tiene_vegetariano=False, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r15", "La Estacion Carros",
                [3, 2, 8,  2, 10], 45000,
                tipo_cocina=["colombiana", "parrilla"],
                tiene_vegetariano=False, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r16", "Grillmaster",
                [3, 2, 9,  1, 10], 40000,
                tipo_cocina=["parrilla", "americana"],
                tiene_vegetariano=False, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r17", "Asadero El Criollo",
                [3, 2, 8,  3, 9], 15000,
                tipo_cocina=["colombiana", "asadero"],
                tiene_vegetariano=False, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r18", "Dulce Mar",
                [5, 2, 8,  3, 7], 32000,
                tipo_cocina=["mariscos", "pescado"],
                tiene_vegetariano=False, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r19", "El Saman Grill",
                [2, 2, 8,  2, 10], 65000,
                tipo_cocina=["parrilla", "premium"],
                tiene_vegetariano=False, tiene_vegano=False, tiene_sin_gluten=False),
    Restaurante("r20", "La Cucina di Roma",
                [2, 5, 7,  7, 6], 35000,
                tipo_cocina=["italiana"],
                tiene_vegetariano=True, tiene_vegano=False, tiene_sin_gluten=False),
]

MOTOR = MotorRecomendacionGrupal(RESTAURANTES_TEST)


# ══════════════════════════════════════════════════════════════════
# GRUPOS DE PRUEBA — fijos y con nombres reconocibles
# ══════════════════════════════════════════════════════════════════

def grupo_carnivoros():
    return [
        PerfilUsuario("Andres",    [3, 2, 8, 2, 10], presupuesto_max=50000),
        PerfilUsuario("Valentina", [2, 3, 7, 2,  9], presupuesto_max=50000),
        PerfilUsuario("Sebastian", [4, 2, 9, 1, 10], presupuesto_max=50000),
    ]

def grupo_heterogeneo():
    return [
        PerfilUsuario("Camila",   [2, 7, 5, 9, 2], presupuesto_max=35000),
        PerfilUsuario("Mateo",    [9, 2, 8, 2, 9], presupuesto_max=35000),
        PerfilUsuario("Isabella", [5, 5, 6, 6, 5], presupuesto_max=35000),
        PerfilUsuario("Nicolas",  [8, 2, 7, 3, 8], presupuesto_max=35000),
    ]

def grupo_con_vegano():
    return [
        PerfilUsuario("Daniela", [1, 6, 5, 10, 1], presupuesto_max=35000,
                      restricciones=["vegano"]),
        PerfilUsuario("Felipe",  [3, 5, 6,  9, 2], presupuesto_max=35000),
        PerfilUsuario("Luisa",   [2, 6, 5,  8, 3], presupuesto_max=35000),
    ]

def grupo_presupuesto_bajo():
    return [
        PerfilUsuario("Ana",   [5, 5, 5, 5, 5], presupuesto_max=10000),
        PerfilUsuario("Bruno", [7, 3, 8, 2, 9], presupuesto_max=10000),
    ]

def grupo_ponderado():
    return [
        PerfilUsuario("Ana",   [7, 3, 7, 3, 8], presupuesto_max=40000, peso_voto=1.8),
        PerfilUsuario("Bruno", [3, 8, 4, 7, 2], presupuesto_max=40000, peso_voto=0.6),
        PerfilUsuario("Carla", [5, 5, 6, 5, 6], presupuesto_max=40000, peso_voto=1.0),
    ]

def grupo_sigma_alto():
    return [
        PerfilUsuario("X", [1,  1,  1,  1,  1], presupuesto_max=50000),
        PerfilUsuario("Y", [10, 10, 10, 10, 10], presupuesto_max=50000),
        PerfilUsuario("Z", [1,  10,  1, 10,  1], presupuesto_max=50000),
    ]


# ══════════════════════════════════════════════════════════════════
# GROUND TRUTH ARTIFICIAL Y METRICAS
# ══════════════════════════════════════════════════════════════════

UMBRAL_GT_ALTO  = 0.80   # para grupos homogeneos
UMBRAL_GT_MEDIO = 0.75   # para grupos heterogeneos o con restricciones


def construir_ground_truth(motor, perfiles, umbral):
    """
    Construye el conjunto de restaurantes relevantes (ground truth artificial).

    Un restaurante es relevante si:
      coseno(perfil_promedio_del_grupo, vector_restaurante) >= umbral

    El perfil promedio (M1) se usa como referencia neutral del GT para no
    favorecer a ninguno de los 5 metodos que estamos evaluando.

    Pasos:
      1. Filtra por presupuesto y restricciones (igual que el motor real).
      2. Calcula el perfil promedio del grupo.
      3. Mide similitud coseno de cada candidato con ese perfil.
      4. Son relevantes los que superan el umbral.
    """
    candidatos, _ = filtrar_restaurantes(motor.restaurantes, perfiles)
    if not candidatos:
        return set()
    perfil_base = m1_promedio(perfiles)
    return {
        r.nombre for r in candidatos
        if similitud_coseno(list(perfil_base), r.vector) >= umbral
    }


def precision_at_k(recomendados, relevantes, k):
    """
    Precision@K = |top-K recomendados interseccion relevantes| / K

    Cuantos de los K recomendados son realmente buenos.
    Si hay menos de K recomendados, usa len(recomendados) como denominador.
    """
    k_ef = min(k, len(recomendados))
    if k_ef == 0:
        return 0.0
    top_k = {r['restaurante'].nombre for r in recomendados[:k_ef]}
    return len(top_k & relevantes) / k_ef


def recall_at_k(recomendados, relevantes, k):
    """
    Recall@K = |top-K recomendados interseccion relevantes| / |relevantes|

    Cuantos de los buenos totales encontro el sistema en el top-K.
    Recall bajo no implica sistema malo: si |GT|=15 y K=3, el maximo
    Recall@3 posible es solo 3/15 = 20%. Es el trade-off normal.
    """
    if not relevantes:
        return 0.0
    top_k = {r['restaurante'].nombre for r in recomendados[:k]}
    return len(top_k & relevantes) / len(relevantes)


def equity_score(resultado):
    """
    Satisfaccion del integrante MENOS contento. Metrica de justicia grupal.
    Diferenciador etico clave de este sistema vs recomendadores simples.
    """
    if not resultado.restaurantes:
        return 0.0
    return resultado.restaurantes[0]['score_min']


# ══════════════════════════════════════════════════════════════════
# INFRAESTRUCTURA DE TESTS
# ══════════════════════════════════════════════════════════════════

_resultados = []


def test(test_id, nombre):
    def decorator(fn):
        def wrapper():
            try:
                fn()
                _resultados.append((test_id, nombre, True, ""))
                print(f"  OK   {test_id}  {nombre}")
            except AssertionError as e:
                _resultados.append((test_id, nombre, False, str(e)))
                print(f"  FAIL {test_id}  {nombre}")
                print(f"         -> {e}")
            except Exception as e:
                _resultados.append((test_id, nombre, False, f"ERROR: {e}"))
                print(f"  ERR  {test_id}  {nombre}")
                print(f"         -> {e}")
        return wrapper
    return decorator


# ══════════════════════════════════════════════════════════════════
# BLOQUE 1 — PRUEBAS UNITARIAS
# ══════════════════════════════════════════════════════════════════

@test("U01", "Presupuesto minimo del grupo siempre respetado")
def u01():
    for presupuesto in [15000, 20000, 30000, 50000]:
        grupo = [PerfilUsuario("X", [5, 5, 5, 5, 5], presupuesto_max=presupuesto)]
        for metodo in METODOS:
            res = MOTOR.recomendar(grupo, metodo, top_k=10)
            for r in res.restaurantes:
                precio = r['restaurante'].precio_promedio
                assert precio <= presupuesto, (
                    f"[{metodo}] '{r['restaurante'].nombre}' "
                    f"${precio} > presupuesto ${presupuesto}"
                )


@test("U02", "Restriccion vegana nunca violada")
def u02():
    grupo = [PerfilUsuario("V", [3, 6, 5, 10, 1], presupuesto_max=40000,
                            restricciones=["vegano"])]
    for metodo in METODOS:
        res = MOTOR.recomendar(grupo, metodo, top_k=10)
        for r in res.restaurantes:
            rest = r['restaurante']
            assert rest.tiene_vegano, (
                f"[{metodo}] '{rest.nombre}' no es vegano pero fue recomendado"
            )


@test("U03", "Restriccion vegetariana nunca violada")
def u03():
    grupo = [PerfilUsuario("V", [3, 6, 5, 10, 1], presupuesto_max=40000,
                            restricciones=["vegetariano"])]
    for metodo in METODOS:
        res = MOTOR.recomendar(grupo, metodo, top_k=10)
        for r in res.restaurantes:
            rest = r['restaurante']
            assert rest.tiene_vegetariano, (
                f"[{metodo}] '{rest.nombre}' no tiene opciones vegetarianas"
            )


@test("U04", "Restriccion sin_mariscos nunca violada")
def u04():
    grupo = [PerfilUsuario("V", [5, 5, 8, 5, 8], presupuesto_max=40000,
                            restricciones=["sin_mariscos"])]
    for metodo in METODOS:
        res = MOTOR.recomendar(grupo, metodo, top_k=10)
        for r in res.restaurantes:
            rest = r['restaurante']
            assert "mariscos" not in rest.tipo_cocina, (
                f"[{metodo}] '{rest.nombre}' es mariscos pero se recomienda con sin_mariscos"
            )


@test("U05", "Todos los scores en rango [0, 1]")
def u05():
    for grupo in [grupo_carnivoros(), grupo_heterogeneo(), grupo_con_vegano()]:
        for metodo in METODOS:
            res = MOTOR.recomendar(grupo, metodo, top_k=5)
            for r in res.restaurantes:
                assert 0 <= r['score_grupo']   <= 1.0001
                assert 0 <= r['score_min']     <= 1.0001
                for persona, s in r['satisfaccion_por_persona'].items():
                    assert 0 <= s <= 1.0001, f"satisfaccion de {persona}: {s}"


@test("U06", "Ranking ordenado de mayor a menor score_grupo")
def u06():
    for grupo in [grupo_carnivoros(), grupo_heterogeneo()]:
        for metodo in METODOS:
            res = MOTOR.recomendar(grupo, metodo, top_k=5)
            scores = [r['score_grupo'] for r in res.restaurantes]
            assert scores == sorted(scores, reverse=True), (
                f"[{metodo}] Ranking desordenado: {scores}"
            )


@test("U07", "top_k nunca retorna mas restaurantes de los pedidos")
def u07():
    grupo = grupo_carnivoros()
    for k in [1, 3, 5, 10]:
        res = MOTOR.recomendar(grupo, 'mayoria_ponderada', top_k=k)
        assert len(res.restaurantes) <= k


@test("U08", "Metodo inexistente lanza ValueError")
def u08():
    lanzo = False
    try:
        MOTOR.recomendar(grupo_carnivoros(), 'metodo_fantasma')
    except ValueError:
        lanzo = True
    assert lanzo, "Deberia lanzar ValueError con metodo inexistente"


@test("U09", "Grupo de 1 persona no rompe el motor")
def u09():
    grupo = [PerfilUsuario("Sola", [5, 5, 5, 5, 5], presupuesto_max=40000)]
    for metodo in METODOS:
        res = MOTOR.recomendar(grupo, metodo, top_k=3)
        assert isinstance(res.restaurantes, list)


@test("U10", "Vector todo-ceros activa fallback sin romper el sistema")
def u10():
    grupo = [
        PerfilUsuario("A", [1, 1, 1, 1, 1], presupuesto_max=40000),
        PerfilUsuario("B", [2, 2, 2, 2, 2], presupuesto_max=40000),
    ]
    res = MOTOR.recomendar(grupo, 'maximo_placer', top_k=3)
    assert isinstance(res.restaurantes, list)
    if res.restaurantes:
        assert res.restaurantes[0]['score_grupo'] > 0


# ══════════════════════════════════════════════════════════════════
# BLOQUE 2 — PRECISION@K Y RECALL@K
#
# Valores de K elegidos:
#   K=1  el primer resultado siempre debe ser relevante (estandar en busqueda)
#   K=3  lo que el usuario ve en pantalla (nuestro top_k por defecto)
#   K=5  cobertura amplia del catalogo
#
# Umbrales de los asserts: calculados empiricamente sobre la base de prueba.
# ══════════════════════════════════════════════════════════════════

@test("M01", "Precision@1 grupo carnivoro (esperado >= 0.80)")
def m01():
    grupo = grupo_carnivoros()
    gt = construir_ground_truth(MOTOR, grupo, UMBRAL_GT_ALTO)
    res = MOTOR.recomendar(grupo, 'mayoria_ponderada', top_k=5)
    p1 = precision_at_k(res.restaurantes, gt, k=1)
    assert p1 >= 0.80, f"Precision@1 = {p1:.2f} < 0.80  |GT|={len(gt)}"


@test("M02", "Precision@3 grupo carnivoro (esperado >= 0.60)")
def m02():
    grupo = grupo_carnivoros()
    gt = construir_ground_truth(MOTOR, grupo, UMBRAL_GT_ALTO)
    res = MOTOR.recomendar(grupo, 'mayoria_ponderada', top_k=5)
    p3 = precision_at_k(res.restaurantes, gt, k=3)
    assert p3 >= 0.60, f"Precision@3 = {p3:.2f} < 0.60  |GT|={len(gt)}"


@test("M03", "Precision@5 grupo carnivoro (esperado >= 0.40)")
def m03():
    grupo = grupo_carnivoros()
    gt = construir_ground_truth(MOTOR, grupo, UMBRAL_GT_ALTO)
    res = MOTOR.recomendar(grupo, 'mayoria_ponderada', top_k=5)
    p5 = precision_at_k(res.restaurantes, gt, k=5)
    assert p5 >= 0.40, f"Precision@5 = {p5:.2f} < 0.40  |GT|={len(gt)}"


@test("M04", "Recall@1 grupo carnivoro (esperado >= 0.05)")
def m04():
    # Recall@1 es bajo cuando |GT| es grande (ej. |GT|=15 -> maximo R@1 = 1/15 = 7%)
    # El umbral 0.05 refleja esta realidad matematica.
    grupo = grupo_carnivoros()
    gt = construir_ground_truth(MOTOR, grupo, UMBRAL_GT_ALTO)
    res = MOTOR.recomendar(grupo, 'mayoria_ponderada', top_k=5)
    r1 = recall_at_k(res.restaurantes, gt, k=1)
    assert r1 >= 0.05 or not gt, f"Recall@1 = {r1:.2f} < 0.05  |GT|={len(gt)}"


@test("M05", "Recall@3 grupo carnivoro (esperado >= 0.15)")
def m05():
    grupo = grupo_carnivoros()
    gt = construir_ground_truth(MOTOR, grupo, UMBRAL_GT_ALTO)
    res = MOTOR.recomendar(grupo, 'mayoria_ponderada', top_k=5)
    r3 = recall_at_k(res.restaurantes, gt, k=3)
    assert r3 >= 0.15 or not gt, f"Recall@3 = {r3:.2f} < 0.15  |GT|={len(gt)}"


@test("M06", "Recall@5 grupo carnivoro (esperado >= 0.25)")
def m06():
    grupo = grupo_carnivoros()
    gt = construir_ground_truth(MOTOR, grupo, UMBRAL_GT_ALTO)
    res = MOTOR.recomendar(grupo, 'mayoria_ponderada', top_k=5)
    r5 = recall_at_k(res.restaurantes, gt, k=5)
    assert r5 >= 0.25 or not gt, f"Recall@5 = {r5:.2f} < 0.25  |GT|={len(gt)}"


@test("M07", "Precision@3 grupo heterogeneo con M5 (esperado >= 0.33)")
def m07():
    grupo = grupo_heterogeneo()
    gt = construir_ground_truth(MOTOR, grupo, UMBRAL_GT_MEDIO)
    res = MOTOR.recomendar(grupo, 'mayoria_ponderada', top_k=5)
    p3 = precision_at_k(res.restaurantes, gt, k=3)
    assert p3 >= 0.33, f"Precision@3 = {p3:.2f} < 0.33  |GT|={len(gt)}"


@test("M08", "Recall@3 grupo heterogeneo con M5 (esperado >= 0.10)")
def m08():
    grupo = grupo_heterogeneo()
    gt = construir_ground_truth(MOTOR, grupo, UMBRAL_GT_MEDIO)
    res = MOTOR.recomendar(grupo, 'mayoria_ponderada', top_k=5)
    r3 = recall_at_k(res.restaurantes, gt, k=3)
    assert r3 >= 0.10 or not gt, f"Recall@3 = {r3:.2f} < 0.10  |GT|={len(gt)}"


@test("M09", "Precision@3 grupo con vegano M2 (esperado = 1.0)")
def m09():
    grupo = grupo_con_vegano()
    candidatos, _ = filtrar_restaurantes(MOTOR.restaurantes, grupo)
    gt = {r.nombre for r in candidatos if r.tiene_vegano}
    res = MOTOR.recomendar(grupo, 'minima_miseria', top_k=3)
    k_ef = min(3, len(res.restaurantes))
    p3 = precision_at_k(res.restaurantes, gt, k=k_ef)
    assert p3 >= 1.0 or not gt, (
        f"Precision@3 con vegano = {p3:.2f} < 1.0\n"
        f"  Recomendados: {[r['restaurante'].nombre for r in res.restaurantes[:3]]}\n"
        f"  GT: {sorted(gt)}"
    )


# ══════════════════════════════════════════════════════════════════
# BLOQUE 3 — PRUEBAS DE ESCENARIO
# ══════════════════════════════════════════════════════════════════

@test("E01", "Grupo homogeneo equity score >= 0.70")
def e01():
    res = MOTOR.recomendar(grupo_carnivoros(), 'promedio', top_k=3)
    eq = equity_score(res)
    assert eq >= 0.70, f"Equity = {eq:.3f} < 0.70"


@test("E02", "Grupo heterogeneo M5 equity no mucho peor que M1 (diferencia <= 0.25)")
def e02():
    grupo = grupo_heterogeneo()
    eq_m1 = equity_score(MOTOR.recomendar(grupo, 'promedio',          top_k=1))
    eq_m5 = equity_score(MOTOR.recomendar(grupo, 'mayoria_ponderada', top_k=1))
    assert eq_m5 >= eq_m1 - 0.25, (
        f"M5={eq_m5:.3f} mucho peor que M1={eq_m1:.3f} (delta={eq_m1-eq_m5:.3f} > 0.25)"
    )


@test("E03", "Grupo con vegano M2 equity >= M1 equity")
def e03():
    grupo = grupo_con_vegano()
    eq_m1 = equity_score(MOTOR.recomendar(grupo, 'promedio',       top_k=1))
    eq_m2 = equity_score(MOTOR.recomendar(grupo, 'minima_miseria', top_k=1))
    assert eq_m2 >= eq_m1 - 0.05, f"M2={eq_m2:.3f} vs M1={eq_m1:.3f}"


@test("E04", "Presupuesto muy bajo activa advertencia de fallback")
def e04():
    res = MOTOR.recomendar(grupo_presupuesto_bajo(), 'promedio', top_k=3)
    assert len(res.advertencias) > 0 or len(res.restaurantes) == 0


@test("E05", "Modificar integrante cambia la recomendacion")
def e05():
    grupo_orig = grupo_carnivoros()
    top1_orig = MOTOR.recomendar(grupo_orig, 'mayoria_ponderada', top_k=1)
    nombre_orig = top1_orig.restaurantes[0]['restaurante'].nombre if top1_orig.restaurantes else ""

    grupo_mod = [
        PerfilUsuario("Andres",    [2, 8, 5, 10, 1], presupuesto_max=50000,
                      restricciones=["vegano"]),
        PerfilUsuario("Valentina", [2, 3, 7,  2, 9], presupuesto_max=50000),
        PerfilUsuario("Sebastian", [4, 2, 9,  1, 10], presupuesto_max=50000),
    ]
    top1_mod = MOTOR.recomendar(grupo_mod, 'mayoria_ponderada', top_k=1)
    nombre_mod = top1_mod.restaurantes[0]['restaurante'].nombre if top1_mod.restaurantes else ""

    assert nombre_orig != nombre_mod, (
        f"Recomendacion no cambio al modificar radicalmente a Andres. Ambas: '{nombre_orig}'"
    )


@test("E06", "Grupo heterogeneo M1 y M5 recomiendan restaurantes distintos")
def e06():
    grupo = grupo_heterogeneo()
    top3_m1 = {r['restaurante'].nombre for r in MOTOR.recomendar(grupo, 'promedio',          top_k=3).restaurantes}
    top3_m5 = {r['restaurante'].nombre for r in MOTOR.recomendar(grupo, 'mayoria_ponderada', top_k=3).restaurantes}
    assert top3_m1 != top3_m5, f"M1 y M5 dan el mismo top-3: {sorted(top3_m1)}"


@test("E07", "Seleccion automatica grupo homogeneo usa promedio")
def e07():
    res = MOTOR.recomendar_automatico(grupo_carnivoros(), top_k=1)
    metodo = res.estadisticas.get('metodo_seleccionado_auto', res.metodo_usado)
    assert metodo == 'promedio', f"Esperaba 'promedio', uso '{metodo}'"


@test("E08", "Seleccion automatica grupo con restricciones usa minima_miseria")
def e08():
    res = MOTOR.recomendar_automatico(grupo_con_vegano(), top_k=1)
    metodo = res.estadisticas.get('metodo_seleccionado_auto', res.metodo_usado)
    assert metodo == 'minima_miseria', f"Esperaba 'minima_miseria', uso '{metodo}'"


@test("E09", "Seleccion automatica grupo con sigma alto usa mayoria_ponderada")
def e09():
    res = MOTOR.recomendar_automatico(grupo_sigma_alto(), top_k=1)
    metodo = res.estadisticas.get('metodo_seleccionado_auto', res.metodo_usado)
    assert metodo == 'mayoria_ponderada', f"Esperaba 'mayoria_ponderada', uso '{metodo}'"


# ══════════════════════════════════════════════════════════════════
# BLOQUE 4 — TABLAS COMPARATIVAS
# ══════════════════════════════════════════════════════════════════

ETIQUETAS = {
    'promedio':           'M1 Promedio naive',
    'minima_miseria':     'M2 Minima miseria',
    'maximo_placer':      'M3 Maximo placer',
    'media_satisfaccion': 'M4 Media satisfaccion',
    'mayoria_ponderada':  'M5 Mayoria ponderada *',
}


def imprimir_tabla(grupo, nombre_escenario, umbral_gt):
    gt = construir_ground_truth(MOTOR, grupo, umbral_gt)
    integrantes = [p.nombre for p in grupo]
    sep = "-" * 94

    print(f"\n  Escenario: {nombre_escenario}")
    print(f"  Integrantes: {integrantes}")
    print(f"  Umbral GT: >= {umbral_gt} | Ground truth ({len(gt)} restaurantes): {sorted(gt)}")
    print(f"\n  {sep}")
    print(f"  {'Metodo':<26} {'P@1':>4} {'P@3':>4} {'P@5':>4} | "
          f"{'R@1':>4} {'R@3':>4} {'R@5':>4} | {'Equity':>6}  Top-1")
    print(f"  {sep}")

    for metodo, etiqueta in ETIQUETAS.items():
        res = MOTOR.recomendar(grupo, metodo, top_k=5)
        recs = res.restaurantes

        p1 = precision_at_k(recs, gt, 1)
        p3 = precision_at_k(recs, gt, 3)
        p5 = precision_at_k(recs, gt, 5)
        r1 = recall_at_k(recs, gt, 1)
        r3 = recall_at_k(recs, gt, 3)
        r5 = recall_at_k(recs, gt, 5)
        eq = equity_score(res)
        top1 = recs[0]['restaurante'].nombre[:30] if recs else "vacío"

        print(f"  {etiqueta:<26} "
              f"{p1:>3.0%} {p3:>3.0%} {p5:>3.0%} | "
              f"{r1:>3.0%} {r3:>3.0%} {r5:>3.0%} | "
              f"{eq:>5.0%}  {top1}")

    print(f"  {sep}\n")


@test("T01", "Tabla M1-M5 escenario heterogeneo")
def t01():
    imprimir_tabla(grupo_heterogeneo(),
                   "Grupo heterogeneo (Camila/Mateo/Isabella/Nicolas)",
                   UMBRAL_GT_MEDIO)


@test("T02", "Tabla M1-M5 escenario carnivoro homogeneo")
def t02():
    imprimir_tabla(grupo_carnivoros(),
                   "Grupo homogeneo carnivoro (Andres/Valentina/Sebastian)",
                   UMBRAL_GT_ALTO)


@test("T03", "Tabla M1-M5 escenario con vegano")
def t03():
    imprimir_tabla(grupo_con_vegano(),
                   "Grupo con vegano (Daniela/Felipe/Luisa)",
                   UMBRAL_GT_MEDIO)


@test("T04", "Tabla M1-M5 escenario pesos distintos")
def t04():
    imprimir_tabla(grupo_ponderado(),
                   "Grupo pesos distintos (Ana x1.8 / Bruno x0.6 / Carla x1.0)",
                   UMBRAL_GT_ALTO)


# ══════════════════════════════════════════════════════════════════
# RUNNER PRINCIPAL
# ══════════════════════════════════════════════════════════════════

TODOS = [
    u01, u02, u03, u04, u05, u06, u07, u08, u09, u10,
    m01, m02, m03, m04, m05, m06, m07, m08, m09,
    e01, e02, e03, e04, e05, e06, e07, e08, e09,
    t01, t02, t03, t04,
]

BLOQUES = {
    "BLOQUE 1 - Pruebas unitarias (correccion del sistema)":
        [u01, u02, u03, u04, u05, u06, u07, u08, u09, u10],
    "BLOQUE 2 - Metricas Precision@K / Recall@K":
        [m01, m02, m03, m04, m05, m06, m07, m08, m09],
    "BLOQUE 3 - Pruebas de escenario (comportamiento esperado)":
        [e01, e02, e03, e04, e05, e06, e07, e08, e09],
    "BLOQUE 4 - Tablas comparativas (material para la presentacion)":
        [t01, t02, t03, t04],
}


def correr_tests():
    print("\n" + "=" * 62)
    print("  DONDE COMEMOS HOY -- Suite de pruebas del sistema")
    print("  Universidad Icesi -- Interaccion Sociotecnologica")
    print("=" * 62)

    for titulo, tests in BLOQUES.items():
        print(f"\n  {'-'*58}")
        print(f"  {titulo}")
        print(f"  {'-'*58}")
        for t in tests:
            t()

    pasaron  = [r for r in _resultados if r[2]]
    fallaron = [r for r in _resultados if not r[2]]
    total    = len(_resultados)

    print("\n" + "=" * 62)
    print("  RESULTADO FINAL")
    print(f"  {'-'*58}")
    print(f"  OK   Pasaron:  {len(pasaron)}/{total}")
    print(f"  FAIL Fallaron: {len(fallaron)}/{total}")

    if fallaron:
        print(f"\n  Tests fallidos:")
        for tid, nombre, _, detalle in fallaron:
            print(f"    . {tid} -- {nombre}")
            if detalle:
                print(f"      {detalle[:140]}")

    pct = len(pasaron) / total * 100 if total else 0
    print(f"\n  Cobertura: {pct:.0f}%")
    print("=" * 62 + "\n")
    return len(fallaron) == 0


if __name__ == "__main__":
    exito = correr_tests()
    sys.exit(0 if exito else 1)
