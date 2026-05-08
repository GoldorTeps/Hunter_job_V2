import os
import sqlite3
from contextlib import contextmanager

DATABASE_URL = os.getenv('DATABASE_URL', '')


def _pg_url():
    url = DATABASE_URL
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url


def _use_postgres():
    return bool(DATABASE_URL)


@contextmanager
def _connection():
    if _use_postgres():
        import psycopg2
        conn = psycopg2.connect(_pg_url())
    else:
        conn = sqlite3.connect('jobs.db')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ph():
    return '%s' if _use_postgres() else '?'


def init_db():
    with _connection() as conn:
        conn.cursor().execute('''
            CREATE TABLE IF NOT EXISTS seen_jobs (
                job_id   TEXT PRIMARY KEY,
                title    TEXT,
                company  TEXT,
                location TEXT,
                url      TEXT,
                category TEXT,
                source   TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    print('[DB] Inicializada correctamente.')


def is_seen(job_id: str) -> bool:
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(f'SELECT 1 FROM seen_jobs WHERE job_id = {_ph()}', (job_id,))
        return cur.fetchone() is not None


def mark_seen(job: dict):
    with _connection() as conn:
        ph = _ph()
        conn.cursor().execute(
            f'''INSERT INTO seen_jobs (job_id, title, company, location, url, category, source)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})
                ON CONFLICT (job_id) DO NOTHING''',
            (job['id'], job['title'], job['company'],
             job['location'], job['url'], job['category'], job['source'])
        )


def stats() -> dict:
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM seen_jobs')
        total = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM seen_jobs WHERE found_at >= CURRENT_DATE')
        today = cur.fetchone()[0]
    return {'total': total, 'today': today}
