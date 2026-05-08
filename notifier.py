import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

API = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'


def _post(text: str, parse_mode: str = 'HTML', reply_markup=None) -> dict:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f'[Telegram] Sin config — {text[:80]}')
        return {}
    payload = {
        'chat_id':                  TELEGRAM_CHAT_ID,
        'text':                     text,
        'parse_mode':               parse_mode,
        'disable_web_page_preview': True,
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        r = requests.post(f'{API}/sendMessage', json=payload, timeout=10)
        return r.json() if r.ok else {}
    except Exception as e:
        print(f'[Telegram] Error: {e}')
        return {}


def _send(text: str, parse_mode: str = 'HTML') -> bool:
    return bool(_post(text, parse_mode).get('ok'))


def answer_callback(callback_id: str, text: str = ''):
    try:
        requests.post(
            f'{API}/answerCallbackQuery',
            json={'callback_query_id': callback_id, 'text': text},
            timeout=5,
        )
    except Exception:
        pass


def _score_stars(score: int) -> str:
    if score >= 9:
        return '🔥'
    if score >= 7:
        return '⭐'
    return '🔹'


def _remote_badge(job: dict) -> str:
    loc = job.get('location', '').lower()
    source = job.get('source', '')
    is_remote = job.get('remote') is True or source == 'RemoteOK' or 'remote' in loc
    return ' 🌍 Remote' if is_remote else ''


def send_startup():
    _send(
        '🤖 <b>Job Hunter v2 — Dev Edition</b>\n\n'
        '⚛️ Frontend  🤖 IA &amp; Dev  🌐 Full Stack  🚀 JS/TS\n\n'
        '🔍 Portales: Indeed · InfoJobs · Tecnoempleo · RemoteOK · LinkedIn\n'
        '🌍 Cobertura: Málaga + España + Remote\n'
        '🧠 IA puntúa cada oferta 1-10 — solo ves lo relevante.\n'
        '📊 Resumen diario a las 9:00. ¡A programar! 💻'
    )


def send_job_alert(job: dict) -> int | None:
    score    = job.get('score', 0)
    reason   = job.get('reason', '')
    match    = job.get('skills_match', [])
    gap      = job.get('skills_gap', [])
    remote   = _remote_badge(job)
    star     = _score_stars(score)

    skills_line = ''
    if match:
        skills_line += f'\n✅ <b>Tienes:</b> {", ".join(match[:5])}'
    if gap:
        skills_line += f'\n⚠️ <b>Podrías necesitar:</b> {", ".join(gap[:3])}'

    summary_line = f'\n<i>{job["summary"][:200]}…</i>' if job.get('summary') else ''

    text = (
        f'{job["category"]}  {star} <b>{score}/10</b>{remote}\n\n'
        f'<b>{job["title"]}</b>\n'
        f'🏢 {job["company"]}\n'
        f'📍 {job["location"]}  ·  {job["source"]}'
        f'{skills_line}'
        f'\n<i>"{reason}"</i>'
        f'{summary_line}\n\n'
        f'🔗 <a href=\'{job["url"]}\'>Ver oferta</a>'
    )

    keyboard = {'inline_keyboard': [[
        {'text': '✅ Voy a aplicar',  'callback_data': f'apply_{job["id"]}'},
        {'text': '❌ Descartar',      'callback_data': f'discard_{job["id"]}'},
    ]]}

    resp = _post(text, reply_markup=keyboard)
    return resp.get('result', {}).get('message_id')


def _esc(text: str) -> str:
    """Escapa caracteres HTML para texto plano dentro de tags HTML."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def send_applied_followup(job: dict):
    """
    Envía URL de la oferta + carta de presentación sugerida (si existe) + botones de confirmación.
    La carta aparece en bloque <pre> para que sea fácil copiarla con mantener pulsado en móvil.
    """
    cover = job.get('cover_letter', '').strip()

    header = (
        f'🔗 <b>Abre la oferta y aplica</b>\n\n'
        f'<b>{_esc(job["title"])}</b> — {_esc(job["company"])}\n'
        f'<a href=\'{job["url"]}\'>Abrir oferta</a>'
    )

    letter_block = (
        f'\n\n💌 <b>Carta sugerida</b> <i>(mantén pulsado → copiar)</i>:\n'
        f'<pre>{_esc(cover)}</pre>'
    ) if cover else ''

    footer = '\n\nCuando lo hayas enviado, pulsa el botón:'

    keyboard = {'inline_keyboard': [[
        {'text': '✅ Enviado',      'callback_data': f'done_{job["id"]}'},
        {'text': '❌ Al final no',  'callback_data': f'discard_{job["id"]}'},
    ]]}
    _post(header + letter_block + footer, reply_markup=keyboard)


def send_daily_digest(
    applied: list,
    discarded: list,
    pending: list,
    db_stats: dict,
):
    total = len(applied) + len(discarded) + len(pending)

    if total == 0:
        _send('📭 <b>Resumen diario</b>\n\nSin ofertas relevantes hoy. Seguiré buscando. 👀')
        return

    lines = ['🌅 <b>Resumen diario — Dev Edition</b>\n']

    if applied:
        lines.append(f'✅ <b>Aplicadas ({len(applied)}):</b>')
        for j in applied:
            lines.append(f'  • {j["puesto"]} — {j["empresa"]} ({j["portal"]})')

    if discarded:
        lines.append(f'❌ <b>Descartadas ({len(discarded)}):</b>')
        for j in discarded:
            lines.append(f'  • {j["puesto"]} — {j["empresa"]}')

    if pending:
        lines.append(f'⏳ <b>Pendientes ({len(pending)}):</b>')
        for j in pending:
            lines.append(f'  • {j["puesto"]} — {j["empresa"]} ({j["portal"]})')

    lines.append(f'\n📊 Acumulado total: {db_stats["total"]} ofertas procesadas')
    _send('\n'.join(lines))


def send_error(msg: str):
    _send(f'⚠️ <b>Error en Job Hunter v2</b>\n\n<code>{msg[:300]}</code>')
