"""
Scrapers para portales de empleo tech:
  - Indeed (RSS)
  - InfoJobs (HTML)
  - Tecnoempleo (RSS — portal tech específico español)
  - RemoteOK (JSON API pública — trabajo remoto)
"""
import time
import hashlib
import unicodedata

import feedparser
import requests
from bs4 import BeautifulSoup

from config import BLACKLIST, LOCATION_MALAGA, LOCATION_SPAIN, PROVINCE, SEARCHES

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'es-ES,es;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


def _job_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:20]


def _is_blacklisted(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in BLACKLIST)


def _clean(text: str) -> str:
    return ' '.join(text.split()) if text else ''


def _normalize(text: str) -> str:
    return unicodedata.normalize('NFKD', text.lower()).encode('ascii', 'ignore').decode()


def _is_tech_relevant(title: str, description: str = '') -> bool:
    """Comprueba que la oferta tiene alguna keyword tech del perfil."""
    haystack = _normalize(title + ' ' + description)
    tech_terms = [
        'react', 'typescript', 'javascript', 'frontend', 'front-end',
        'fullstack', 'full stack', 'node', 'python', 'nextjs', 'next.js',
        'desarrollador', 'developer', 'programador', 'engineer',
        'ia ', 'inteligencia artificial', 'machine learning', 'llm', 'openai',
        'tailwind', 'vue', 'angular', 'svelte', 'web developer',
    ]
    return any(t in haystack for t in tech_terms)


# ── Indeed (RSS) ──────────────────────────────────────────────────────────────

def scrape_indeed(keyword: str, category: str) -> list:
    jobs = []
    url = (
        f'https://es.indeed.com/rss'
        f'?q={keyword.replace(" ", "+")}'
        f'&l={LOCATION_MALAGA.replace(" ", "+")}'
        f'&radius=50'
        f'&sort=date'
    )
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            title   = _clean(entry.get('title', ''))
            company = _clean(entry.get('author', 'Empresa'))
            link    = entry.get('link', '')
            summary = _clean(entry.get('summary', ''))
            loc     = _clean(entry.get('indeed_city', LOCATION_MALAGA))

            if not title or not link:
                continue
            if _is_blacklisted(title + ' ' + summary):
                continue
            if not _is_tech_relevant(title, summary):
                continue

            jobs.append({
                'id':       _job_id(link),
                'title':    title,
                'company':  company,
                'location': loc,
                'url':      link,
                'category': category,
                'source':   'Indeed',
                'summary':  summary[:300],
            })
    except Exception as e:
        print(f'[Indeed] Error "{keyword}": {e}')
    return jobs


# ── InfoJobs ──────────────────────────────────────────────────────────────────

def scrape_infojobs(keyword: str, category: str) -> list:
    jobs = []
    url = (
        f'https://www.infojobs.net/jobsearch/search-results/list.xhtml'
        f'?keyword={keyword.replace(" ", "+")}'
        f'&province={PROVINCE}'
        f'&sortBy=PUBLICATION_DATE'
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(resp.text, 'html.parser')

        for item in soup.select('li[data-jobad-id], .ij-OfferList-item')[:12]:
            title_el   = item.select_one('h2 a, .ij-OfferList-item-title a, h3 a')
            company_el = item.select_one('.ij-OfferList-item-company, .company-name')
            loc_el     = item.select_one('.ij-OfferList-item-location, .location')

            if not title_el:
                continue

            title   = _clean(title_el.get_text())
            company = _clean(company_el.get_text()) if company_el else 'Empresa'
            loc     = _clean(loc_el.get_text()) if loc_el else LOCATION_MALAGA
            href    = title_el.get('href', '')
            link    = href if href.startswith('http') else f'https://www.infojobs.net{href}'

            if not title or _is_blacklisted(title):
                continue
            if not _is_tech_relevant(title):
                continue

            jobs.append({
                'id':       _job_id(link),
                'title':    title,
                'company':  company,
                'location': loc,
                'url':      link,
                'category': category,
                'source':   'InfoJobs',
                'summary':  '',
            })
    except Exception as e:
        print(f'[InfoJobs] Error "{keyword}": {e}')
    return jobs


# ── Tecnoempleo (RSS) ─────────────────────────────────────────────────────────

_TECNOEMPLEO_RSS = 'https://www.tecnoempleo.com/rss/ofertas-trabajo-informatica-7.xml'

# Keywords del perfil para filtrar el feed RSS general de Tecnoempleo
_TECNOEMPLEO_FILTER = [
    'react', 'frontend', 'front-end', 'typescript', 'javascript',
    'fullstack', 'full stack', 'node.js', 'nodejs', 'next.js', 'nextjs',
    'python', 'desarrollador web', 'web developer', 'ia ', 'inteligencia artificial',
    'llm', 'machine learning',
]

_tecnoempleo_cache: list | None = None


def _get_tecnoempleo_feed() -> list:
    """Descarga el feed RSS de Tecnoempleo una sola vez por ciclo."""
    global _tecnoempleo_cache
    if _tecnoempleo_cache is not None:
        return _tecnoempleo_cache
    try:
        feed = feedparser.parse(_TECNOEMPLEO_RSS)
        _tecnoempleo_cache = feed.entries
        print(f'[Tecnoempleo] Feed cargado: {len(feed.entries)} entradas.')
    except Exception as e:
        print(f'[Tecnoempleo] Error cargando feed: {e}')
        _tecnoempleo_cache = []
    return _tecnoempleo_cache


def scrape_tecnoempleo(keyword: str, category: str) -> list:
    """Filtra el feed de Tecnoempleo por keyword y categoría."""
    jobs = []
    entries = _get_tecnoempleo_feed()
    kw_norm = _normalize(keyword)

    for entry in entries:
        title   = _clean(entry.get('title', ''))
        summary = _clean(entry.get('summary', '') or entry.get('description', ''))
        link    = entry.get('link', '')

        if not title or not link:
            continue

        title_norm = _normalize(title)
        if kw_norm not in title_norm and kw_norm not in _normalize(summary):
            continue
        if _is_blacklisted(title + ' ' + summary):
            continue

        loc_raw = entry.get('tags', [{}])[0].get('term', '') if entry.get('tags') else ''
        loc = _clean(loc_raw) or LOCATION_SPAIN

        jobs.append({
            'id':       _job_id(link),
            'title':    title,
            'company':  _clean(entry.get('author', 'Empresa')),
            'location': loc,
            'url':      link,
            'category': category,
            'source':   'Tecnoempleo',
            'summary':  summary[:300],
        })

    return jobs


def reset_tecnoempleo_cache():
    """Llamar al inicio de cada ciclo de búsqueda para refrescar el feed."""
    global _tecnoempleo_cache
    _tecnoempleo_cache = None


# ── RemoteOK (JSON API) ───────────────────────────────────────────────────────

_REMOTEOK_BASE = 'https://remoteok.io/api'
_REMOTEOK_HEADERS = {
    **HEADERS,
    'Accept': 'application/json',
}


def scrape_remoteok(tag: str, category: str) -> list:
    """
    Usa la API pública de RemoteOK para buscar trabajos remotos por tag.
    Todas las posiciones son remote por definición.
    """
    jobs = []
    try:
        resp = requests.get(
            _REMOTEOK_BASE,
            params={'tag': tag},
            headers=_REMOTEOK_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        # El primer elemento es siempre el aviso legal — saltarlo
        for offer in data[1:21]:
            if not isinstance(offer, dict):
                continue

            title   = _clean(offer.get('position', ''))
            company = _clean(offer.get('company', 'Empresa'))
            loc     = offer.get('location') or 'Remote'
            link    = offer.get('url', '') or offer.get('apply_url', '')
            summary = _clean(offer.get('description', ''))

            if not title or not link:
                continue
            if _is_blacklisted(title + ' ' + summary):
                continue
            if not _is_tech_relevant(title, summary):
                continue

            # Añadir indicador de salario si está disponible
            sal_min = offer.get('salary_min')
            sal_max = offer.get('salary_max')
            if sal_min and sal_max:
                summary = f'${sal_min:,}–${sal_max:,}/yr · ' + summary[:250]
            else:
                summary = summary[:300]

            jobs.append({
                'id':       _job_id(link),
                'title':    title,
                'company':  company,
                'location': f'{loc} (Remote)',
                'url':      link,
                'category': category,
                'source':   'RemoteOK',
                'summary':  summary,
            })
    except Exception as e:
        print(f'[RemoteOK] Error "{tag}": {e}')
    return jobs


# ── Orquestador ───────────────────────────────────────────────────────────────

def run_all_searches() -> list:
    from scraper_linkedin import scrape_all_linkedin

    reset_tecnoempleo_cache()
    all_jobs = []

    for search in SEARCHES:
        cat = search['category']

        for kw in search.get('indeed', [])[:2]:
            all_jobs += scrape_indeed(kw, cat)
            time.sleep(1.5)

        for kw in search.get('infojobs', [])[:2]:
            all_jobs += scrape_infojobs(kw, cat)
            time.sleep(1.5)

        for kw in search.get('tecnoempleo', [])[:3]:
            all_jobs += scrape_tecnoempleo(kw, cat)
            # sin sleep: el feed ya está cacheado

        for tag in search.get('remoteok', [])[:2]:
            all_jobs += scrape_remoteok(tag, cat)
            time.sleep(2)

    # LinkedIn al final (tiene sus propias pausas)
    all_jobs += scrape_all_linkedin()

    # Eliminar duplicados por ID
    seen_ids = set()
    unique = []
    for job in all_jobs:
        if job['id'] not in seen_ids:
            seen_ids.add(job['id'])
            unique.append(job)

    print(f'[Scraper] {len(unique)} ofertas únicas encontradas.')
    return unique
