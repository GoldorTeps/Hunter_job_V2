"""
Auto-apply por email para ofertas que incluyen dirección de contacto en el anuncio.
Portal-agnóstico: funciona con cualquier oferta de cualquier scraper.
Adjunta el CV PDF si existe en cvs/CV_Developer.pdf.
"""
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from config import CANDIDATE_NAME, CANDIDATE_EMAIL, CANDIDATE_PHONE, PORTFOLIO_URL

CV_PATH = os.path.join(os.path.dirname(__file__), 'cvs', 'CV_Developer.pdf')

_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

# Dominios de correo personal → no son emails de empresa para aplicar
_PERSONAL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'yahoo.es', 'hotmail.com', 'hotmail.es',
    'outlook.com', 'outlook.es', 'icloud.com', 'live.com', 'msn.com',
    'example.com', 'test.com',
}


def extract_apply_email(job: dict) -> str | None:
    """
    Busca un email de contacto laboral en el summary de la oferta.
    Descarta dominios de correo personal y el propio email del candidato.
    """
    haystack = ' '.join(filter(None, [job.get('summary', ''), job.get('title', '')]))
    for email in _EMAIL_RE.findall(haystack):
        domain = email.split('@')[-1].lower()
        if domain in _PERSONAL_DOMAINS:
            continue
        if email.lower() == CANDIDATE_EMAIL.lower():
            continue
        return email
    return None


def _is_smtp_configured() -> bool:
    return bool(os.getenv('GMAIL_USER') and os.getenv('GMAIL_APP_PASSWORD'))


def send_application_email(job: dict, apply_to: str) -> tuple[bool, str]:
    """
    Envía la candidatura por email.

    Devuelve (True, '') si el envío fue correcto.
    Devuelve (False, reason) si falló o SMTP no está configurado.
    """
    if not _is_smtp_configured():
        return False, 'GMAIL_USER o GMAIL_APP_PASSWORD no configurados en .env'

    gmail_user = os.getenv('GMAIL_USER', '')
    gmail_pass = os.getenv('GMAIL_APP_PASSWORD', '')
    cover      = (job.get('cover_letter') or '').strip()

    # ── Construir mensaje ──────────────────────────────────────────────────
    msg = MIMEMultipart()
    msg['From']    = f'{CANDIDATE_NAME} <{CANDIDATE_EMAIL}>'
    msg['To']      = apply_to
    msg['Subject'] = f'Candidatura: {job["title"]} — {CANDIDATE_NAME}'
    msg['Reply-To']= CANDIDATE_EMAIL

    body_parts = []
    if cover:
        body_parts.append(cover)
    else:
        body_parts.append(
            f'Me interesa la posición de {job["title"]} en {job["company"]}. '
            f'Adjunto mi CV para su consideración.'
        )

    signature = (
        f'\n\n—\n'
        f'{CANDIDATE_NAME}\n'
        f'Portfolio: {PORTFOLIO_URL}\n'
        f'GitHub: https://github.com/GoldorTeps\n'
        f'Email: {CANDIDATE_EMAIL}'
    )
    if CANDIDATE_PHONE:
        signature += f'\nTeléfono: {CANDIDATE_PHONE}'

    body_parts.append(signature)
    msg.attach(MIMEText('\n'.join(body_parts), 'plain', 'utf-8'))

    # ── Adjuntar CV ────────────────────────────────────────────────────────
    cv_attached = False
    if os.path.exists(CV_PATH):
        try:
            with open(CV_PATH, 'rb') as f:
                pdf = MIMEApplication(f.read(), _subtype='pdf')
                pdf.add_header(
                    'Content-Disposition', 'attachment',
                    filename='CV_David_Janer_Perez.pdf',
                )
                msg.attach(pdf)
            cv_attached = True
        except Exception as e:
            print(f'[Email] No se pudo adjuntar CV: {e}')

    # ── Enviar vía Gmail SMTP SSL ──────────────────────────────────────────
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, apply_to, msg.as_string())

        print(
            f'[Email] ✅ Enviado a {apply_to}: '
            f'"{job["title"]}" — {job["company"]}'
            f'{" + CV adjunto" if cv_attached else ""}'
        )
        return True, ''

    except smtplib.SMTPAuthenticationError:
        return False, 'Credenciales SMTP incorrectas. Usa un Google App Password.'
    except Exception as e:
        return False, str(e)


def smtp_ready() -> bool:
    """Indica si el módulo puede enviar emails (SMTP configurado)."""
    return _is_smtp_configured()
