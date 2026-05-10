"""
Enriquecimiento con IA:
  - Puntúa cada oferta 1-10 según el perfil del candidato.
  - Genera una carta de presentación personalizada para las ofertas que pasan el umbral.
"""
import os
import json

from openai import OpenAI
from config import PROFILE_SUMMARY, MIN_AI_SCORE

_client = None
_cv_text_cache: str | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', ''))
    return _client


def _load_dev_cv() -> str:
    """
    Carga el texto del CV del desarrollador.
    Prioridad: cvs/CV_Developer.pdf (si existe y pdfplumber está instalado)
               → PROFILE_SUMMARY como fallback.
    El resultado se cachea en memoria para el resto del proceso.
    """
    global _cv_text_cache
    if _cv_text_cache is not None:
        return _cv_text_cache

    cv_path = os.path.join(os.path.dirname(__file__), 'cvs', 'CV_Developer.pdf')
    if os.path.exists(cv_path):
        try:
            import pdfplumber
            with pdfplumber.open(cv_path) as pdf:
                _cv_text_cache = '\n'.join(p.extract_text() or '' for p in pdf.pages).strip()
            print(f'[AI] CV cargado desde PDF ({len(_cv_text_cache)} chars).')
            return _cv_text_cache
        except ImportError:
            print('[AI] pdfplumber no instalado — usando PROFILE_SUMMARY como CV.')
        except Exception as e:
            print(f'[AI] Error leyendo CV PDF: {e} — usando PROFILE_SUMMARY.')

    _cv_text_cache = PROFILE_SUMMARY.strip()
    return _cv_text_cache


# ── Scoring ───────────────────────────────────────────────────────────────────

_SYSTEM = (
    'Eres un asistente que analiza ofertas de trabajo para un desarrollador frontend/fullstack '
    'con foco en IA y automatización. Respondes ÚNICAMENTE con JSON válido, sin markdown.'
)


# ── Carta de presentación ─────────────────────────────────────────────────────

_COVER_SYSTEM = (
    'Eres un redactor especializado en cartas de presentación para desarrolladores. '
    'Respondes ÚNICAMENTE con el cuerpo de la carta — sin saludo, sin despedida, sin firma.'
)

_COVER_PROMPT = """Escribe una carta de presentación breve (3-4 oraciones) para este puesto.

REGLAS ESTRICTAS — incumplirlas invalida la respuesta:
1. Usa SOLO información del perfil del candidato. No inventes experiencia ni habilidades.
2. Menciona el stack técnico que el candidato tiene Y que la oferta pide (ver "Skills que encajan").
3. Si la oferta menciona IA, LLM, automatización o producto: cita ZeroCog.org o el Job Hunter Bot como evidencia real.
4. Sin "Estimado/a", sin "Un cordial saludo", sin fecha, sin nombre al final.
5. Español. Tono directo, honesto, sin frases vacías.

=== PERFIL DEL CANDIDATO ===
{cv_text}

=== OFERTA ===
Puesto: {title}
Empresa: {company}
Descripción: {summary}
Skills del candidato que encajan con esta oferta: {skills_match}

Responde ÚNICAMENTE con las 3-4 oraciones de la carta."""

_PROMPT = """Analiza esta oferta de trabajo para el candidato descrito y responde con JSON.

=== PERFIL DEL CANDIDATO ===
{profile}

=== OFERTA ===
Título: {title}
Empresa: {company}
Ubicación: {location}
Fuente: {source}
Descripción: {summary}

Responde con este JSON exacto (sin texto adicional):
{{
  "score": <entero 1-10>,
  "reason": "<frase corta de 10-15 palabras explicando el score>",
  "skills_match": ["skill1", "skill2"],
  "skills_gap": ["skill1", "skill2"],
  "remote": <true|false|null>,
  "seniority": "<junior|mid|senior|lead|unknown>"
}}

Criterios de scoring:
- 9-10: Encaje perfecto (React/TS/Node/AI, remoto o Málaga, startup/producto)
- 7-8:  Buen encaje (stack conocido, condiciones aceptables)
- 5-6:  Encaje parcial (skills relevantes pero stack diferente o condiciones inciertas)
- 3-4:  Encaje débil (solo Python o JS genérico, sin IA/frontend)
- 1-2:  No relevante para el perfil

Bonus +1 punto (aplícalo antes de asignar el score final):
Si la oferta menciona explícitamente LLM, OpenAI, automatización, agentes IA, o producto IA,
el candidato tiene experiencia real y demostrable en producción con IA:
  - ZeroCog.org: plataforma de coaching con IA que él diseñó y desplegó.
  - Job Hunter Bot: bot de búsqueda de empleo autónomo con scraping + IA + Telegram (este mismo proyecto).
Aplica el +1 si la oferta requiere o valora IA/LLM en producción y el score base sería ≥ 6.
"""


def score_job(job: dict) -> dict:
    """
    Llama a GPT-4o-mini para puntuar la oferta.
    Devuelve dict con score, reason, skills_match, skills_gap, remote, seniority.
    En caso de error, devuelve score=0 para que se filtre.
    """
    if not os.getenv('OPENAI_API_KEY', ''):
        return {'score': 7, 'reason': 'Sin API key — aprobado por defecto', 'skills_match': [], 'skills_gap': [], 'remote': None, 'seniority': 'unknown'}

    prompt = _PROMPT.format(
        profile  = PROFILE_SUMMARY.strip(),
        title    = job.get('title', ''),
        company  = job.get('company', ''),
        location = job.get('location', ''),
        source   = job.get('source', ''),
        summary  = (job.get('summary') or 'No disponible')[:600],
    )

    try:
        response = _get_client().chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': _SYSTEM},
                {'role': 'user',   'content': prompt},
            ],
            max_tokens=200,
            temperature=0.2,
            response_format={'type': 'json_object'},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        return {
            'score':        int(data.get('score', 0)),
            'reason':       str(data.get('reason', '')),
            'skills_match': data.get('skills_match', []),
            'skills_gap':   data.get('skills_gap', []),
            'remote':       data.get('remote'),
            'seniority':    data.get('seniority', 'unknown'),
        }
    except Exception as e:
        print(f'[AI] Error scoring "{job.get("title")}": {e}')
        return {'score': 0, 'reason': str(e), 'skills_match': [], 'skills_gap': [], 'remote': None, 'seniority': 'unknown'}


def generate_cover_letter(job: dict) -> str:
    """
    Genera una carta de presentación personalizada para el job.
    Usa skills_match del scoring para personalizar el stack mencionado.
    Devuelve cadena vacía si no hay API key o falla la llamada.
    """
    if not os.getenv('OPENAI_API_KEY', ''):
        return ''

    cv_text      = _load_dev_cv()
    skills_match = ', '.join(job.get('skills_match', [])) or 'ver perfil completo'
    summary      = (job.get('summary') or 'No disponible')[:500]

    prompt = _COVER_PROMPT.format(
        cv_text      = cv_text[:2000],
        title        = job.get('title', ''),
        company      = job.get('company', ''),
        summary      = summary,
        skills_match = skills_match,
    )

    try:
        response = _get_client().chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': _COVER_SYSTEM},
                {'role': 'user',   'content': prompt},
            ],
            max_tokens=250,
            temperature=0.3,
        )
        letter = response.choices[0].message.content.strip()
        print(f'[AI] Carta generada para "{job.get("title")}" ({len(letter)} chars).')
        return letter
    except Exception as e:
        print(f'[AI] Error generando carta para "{job.get("title")}": {e}')
        return ''


def enrich_job(job: dict) -> dict | None:
    """
    Puntúa el job con IA y, si supera el umbral, genera la carta de presentación.
    Devuelve None si el score está por debajo de MIN_AI_SCORE.
    """
    analysis = score_job(job)
    score    = analysis['score']

    if score < MIN_AI_SCORE:
        print(f'[AI] Descartado (score {score}/10): {job["title"]} — {job["company"]}')
        return None

    job.update(analysis)
    job['cover_letter'] = generate_cover_letter(job)
    print(f'[AI] ✅ Score {score}/10: {job["title"]} — {job["company"]}')
    return job
