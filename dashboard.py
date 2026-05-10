"""
Consultas de la base de datos de ofertas procesadas.
Ejecutar directamente:  python dashboard.py [comando]

Comandos:
  python dashboard.py          → resumen general
  python dashboard.py pending  → ofertas pendientes de acción
  python dashboard.py applied  → candidaturas enviadas
  python dashboard.py all      → todas las ofertas (últimos 30 días)
  python dashboard.py stats    → estadísticas por portal y categoría
"""
import sys
import os
from datetime import datetime, timedelta
from database import _connection, _ph

BOLD  = '\033[1m'
RESET = '\033[0m'
GREEN = '\033[32m'
YELLOW= '\033[33m'
CYAN  = '\033[36m'
RED   = '\033[31m'


def _status_icon(status: str) -> str:
    return {
        'pending':          '⏳',
        'applied':          '✅',
        'applied_auto':     '✉️ ',
        'applied_external': '🔗',
        'discarded':        '❌',
    }.get(status, '❓')


def _fmt_row(j: dict) -> str:
    icon  = _status_icon(j.get('estado', ''))
    fecha = j.get('fecha', '')[:16]
    score = j.get('score', '-')
    score_str = f'[{score}/10]' if score != '-' else '[  -  ]'
    return (
        f"{icon} {score_str} {fecha}  "
        f"{j.get('puesto', '')[:45]:<45}  "
        f"{j.get('empresa', '')[:25]:<25}  "
        f"{j.get('portal', ''):<15}  "
        f"{j.get('categoria', '')}"
    )


def resumen():
    cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM seen_jobs')
        total_vistas = cur.fetchone()[0]

        cur.execute(
            f'SELECT estado, COUNT(*) FROM candidaturas WHERE fecha >= {_ph()} GROUP BY estado',
            (cutoff,)
        )
        por_estado = dict(cur.fetchall())

    print(f'\n{BOLD}=== Job Hunter v2 — BBDD Ofertas ==={RESET}')
    print(f'Total ofertas procesadas (histórico): {BOLD}{total_vistas}{RESET}')
    print(f'\nÚltimos 30 días:')
    for estado, icon in [('pending','⏳'), ('applied','✅'), ('applied_auto','✉️ '), ('discarded','❌')]:
        n = por_estado.get(estado, 0)
        print(f'  {icon} {estado:<15} {n}')
    total_30 = sum(por_estado.values())
    print(f'  {"Total":<17} {total_30}')


def listar(estado_filtro: str | None = None, dias: int = 30):
    cutoff = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
    ph = _ph()
    with _connection() as conn:
        cur = conn.cursor()
        if estado_filtro:
            cur.execute(
                f'SELECT fecha, empresa, puesto, portal, categoria, score, estado, url '
                f'FROM candidaturas WHERE fecha >= {ph} AND estado = {ph} ORDER BY fecha DESC',
                (cutoff, estado_filtro)
            )
        else:
            cur.execute(
                f'SELECT fecha, empresa, puesto, portal, categoria, score, estado, url '
                f'FROM candidaturas WHERE fecha >= {ph} ORDER BY fecha DESC',
                (cutoff,)
            )
        rows = cur.fetchall()

    cols = ['fecha', 'empresa', 'puesto', 'portal', 'categoria', 'score', 'estado', 'url']
    jobs = [dict(zip(cols, r)) for r in rows]

    titulo = f'Candidaturas: {estado_filtro or "todas"} (últimos {dias} días) — {len(jobs)} registros'
    print(f'\n{BOLD}{titulo}{RESET}')
    print('-' * 120)
    header = (
        f"{'ST':<4} {'Score':<7} {'Fecha':<16}  "
        f"{'Puesto':<45}  {'Empresa':<25}  {'Portal':<15}  Categoría"
    )
    print(f'{CYAN}{header}{RESET}')
    print('-' * 120)
    for j in jobs:
        print(_fmt_row(j))
    print('-' * 120)


def estadisticas():
    with _connection() as conn:
        cur = conn.cursor()

        cur.execute('SELECT portal, COUNT(*) FROM candidaturas GROUP BY portal ORDER BY COUNT(*) DESC')
        por_portal = cur.fetchall()

        cur.execute('SELECT categoria, COUNT(*), AVG(score) FROM candidaturas GROUP BY categoria ORDER BY COUNT(*) DESC')
        por_cat = cur.fetchall()

        cur.execute('SELECT AVG(score), MIN(score), MAX(score) FROM candidaturas WHERE score > 0')
        score_stats = cur.fetchone()

    print(f'\n{BOLD}=== Estadísticas ==={RESET}')

    print(f'\n{BOLD}Por portal:{RESET}')
    for portal, n in por_portal:
        bar = '█' * min(n, 40)
        print(f'  {portal:<20} {n:>4}  {bar}')

    print(f'\n{BOLD}Por categoría:{RESET}')
    for cat, n, avg_score in por_cat:
        avg_str = f'{avg_score:.1f}' if avg_score else ' — '
        print(f'  {cat:<25} {n:>4} ofertas  avg score: {avg_str}')

    if score_stats and score_stats[0]:
        print(f'\n{BOLD}Scoring IA:{RESET}')
        print(f'  Media: {score_stats[0]:.1f}  |  Mín: {score_stats[1]}  |  Máx: {score_stats[2]}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''

    if cmd == 'pending':
        listar('pending')
    elif cmd == 'applied':
        listar('applied')
        listar('applied_auto')
    elif cmd == 'all':
        listar()
    elif cmd == 'stats':
        estadisticas()
    else:
        resumen()
        print(f'\n{YELLOW}Comandos: pending · applied · all · stats{RESET}')
