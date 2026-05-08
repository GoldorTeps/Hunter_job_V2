"""
Enriquecimiento con IA: puntúa cada oferta 1-10 según el perfil del candidato
y extrae qué skills del JD tiene David vs cuáles podrían faltar.
"""
import os
import json

from openai import OpenAI
from config import PROFILE_SUMMARY, MIN_AI_SCORE

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', ''))
    return _client


_SYSTEM = (
    'Eres un asistente que analiza ofertas de trabajo para un desarrollador frontend/fullstack '
    'con foco en IA y automatización. Respondes ÚNICAMENTE con JSON válido, sin markdown.'
)

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


def enrich_job(job: dict) -> dict | None:
    """
    Enriquece el job con el análisis de IA.
    Devuelve None si el score está por debajo de MIN_AI_SCORE.
    """
    analysis = score_job(job)
    score = analysis['score']

    if score < MIN_AI_SCORE:
        print(f'[AI] Descartado (score {score}/10): {job["title"]} — {job["company"]}')
        return None

    job.update(analysis)
    print(f'[AI] ✅ Score {score}/10: {job["title"]} — {job["company"]}')
    return job
