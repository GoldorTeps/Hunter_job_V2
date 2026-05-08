import time
import threading
import traceback
from datetime import datetime

import requests
import schedule

from config import CHECK_INTERVAL_MIN, DIGEST_HOUR, ACTIVE_HOUR_START, ACTIVE_HOUR_END, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from database import init_db, is_seen, mark_seen, stats, save_pending, load_all_pending, delete_pending
from scraper import run_all_searches
from notifier import (
    send_startup, send_job_alert, send_applied_followup,
    send_daily_digest, send_error, answer_callback,
)
from ai_assistant import enrich_job
from tracker import (
    init_tracker, track, update_status, today_jobs,
    STATUS_PENDING, STATUS_APPLIED, STATUS_DISCARDED,
)

_pending_jobs: dict = {}


def _is_active_hour() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    if now.hour < ACTIVE_HOUR_START or now.hour > ACTIVE_HOUR_END:
        return False
    return True


def _now():
    return datetime.now().strftime('%H:%M:%S')


# ── Callbacks de Telegram ────────────────────────────────────────────────────

def _handle_callback(cb: dict):
    data  = cb.get('data', '')
    cb_id = cb['id']

    if data.startswith('apply_'):
        job_id = data[len('apply_'):]
        job = _pending_jobs.get(job_id)
        if not job:
            answer_callback(cb_id, '⚠️ Oferta expirada (bot reiniciado). Usa el enlace.')
            return
        answer_callback(cb_id, '🔗 Abriendo oferta...')
        send_applied_followup(job)

    elif data.startswith('done_'):
        job_id = data[len('done_'):]
        answer_callback(cb_id, '✅ Registrada como aplicada.')
        update_status(job_id, STATUS_APPLIED)
        _pending_jobs.pop(job_id, None)
        delete_pending(job_id)

    elif data.startswith('discard_'):
        job_id = data[len('discard_'):]
        answer_callback(cb_id, '❌ Descartada.')
        update_status(job_id, STATUS_DISCARDED)
        _pending_jobs.pop(job_id, None)
        delete_pending(job_id)


def _poll_callbacks():
    """Hilo secundario: escucha callback queries mediante long-polling."""
    api    = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'
    offset = 0

    while True:
        try:
            r = requests.post(
                f'{api}/getUpdates',
                json={'offset': offset, 'timeout': 30, 'allowed_updates': ['callback_query']},
                timeout=35,
            )
            if not r.ok:
                time.sleep(5)
                continue

            for update in r.json().get('result', []):
                offset = update['update_id'] + 1
                if 'callback_query' in update:
                    try:
                        _handle_callback(update['callback_query'])
                    except Exception as e:
                        print(f'[Callbacks] Error: {e}')

        except Exception as e:
            print(f'[Callbacks] Error en poll: {e}')
            time.sleep(5)


# ── Loop principal ───────────────────────────────────────────────────────────

def check_jobs():
    print(f'[{_now()}] Buscando...')
    try:
        jobs     = run_all_searches()
        new_jobs = []

        for job in jobs:
            if is_seen(job['id']):
                continue

            enriched = enrich_job(job)
            mark_seen(job)

            if enriched is None:
                continue

            track(enriched, status=STATUS_PENDING)
            _pending_jobs[enriched['id']] = enriched
            save_pending(enriched['id'], enriched)

            if _is_active_hour():
                send_job_alert(enriched)

            new_jobs.append(enriched)
            time.sleep(0.5)

        print(f'[{_now()}] {len(new_jobs)} nuevas relevantes / {len(jobs)} encontradas')

    except Exception as e:
        err = traceback.format_exc()
        print(f'[ERROR] {err}')
        send_error(str(e))


def daily_digest():
    print(f'[{_now()}] Enviando resumen diario...')
    try:
        jobs = today_jobs()
        send_daily_digest(
            applied   =[j for j in jobs if j['status'] == STATUS_APPLIED],
            discarded =[j for j in jobs if j['status'] == STATUS_DISCARDED],
            pending   =[j for j in jobs if j['status'] == STATUS_PENDING],
            db_stats  =stats(),
        )
    except Exception as e:
        err = traceback.format_exc()
        print(f'[ERROR digest] {err}')
        send_error(str(e))


if __name__ == '__main__':
    print('🚀 Job Hunter v2 — Dev Edition arrancando...')
    init_db()
    init_tracker()

    # AJ-2: repoblar _pending_jobs desde DB para sobrevivir reinicios
    recovered = load_all_pending()
    _pending_jobs.update(recovered)
    if recovered:
        print(f'[Pending] {len(recovered)} ofertas recuperadas de DB.')

    send_startup()

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        t = threading.Thread(target=_poll_callbacks, daemon=True, name='callbacks')
        t.start()
        print('✅ Hilo de callbacks activo.')

    check_jobs()

    schedule.every(CHECK_INTERVAL_MIN).minutes.do(check_jobs)
    schedule.every().day.at(f'{DIGEST_HOUR:02d}:00').do(daily_digest)

    print(f'✅ Buscando cada {CHECK_INTERVAL_MIN} min · Resumen a las {DIGEST_HOUR}:00 h')

    while True:
        schedule.run_pending()
        time.sleep(60)
