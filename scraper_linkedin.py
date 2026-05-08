"""
LinkedIn Jobs — endpoint público sin login.
Busca en toda España para maximizar cobertura en trabajos tech/remote.
"""
import time
import hashlib

import requests
from bs4 import BeautifulSoup

from config import BLACKLIST, SEARCHES, LINKEDIN_LOCATION

BASE_URL = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search'

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'es-ES,es;q=0.9',
}


def _job_id(url: str) -> str:
    return 'li_' + hashlib.md5(url.encode()).hexdigest()[:18]


def _is_blacklisted(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in BLACKLIST)


def _fetch_html(keyword: str) -> str:
    params = {
        'keywords': keyword,
        'location': LINKEDIN_LOCATION,
        'f_TPR':    'r86400',  # últimas 24 horas
        'position': 1,
        'pageNum':  0,
        'start':    0,
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f'[LinkedIn] Error fetch "{keyword}": {e}')
        return ''


def _parse_jobs(html: str, category: str) -> list:
    jobs = []
    soup = BeautifulSoup(html, 'html.parser')

    for card in soup.select('li')[:15]:
        title_el   = card.select_one('h3.base-search-card__title')
        company_el = card.select_one('h4.base-search-card__subtitle')
        loc_el     = card.select_one('span.job-search-card__location')
        link_el    = card.select_one('a.base-card__full-link, a[href*="/jobs/view/"]')

        if not title_el or not link_el:
            continue

        title   = title_el.get_text(strip=True)
        company = company_el.get_text(strip=True) if company_el else 'Empresa'
        loc     = loc_el.get_text(strip=True) if loc_el else LINKEDIN_LOCATION
        url     = link_el.get('href', '').split('?')[0]

        if not title or not url:
            continue
        if _is_blacklisted(title):
            continue

        jobs.append({
            'id':       _job_id(url),
            'title':    title,
            'company':  company,
            'location': loc,
            'url':      url,
            'category': category,
            'source':   'LinkedIn',
            'summary':  '',
        })

    return jobs


def scrape_all_linkedin() -> list:
    all_jobs = []

    for search in SEARCHES:
        cat = search['category']
        for kw in search.get('linkedin', [])[:2]:
            html = _fetch_html(kw)
            if html:
                all_jobs += _parse_jobs(html, cat)
            time.sleep(2.5)

    seen = set()
    unique = []
    for job in all_jobs:
        if job['id'] not in seen:
            seen.add(job['id'])
            unique.append(job)

    print(f'[LinkedIn] {len(unique)} ofertas únicas.')
    return unique
