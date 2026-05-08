"""
Scrapers para portales de empleo tech:
  - Indeed (RSS)              — España
  - InfoJobs (HTML)           — España
  - Tecnoempleo (RSS)         — España, tech-específico
  - RemoteOK (JSON API)       — Global, remoto
  - WeWorkRemotely (RSS)      — Global, remoto
  - GetOnBoard (JSON API)     — Latam / España, tech
  - Torre.co (POST API)       — Global, matching IA
  - Computrabajo (HTML)       — España / Latam
  - Wellfound (HTML/SSR)      — Global, startups (best-effort)
"""
import json
import time
import hashlib
import unicodedata

import feedparser
import requests
from bs4 import BeautifulSoup

from config import BLACKLIST, LOCATION_MALAGA, LOCATION_SPAIN, PROVINCE, SEARCHES, WWR_CATEGORIES

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


# ── WeWorkRemotely (RSS) ──────────────────────────────────────────────────────

_WWR_BASE = 'https://weworkremotely.com/categories/{slug}.rss'

# Keywords tech mínimas para filtrar el feed de categoría (no son busquedas, son filtros)
_WWR_TECH_FILTER = [
    'react', 'typescript', 'javascript', 'frontend', 'front-end',
    'fullstack', 'full stack', 'node', 'python', 'next.js', 'nextjs',
    'vue', 'svelte', 'angular', 'ai ', 'llm', 'machine learning',
]


def scrape_weworkremotely(category_slug: str, category: str) -> list:
    jobs = []
    url = _WWR_BASE.format(slug=category_slug)
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:25]:
            raw_title = _clean(entry.get('title', ''))
            link      = entry.get('link', '')
            summary   = _clean(entry.get('summary', '') or entry.get('description', ''))

            if not raw_title or not link:
                continue

            # El título suele ser "Company: Job Title"
            if ': ' in raw_title:
                company, title = raw_title.split(': ', 1)
            else:
                title, company = raw_title, 'Empresa'

            if _is_blacklisted(title + ' ' + summary):
                continue

            # Filtrar solo ofertas tech relevantes para el perfil
            haystack = _normalize(title + ' ' + summary)
            if not any(t in haystack for t in _WWR_TECH_FILTER):
                continue

            jobs.append({
                'id':       _job_id(link),
                'title':    title,
                'company':  company,
                'location': 'Remote (Worldwide)',
                'url':      link,
                'category': category,
                'source':   'WeWorkRemotely',
                'summary':  summary[:300],
            })
    except Exception as e:
        print(f'[WWR] Error "{category_slug}": {e}')
    return jobs


# ── GetOnBoard (JSON API) ─────────────────────────────────────────────────────

_GOB_BASE = 'https://www.getonbrd.com/api/v0/jobs'


def scrape_getonboard(query: str, category: str) -> list:
    jobs = []
    try:
        resp = requests.get(
            _GOB_BASE,
            params={'query': query, 'per_page': 20, 'published': 'true'},
            headers={**HEADERS, 'Accept': 'application/json'},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get('data', [])

        for item in data:
            if item.get('type') != 'job':
                continue
            attrs = item.get('attributes', {})
            job_id_slug = item.get('id', '')

            title   = _clean(attrs.get('title', ''))
            summary = _clean(attrs.get('description', '') or '')
            company = _clean(attrs.get('company_name', '') or job_id_slug.split('-')[0].title())
            loc_raw = attrs.get('country', '') or ''
            remote  = attrs.get('remote', False)
            loc     = ('Remote · ' + loc_raw) if remote else (loc_raw or LOCATION_SPAIN)

            link = f'https://www.getonbrd.com/jobs/{job_id_slug}'

            sal_min = attrs.get('salary_from')
            sal_max = attrs.get('salary_to')
            currency = attrs.get('currency', 'USD')
            if sal_min and sal_max:
                summary = f'{currency} {sal_min:,}–{sal_max:,}/mo · ' + summary[:250]
            else:
                summary = summary[:300]

            if not title or _is_blacklisted(title + ' ' + summary):
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
                'source':   'GetOnBoard',
                'summary':  summary,
            })
    except Exception as e:
        print(f'[GetOnBoard] Error "{query}": {e}')
    return jobs


# ── Torre.co (POST API) ───────────────────────────────────────────────────────

_TORRE_SEARCH = 'https://torre.ai/api/opportunities/_search'


def scrape_torre(query: str, category: str) -> list:
    jobs = []
    try:
        resp = requests.post(
            _TORRE_SEARCH,
            json={'q': query, 'size': 20, 'aggregate': False, 'remote': True},
            headers={**HEADERS, 'Content-Type': 'application/json', 'Accept': 'application/json'},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get('results', [])

        for opp in results:
            title   = _clean(opp.get('objective', ''))
            opp_id  = opp.get('id', '')
            orgs    = opp.get('organizations', [])
            company = orgs[0].get('name', 'Empresa') if orgs else 'Empresa'
            loc     = _clean(opp.get('locationName', '') or 'Remote')
            remote  = opp.get('remote', False)
            link    = f'https://torre.ai/opportunities/{opp_id}'

            comp = opp.get('compensation', {}) or {}
            sal_min  = comp.get('minAmount')
            sal_max  = comp.get('maxAmount')
            currency = comp.get('currency', 'USD')
            summary  = ''
            if sal_min and sal_max:
                summary = f'{currency} {sal_min:,}–{sal_max:,}/mo'
            if remote:
                loc = f'Remote · {loc}' if loc and loc != 'Remote' else 'Remote'

            if not title or not opp_id:
                continue
            if _is_blacklisted(title):
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
                'source':   'Torre.co',
                'summary':  summary,
            })
    except Exception as e:
        print(f'[Torre] Error "{query}": {e}')
    return jobs


# ── Computrabajo España (HTML) ────────────────────────────────────────────────

_COMPUTRABAJO_BASE = 'https://www.computrabajo.es/ofertas-de-trabajo'


def scrape_computrabajo(keyword: str, category: str) -> list:
    jobs = []
    url = f'{_COMPUTRABAJO_BASE}?q={keyword.replace(" ", "+")}'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Computrabajo cambia selectores con frecuencia — probamos en orden de prioridad
        items = (
            soup.select('article.box_offer')
            or soup.select('div[data-jobid]')
            or soup.select('.offerList > li')
            or soup.select('article[data-id]')
        )

        for item in items[:15]:
            title_el   = item.select_one('h2 a, h1 a, .title_offer a, a.js-o-link')
            company_el = item.select_one('.fc_base.t_ellipsis, .company, a[data-ga-action="empresa"]')
            loc_el     = item.select_one('.fs13, .location, span[itemprop="addressLocality"]')

            if not title_el:
                continue

            title   = _clean(title_el.get_text())
            company = _clean(company_el.get_text()) if company_el else 'Empresa'
            loc     = _clean(loc_el.get_text()) if loc_el else LOCATION_SPAIN
            href    = title_el.get('href', '')
            link    = href if href.startswith('http') else f'https://www.computrabajo.es{href}'

            if not title or not link or _is_blacklisted(title):
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
                'source':   'Computrabajo',
                'summary':  '',
            })
    except Exception as e:
        print(f'[Computrabajo] Error "{keyword}": {e}')
    return jobs


# ── Wellfound / AngelList (HTML + Next.js SSR) ─────────────────────────────

_WELLFOUND_BASE = 'https://wellfound.com/jobs'


def scrape_wellfound(keyword: str, category: str) -> list:
    """
    Wellfound es una SPA Next.js. Intentamos extraer datos del tag __NEXT_DATA__
    que algunas páginas incluyen en el HTML inicial. Si falla, retorna lista vacía.
    """
    jobs = []
    url = f'{_WELLFOUND_BASE}?query={keyword.replace(" ", "+")}'
    try:
        resp = requests.get(
            url,
            headers={
                **HEADERS,
                'Accept': 'text/html,application/xhtml+xml',
                'Cookie': '',   # sin sesión — acceso público
            },
            timeout=15,
        )
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Intentar extraer datos SSR de Next.js
        next_script = soup.find('script', {'id': '__NEXT_DATA__'})
        if next_script and next_script.string:
            page_data = json.loads(next_script.string)
            # Navegar la estructura de datos de Wellfound (varía según versión)
            jobs_raw = (
                page_data.get('props', {})
                         .get('pageProps', {})
                         .get('jobs', [])
                or page_data.get('props', {})
                            .get('pageProps', {})
                            .get('initialData', {})
                            .get('jobs', [])
            )
            for j in jobs_raw[:15]:
                title   = _clean(j.get('title', '') or j.get('role', ''))
                company = _clean(
                    j.get('company', {}).get('name', '')
                    if isinstance(j.get('company'), dict)
                    else str(j.get('company', 'Empresa'))
                )
                loc   = _clean(j.get('locationDisplayName', '') or j.get('location', '') or 'Remote')
                slug  = j.get('slug', '') or j.get('id', '')
                link  = f'https://wellfound.com/jobs/{slug}' if slug else ''

                if not title or not link:
                    continue
                if _is_blacklisted(title):
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
                    'source':   'Wellfound',
                    'summary':  '',
                })
        else:
            # Fallback: scraping HTML estático (limitado sin JS)
            for card in soup.select('a[data-test="StartupResult"], .styles_component__*')[:10]:
                title_el = card.select_one('h2, h3, .role-title, [class*="title"]')
                if not title_el:
                    continue
                title = _clean(title_el.get_text())
                href  = card.get('href', '')
                link  = href if href.startswith('http') else f'https://wellfound.com{href}'
                if title and link and _is_tech_relevant(title):
                    jobs.append({
                        'id':       _job_id(link),
                        'title':    title,
                        'company':  'Startup',
                        'location': 'Remote',
                        'url':      link,
                        'category': category,
                        'source':   'Wellfound',
                        'summary':  '',
                    })

    except Exception as e:
        print(f'[Wellfound] Error "{keyword}": {e}')

    if jobs:
        print(f'[Wellfound] {len(jobs)} ofertas encontradas para "{keyword}".')
    return jobs


# ── Orquestador ───────────────────────────────────────────────────────────────

def run_all_searches() -> list:
    from scraper_linkedin import scrape_all_linkedin

    reset_tecnoempleo_cache()
    all_jobs = []

    # ── Portales por keyword ───────────────────────────────────────────────
    for search in SEARCHES:
        cat = search['category']

        for kw in search.get('indeed', [])[:2]:
            all_jobs += scrape_indeed(kw, cat)
            time.sleep(1.5)

        for kw in search.get('infojobs', [])[:2]:
            all_jobs += scrape_infojobs(kw, cat)
            time.sleep(1.5)

        for kw in search.get('tecnoempleo', [])[:3]:
            all_jobs += scrape_tecnoempleo(kw, cat)   # feed cacheado, sin sleep

        for tag in search.get('remoteok', [])[:2]:
            all_jobs += scrape_remoteok(tag, cat)
            time.sleep(2)

        for kw in search.get('getonboard', [])[:2]:
            all_jobs += scrape_getonboard(kw, cat)
            time.sleep(2)

        for kw in search.get('torre', [])[:2]:
            all_jobs += scrape_torre(kw, cat)
            time.sleep(1.5)

        for kw in search.get('computrabajo', [])[:2]:
            all_jobs += scrape_computrabajo(kw, cat)
            time.sleep(1.5)

        for kw in search.get('wellfound', [])[:1]:
            all_jobs += scrape_wellfound(kw, cat)
            time.sleep(2)

    # ── WeWorkRemotely: por categoría (RSS global, filtramos client-side) ──
    for slug, cat in WWR_CATEGORIES.items():
        all_jobs += scrape_weworkremotely(slug, cat)
        time.sleep(2)

    # ── LinkedIn: búsqueda pública en toda España ──────────────────────────
    all_jobs += scrape_all_linkedin()

    # ── Deduplicar por ID ──────────────────────────────────────────────────
    seen_ids = set()
    unique = []
    for job in all_jobs:
        if job['id'] not in seen_ids:
            seen_ids.add(job['id'])
            unique.append(job)

    print(f'[Scraper] {len(unique)} ofertas únicas encontradas.')
    return unique
