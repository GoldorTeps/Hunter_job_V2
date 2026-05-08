"""
Tracking de candidaturas.
Guarda en PostgreSQL (Railway) y en candidaturas.csv (local).
"""
import csv
import os
from datetime import datetime
from database import _connection, _ph, _use_postgres

CSV_PATH = os.path.join(os.path.dirname(__file__), 'candidaturas.csv')

COLUMNS = ['fecha', 'empresa', 'puesto', 'portal', 'categoria', 'score', 'estado', 'url', 'job_id']

STATUS_PENDING         = 'pending'
STATUS_APPLIED         = 'applied'
STATUS_DISCARDED       = 'discarded'


def init_tracker():
    with _connection() as conn:
        conn.cursor().execute('''
            CREATE TABLE IF NOT EXISTS candidaturas (
                id        SERIAL PRIMARY KEY,
                fecha     TEXT,
                empresa   TEXT,
                puesto    TEXT,
                portal    TEXT,
                categoria TEXT,
                score     INTEGER DEFAULT 0,
                estado    TEXT DEFAULT 'pending',
                url       TEXT,
                job_id    TEXT
            )
        ''') if _use_postgres() else conn.cursor().execute('''
            CREATE TABLE IF NOT EXISTS candidaturas (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha     TEXT,
                empresa   TEXT,
                puesto    TEXT,
                portal    TEXT,
                categoria TEXT,
                score     INTEGER DEFAULT 0,
                estado    TEXT DEFAULT 'pending',
                url       TEXT,
                job_id    TEXT
            )
        ''')

    try:
        with _connection() as conn:
            if _use_postgres():
                conn.cursor().execute('ALTER TABLE candidaturas ADD COLUMN IF NOT EXISTS job_id TEXT')
                conn.cursor().execute('ALTER TABLE candidaturas ADD COLUMN IF NOT EXISTS score INTEGER DEFAULT 0')
            else:
                for col in ['job_id TEXT', 'score INTEGER DEFAULT 0']:
                    try:
                        conn.cursor().execute(f'ALTER TABLE candidaturas ADD COLUMN {col}')
                    except Exception:
                        pass
    except Exception:
        pass

    _ensure_csv_header()


def _ensure_csv_header():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writeheader()


def track(job: dict, status: str = STATUS_PENDING):
    row = {
        'fecha':     datetime.now().strftime('%Y-%m-%d %H:%M'),
        'empresa':   job.get('company', ''),
        'puesto':    job.get('title', ''),
        'portal':    job.get('source', ''),
        'categoria': job.get('category', ''),
        'score':     job.get('score', 0),
        'estado':    status,
        'url':       job.get('url', ''),
        'job_id':    job.get('id', ''),
    }

    try:
        ph = _ph()
        with _connection() as conn:
            conn.cursor().execute(
                f'''INSERT INTO candidaturas
                    (fecha, empresa, puesto, portal, categoria, score, estado, url, job_id)
                    VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})''',
                tuple(row.values())
            )
    except Exception as e:
        print(f'[Tracker] Error DB: {e}')

    try:
        _ensure_csv_header()
        with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
            csv.DictWriter(f, fieldnames=COLUMNS).writerow(row)
    except Exception as e:
        print(f'[Tracker] Error CSV: {e}')

    print(f'[Tracker] ✔ {row["puesto"]} — {row["empresa"]} (score={row["score"]}, {status})')


def update_status(job_id: str, status: str):
    if not job_id:
        return
    try:
        ph = _ph()
        with _connection() as conn:
            conn.cursor().execute(
                f'UPDATE candidaturas SET estado = {ph} WHERE job_id = {ph}',
                (status, job_id)
            )
        print(f'[Tracker] Estado → {status} para job_id={job_id}')
    except Exception as e:
        print(f'[Tracker] Error update_status: {e}')


def today_jobs() -> list:
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        ph = _ph()
        with _connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f'''SELECT empresa, puesto, portal, categoria, score, estado, url, job_id
                    FROM candidaturas WHERE fecha LIKE {ph}''',
                (f'{today}%',)
            )
            rows = cur.fetchall()
        cols = ['empresa', 'puesto', 'portal', 'categoria', 'score', 'status', 'url', 'job_id']
        return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        print(f'[Tracker] Error today_jobs: {e}')
        return []
