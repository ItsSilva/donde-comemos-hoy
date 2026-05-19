"""
demo.py — Demostración completa del sistema ¿Dónde comemos hoy?
============================================================
Ejecutar: python demo.py

Muestra:
  1. Recomendación individual (1 persona)
  2. Recomendación grupal con los 5 métodos comparados
  3. Escenario con restricciones dietarias y presupuesto ajustado
  4. Selección automática de método según homogeneidad del grupo
  5. Análisis de robustez (100 grupos aleatorios)
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from core.motor_recomendacion import MotorRecomendacionGrupal, PerfilUsuario, DIMS
from data.base_datos import cargar_restaurantes

# ─────────────────────────────────────────────────────────────────
# Datos de prueba (sin conexión a BD)
# ─────────────────────────────────────────────────────────────────

def grupo_carnivoros():
    """Grupo homogéneo — todos amantes de la carne."""
    return [
        PerfilUsuario("Andrés",   [3, 2, 8, 2, 10], presupuesto_max=40000),
        PerfilUsuario("Valentina",[2, 3, 7, 2, 9],  presupuesto_max=45000),
        PerfilUsuario("Sebastián",[4, 2, 9, 1, 10], presupuesto_max=50000),
    ]

def grupo_heterogeneo():
    """Grupo heterogéneo — gustos muy distintos."""
    return [
        PerfilUsuario("Camila",  [2, 7, 5, 9, 2],  presupuesto_max=25000, restricciones=['vegetariano']),
        PerfilUsuario("Mateo",   [9, 2, 8, 2, 9],  presupuesto_max=35000),
        PerfilUsuario("Isabella",[5, 5, 6, 6, 5],  presupuesto_max=30000),
        PerfilUsuario("Nicolás", [8, 2, 7, 3, 8],  presupuesto_max=20000),
    ]

def grupo_ajustado():
    """Grupo con presupuesto bajo y vegano."""
    return [
        PerfilUsuario("Daniela", [1, 6, 5, 10, 1], presupuesto_max=22000, restricciones=['vegano']),
        PerfilUsuario("Felipe",  [3, 5, 6, 9, 2],  presupuesto_max=20000, restricciones=['vegetariano']),
        PerfilUsuario("Luisa",   [2, 6, 5, 8, 3],  presupuesto_max=25000),
    ]

def grupo_grande():
    """Grupo grande con pesos distintos (M5 ponderado)."""
    return [
        PerfilUsuario("Ana",     [7, 3, 7, 3, 8],  peso_voto=1.5),  # cedió más la última vez
        PerfilUsuario("Bruno",   [3, 8, 4, 7, 2],  peso_voto=0.8),
        PerfilUsuario("Carla",   [5, 5, 6, 5, 6],  peso_voto=1.0),
        PerfilUsuario("David",   [9, 2, 8, 2, 9],  peso_voto=0.7),
        PerfilUsuario("Elena",   [2, 7, 5, 8, 3],  peso_voto=1.2),
    ]


# ─────────────────────────────────────────────────────────────────
# FUNCIONES DE DEMOSTRACIÓN
# ─────────────────────────────────────────────────────────────────

SEP = "═" * 60

def banner(titulo: str):
    print(f"\n{SEP}")
    print(f"  {titulo}")
    print(SEP)

def imprimir_resultado(resultado, mostrar_satisfaccion: bool = True):
    metodo_labels = {
        'promedio':           'M1 — Promedio naive',
        'minima_miseria':     'M2 — Mínima miseria',
        'maximo_placer':      'M3 — Máximo placer',
        'media_satisfaccion': 'M4 — Media satisfacción',
        'mayoria_ponderada':  'M5 — Mayoría ponderada ★',
    }
    print(f"\nGrupo: {resultado.grupo}")
    print(f"Método usado: {metodo_labels.get(resultado.metodo_usado, resultado.metodo_usado)}")
    perfil_str = {d: round(v, 1) for d, v in zip(DIMS, resultado.perfil_n)}
    print(f"Perfil N del grupo: {perfil_str}")

    if resultado.advertencias:
        for adv in resultado.advertencias:
            print(f"  {adv}")

    print(f"\n{'#':>3}  {'Restaurante':<28} {'Score':>6} {'Min':>6}  Tipo")
    print("─" * 65)
    for i, r in enumerate(resultado.restaurantes, 1):
        rest = r['restaurante']
        print(f"  {i}.  {rest.nombre:<28} {r['score_grupo']:>5.2%} {r['score_min']:>5.2%}"
              f"  {', '.join(rest.tipo_cocina[:2]) if rest.tipo_cocina else '—'}")
        if mostrar_satisfaccion and i == 1:
            sat = r['satisfaccion_por_persona']
            for persona, score in sorted(sat.items(), key=lambda x: x[1], reverse=True):
                barra = '█' * int(score * 20)
                print(f"       {persona:<12} {score:.2%}  {barra}")

    stats = resultado.estadisticas
    print(f"\n  Diversidad grupal: {stats.get('diversidad', 0):.0%}  |  "
          f"σ global: {stats.get('sigma_grupal', 0):.2f}")


def demo_1_individual():
    banner("DEMO 1 — Recomendación individual (1 persona)")
    restaurantes = cargar_restaurantes()
    motor = MotorRecomendacionGrupal(restaurantes)

    perfil = [PerfilUsuario("Sofía", [8, 2, 7, 2, 9], presupuesto_max=40000)]
    resultado = motor.recomendar(perfil, metodo='promedio', top_k=3)
    imprimir_resultado(resultado)


def demo_2_comparar_metodos():
    banner("DEMO 2 — Comparación de los 5 métodos (grupo heterogéneo)")
    restaurantes = cargar_restaurantes()
    motor = MotorRecomendacionGrupal(restaurantes)
    grupo = grupo_heterogeneo()

    print(f"\nIntegrantes del grupo:")
    for p in grupo:
        print(f"  {p.nombre:<12} {dict(zip(DIMS, p.vector))}  ${p.presupuesto_max:,}")

    comparativa = motor.comparar_metodos(grupo, top_k=3)

    print(f"\n{'Método':<25} {'Top 1':<30} {'Score':>6} {'Score Min':>9}")
    print("─" * 75)
    for metodo, datos in comparativa.items():
        etiqueta = {
            'promedio': 'M1 Promedio',
            'minima_miseria': 'M2 Mín. miseria',
            'maximo_placer': 'M3 Máx. placer',
            'media_satisfaccion': 'M4 Media σ',
            'mayoria_ponderada': 'M5 May. ponderada ★',
        }.get(metodo, metodo)
        adv = ' ⚠️' if datos['advertencias'] else ''
        print(f"  {etiqueta:<23} {datos['top_1']:<30} {datos['score_top_1']:>5.2%} "
              f"{datos['score_min_top_1']:>8.2%}{adv}")


def demo_3_restricciones():
    banner("DEMO 3 — Grupo con restricciones dietarias y presupuesto bajo")
    restaurantes = cargar_restaurantes()
    motor = MotorRecomendacionGrupal(restaurantes)
    grupo = grupo_ajustado()

    print(f"\nIntegrantes:")
    for p in grupo:
        print(f"  {p.nombre:<12} restricciones={p.restricciones}  ${p.presupuesto_max:,}")

    resultado = motor.recomendar(grupo, metodo='minima_miseria', top_k=3)
    imprimir_resultado(resultado)


def demo_4_automatico():
    banner("DEMO 4 — Selección automática de método")
    restaurantes = cargar_restaurantes()
    motor = MotorRecomendacionGrupal(restaurantes)

    for nombre, grupo in [
        ("Grupo homogéneo (carnívoros)",   grupo_carnivoros()),
        ("Grupo heterogéneo",              grupo_heterogeneo()),
        ("Grupo con restricciones veganas", grupo_ajustado()),
    ]:
        resultado = motor.recomendar_automatico(grupo, top_k=1)
        metodo = resultado.estadisticas.get('metodo_seleccionado_auto', resultado.metodo_usado)
        razon  = resultado.estadisticas.get('razon_seleccion', '')
        top1   = resultado.restaurantes[0]['restaurante'].nombre if resultado.restaurantes else '∅'
        sigma  = resultado.estadisticas.get('sigma_grupal', 0)
        print(f"\n  📍 {nombre}")
        print(f"     Método auto: {metodo} ({razon}, σ={sigma})")
        print(f"     Top 1: {top1}")


def demo_5_ponderado():
    banner("DEMO 5 — Método propio M5: mayoría ponderada (pesos distintos)")
    restaurantes = cargar_restaurantes()
    motor = MotorRecomendacionGrupal(restaurantes)
    grupo = grupo_grande()

    print(f"\nIntegrantes con pesos de voto:")
    for p in grupo:
        print(f"  {p.nombre:<12} vector={p.vector}  peso={p.peso_voto}")

    resultado = motor.recomendar(grupo, metodo='mayoria_ponderada', top_k=3)
    imprimir_resultado(resultado)


def demo_6_robustez():
    banner("DEMO 6 — Análisis de robustez (50 grupos aleatorios)")
    restaurantes = cargar_restaurantes()
    motor = MotorRecomendacionGrupal(restaurantes)

    np.random.seed(42)
    metodos = list({'promedio', 'minima_miseria', 'maximo_placer',
                    'media_satisfaccion', 'mayoria_ponderada'})
    vacios = {m: 0 for m in metodos}
    scores_min = {m: [] for m in metodos}

    for _ in range(50):
        n = np.random.randint(2, 6)
        grupo = [
            PerfilUsuario(
                nombre=f"P{i}",
                vector=np.random.uniform(1, 10, 5).round(1).tolist(),
                presupuesto_max=np.random.randint(15000, 60000),
            )
            for i in range(n)
        ]
        for m in metodos:
            res = motor.recomendar(grupo, metodo=m, top_k=1)
            if not res.restaurantes:
                vacios[m] += 1
            else:
                scores_min[m].append(res.restaurantes[0]['score_min'])

    print(f"\n{'Método':<25} {'Vacíos/50':>10} {'Score min prom':>15}")
    print("─" * 53)
    for m in sorted(vacios, key=lambda x: vacios[x]):
        avg = f"{np.mean(scores_min[m]):.3f}" if scores_min[m] else "N/A"
        etiq = {'promedio':'M1 Promedio','minima_miseria':'M2 Mín. miseria',
                'maximo_placer':'M3 Máx. placer','media_satisfaccion':'M4 Media σ',
                'mayoria_ponderada':'M5 Mayoría pond. ★'}.get(m, m)
        print(f"  {etiq:<23} {vacios[m]:>10}    {avg:>12}")


# ─────────────────────────────────────────────────────────────────
# EJECUTAR TODAS LAS DEMOS
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("\n" + "🍽️  ¿DÓNDE COMEMOS HOY? — Sistema de Recomendación Grupal  🍽️".center(60))
    print("Universidad Icesi · Interacción Sociotecnológica".center(60))

    demo_1_individual()
    demo_2_comparar_metodos()
    demo_3_restricciones()
    demo_4_automatico()
    demo_5_ponderado()
    demo_6_robustez()

    print(f"\n\n{'=' * 60}")
    print("  ✅ Todas las demos ejecutadas correctamente")
    print(f"{'=' * 60}\n")
