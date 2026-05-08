from dotenv import load_dotenv
load_dotenv()

import os

TELEGRAM_TOKEN   = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
DATABASE_URL     = os.getenv('DATABASE_URL', '')
OPENAI_API_KEY   = os.getenv('OPENAI_API_KEY', '')

CHECK_INTERVAL_MIN = int(os.getenv('CHECK_INTERVAL_MINUTES', '45'))
ACTIVE_HOUR_START  = int(os.getenv('ACTIVE_HOUR_START', '9'))
ACTIVE_HOUR_END    = int(os.getenv('ACTIVE_HOUR_END', '21'))
DIGEST_HOUR        = int(os.getenv('DIGEST_HOUR', '9'))
MIN_AI_SCORE       = int(os.getenv('MIN_AI_SCORE', '6'))

# Perfil del candidato — fuente de verdad para el scoring con IA
PROFILE_SUMMARY = """
Name: Adolfo David Janer Pérez
Location: Torremolinos, Málaga, Spain
Work preference: Remote (preferred) > Hybrid > On-site Málaga area.
                 Open to any location in Spain if remote or hybrid.

Technical stack (strong):
  Frontend: React, TypeScript, Tailwind CSS, Framer Motion, Next.js, Vite
  Backend:  Node.js, Python, PostgreSQL, SQLite, REST APIs
  AI/LLM:   OpenAI API, prompt engineering, embeddings, LLM integration
  Automation: Playwright, Telegram Bot API, web scraping pipelines
  Deploy:   Railway, Vercel, Git, GitHub

Production projects shipped:
  - ZeroCog.org: AI decision-architecture SaaS (React, TS, Node.js, OpenAI, PostgreSQL, Railway)
  - Job Hunter Bot: Telegram bot with AI semantic filtering for job search (Python, OpenAI, Railway)
  - AURUM Bunkers: luxury editorial landing page for UHNW clients (React, Framer Motion, Tailwind)
  - Google Maps Scraper: lead-gen data pipeline with rate-limit handling (Python, Playwright, PostgreSQL)
  - Several paid client landing pages deployed on Vercel

Background: Self-taught developer from a different industry. Uses AI as a genuine work multiplier.
Strong product thinking — understands the business problem before writing code.
Languages: Spanish (native), English (professional working proficiency).

Seniority target: Junior to mid-level. Open to any company size if the work is interesting.
Not interested in: pure sales roles, physical labor, mandatory self-employment / freelance only.
"""

LOCATION_MALAGA   = 'Málaga'
LOCATION_SPAIN    = 'España'
LINKEDIN_LOCATION = 'España'
PROVINCE          = '29'   # Málaga (InfoJobs)

SEARCHES = [
    {
        'category':     '⚛️ Frontend',
        'indeed':       ['desarrollador frontend react', 'react developer málaga', 'frontend typescript'],
        'infojobs':     ['desarrollador frontend react', 'react developer', 'frontend javascript'],
        'tecnoempleo':  ['react developer', 'frontend react', 'desarrollador react typescript'],
        'linkedin':     ['react developer', 'frontend developer react', 'desarrollador frontend react'],
        'remoteok':     ['react', 'frontend-react'],
        'wwr':          [],  # WeWorkRemotely usa categorías globales — ver WWR_CATEGORIES
        'getonboard':   ['react developer', 'frontend react developer', 'frontend typescript'],
        'torre':        ['react developer', 'frontend developer react typescript'],
        'computrabajo': ['react developer malaga', 'frontend developer malaga'],
        'wellfound':    ['react developer', 'frontend engineer react'],
    },
    {
        'category':     '🤖 IA & Dev',
        'indeed':       ['ai developer python', 'desarrollador inteligencia artificial', 'python llm developer'],
        'infojobs':     ['desarrollador ia python', 'ai developer'],
        'tecnoempleo':  ['inteligencia artificial developer', 'python ia', 'ai engineer'],
        'linkedin':     ['ai developer python', 'llm engineer', 'ai product engineer'],
        'remoteok':     ['ai', 'llm', 'python-ai'],
        'wwr':          [],
        'getonboard':   ['ai developer', 'python developer ia', 'llm engineer'],
        'torre':        ['ai developer python', 'machine learning engineer', 'llm developer'],
        'computrabajo': ['desarrollador python ia malaga', 'machine learning malaga'],
        'wellfound':    ['ai engineer', 'llm developer', 'ai product engineer'],
    },
    {
        'category':     '🌐 Full Stack',
        'indeed':       ['fullstack react node', 'full stack developer typescript', 'desarrollador full stack react'],
        'infojobs':     ['full stack developer react', 'desarrollador fullstack node'],
        'tecnoempleo':  ['fullstack react node', 'full stack typescript', 'desarrollador full stack'],
        'linkedin':     ['full stack developer react node', 'fullstack typescript'],
        'remoteok':     ['fullstack', 'nodejs-react'],
        'wwr':          [],  # WeWorkRemotely usa categorías globales — ver WWR_CATEGORIES
        'getonboard':   ['full stack developer react', 'fullstack node typescript'],
        'torre':        ['full stack developer react node', 'fullstack typescript developer'],
        'computrabajo': ['full stack developer malaga', 'desarrollador fullstack malaga'],
        'wellfound':    ['full stack engineer react', 'fullstack developer node'],
    },
    {
        'category':     '🚀 JavaScript / TypeScript',
        'indeed':       ['javascript developer málaga', 'typescript developer', 'next.js developer'],
        'infojobs':     ['javascript developer', 'typescript developer'],
        'tecnoempleo':  ['javascript developer', 'typescript', 'nextjs developer'],
        'linkedin':     ['typescript developer', 'javascript developer next.js'],
        'remoteok':     ['typescript', 'nextjs'],
        'wwr':          [],
        'getonboard':   ['javascript developer', 'typescript developer', 'nextjs developer'],
        'torre':        ['typescript developer', 'javascript engineer'],
        'computrabajo': ['javascript developer malaga', 'typescript developer malaga'],
        'wellfound':    ['typescript engineer', 'javascript developer'],
    },
]

# WeWorkRemotely: categorías del portal → nuestra etiqueta.
# Cada categoría se descarga UNA vez y se filtra client-side por keywords tech.
WWR_CATEGORIES = {
    'remote-front-end-programming-jobs':  '⚛️ Frontend',
    'remote-full-stack-programming-jobs': '🌐 Full Stack',
}

BLACKLIST = [
    'comercial', 'ejecutivo de ventas', 'representante de ventas',
    'mozo', 'almacén', 'almacen', 'repartidor', 'conductor reparto',
    'camarero', 'cocinero', 'limpieza', 'vigilante', 'seguridad privada',
    'electricista', 'fontanero', 'operario',
    'multinivel', 'mlm', 'solo comisiones', 'sin sueldo fijo',
    'ingresos extra desde casa',
]
