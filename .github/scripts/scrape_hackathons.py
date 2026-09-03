#!/usr/bin/env python3

import json
import re
import subprocess
import time
import datetime
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup

LISTINGS_FILE = Path('listings.json')
SEEN_FILE = Path('.github/data/seen_hackathons.json')
KNOWN_FILE = Path('hackathons.yml')

REQUEST_TIMEOUT = 15
REQUEST_DELAY = 0.5

TODAY = datetime.date.today().isoformat()


def load_json(path: Path, default):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path: Path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def normalize_url(url: str) -> str:
    if not url:
        return ''
    url = url.strip().split('?')[0].rstrip('/')
    if url.startswith('http://'):
        url = 'https://' + url[7:]
    return url


def is_past(end_date: str) -> bool:
    try:
        return end_date < TODAY
    except Exception:
        return False


def add_hackathon(listings: list, entry: dict, seen: dict) -> bool:
    url_norm = normalize_url(entry.get('url', ''))
    name_key = entry.get('name', '').strip().lower()
    organizer_key = entry.get('organizer', '').strip().lower()

    for existing in listings:
        existing_url_norm = normalize_url(existing.get('url', ''))
        if url_norm and existing_url_norm and url_norm == existing_url_norm:
            return False
        if (existing.get('name', '').strip().lower() == name_key
                and existing.get('organizer', '').strip().lower() == organizer_key):
            return False

    if url_norm and url_norm in seen:
        return False

    listings.append(entry)
    return True


def commit_entry(entry: dict):
    start = entry.get('start_date', '')
    end = entry.get('end_date', '')
    if start and end and start != end:
        date_range = f'{start} – {end}'
    elif start:
        date_range = start
    else:
        date_range = 'TBD'

    name = entry.get('name', 'Unknown')
    msg = f'add {name} — {date_range}'

    try:
        subprocess.run(['git', 'add', 'listings.json', 'README.md'], check=True)
        subprocess.run(['git', 'commit', '-m', msg], check=True)
        print(f'Committed: {msg}')
    except subprocess.CalledProcessError as e:
        print(f'Git commit error: {e}')


def scrape_mlh() -> list:
    results = []
    seasons = ['2027', '2026']

    for season in seasons:
        url = f'https://mlh.io/seasons/{season}/events'
        try:
            resp = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; hackathon-scraper/1.0)'},
            )
            resp.raise_for_status()
        except Exception as e:
            print(f'MLH {season}: fetch error — {e}')
            continue

        soup = BeautifulSoup(resp.text, 'html.parser')

        cards = soup.select('div.event, a.event, .event-wrapper')
        if not cards:
            cards = soup.select('[class*="event"]')

        for card in cards:
            try:
                name_el = card.select_one('h3, h2, .event-name, [class*="name"]')
                name = name_el.get_text(strip=True) if name_el else ''
                if not name:
                    continue

                link_el = card if card.name == 'a' else card.select_one('a')
                href = link_el.get('href', '') if link_el else ''
                if href and not href.startswith('http'):
                    href = 'https://mlh.io' + href

                loc_el = card.select_one('.event-location, [class*="location"], [class*="city"]')
                location = loc_el.get_text(strip=True) if loc_el else 'Unknown'

                mode = 'In-Person'
                mode_el = card.select_one('[class*="hybrid"], [class*="virtual"], [class*="online"], [class*="mode"]')
                if mode_el:
                    badge_text = mode_el.get_text(strip=True).lower()
                    if 'hybrid' in badge_text:
                        mode = 'Hybrid'
                    elif 'virtual' in badge_text or 'online' in badge_text:
                        mode = 'Virtual'

                date_el = card.select_one('.event-date, [class*="date"], time')
                date_text = date_el.get_text(strip=True) if date_el else ''
                start_date = TODAY
                end_date = TODAY

                results.append({
                    'name': name,
                    'organizer': 'MLH',
                    'location': location,
                    'mode': mode,
                    'start_date': start_date,
                    'end_date': end_date,
                    'open_to': 'College',
                    'prize_pool': 'Unknown',
                    'url': href,
                    'date_added': TODAY,
                    '_raw_date': date_text,
                    '_source': f'mlh-{season}',
                })
            except Exception as e:
                print(f'MLH card parse error: {e}')

        time.sleep(REQUEST_DELAY)

    print(f'MLH: {len(results)} raw events')
    return results


def _parse_devpost_dates(text):
    text = text.replace('–', '-').replace('—', '-')
    m = re.search(r'(\w+ \d{1,2},?\s*\d{4})\s*-\s*(\w+ \d{1,2},?\s*\d{4})', text)
    if m:
        fmts = ['%b %d, %Y', '%B %d, %Y', '%b %d %Y', '%B %d %Y']
        s_str = m.group(1).strip()
        e_str = m.group(2).strip()
        for fmt in fmts:
            try:
                s = datetime.datetime.strptime(s_str, fmt).date().isoformat()
                e = datetime.datetime.strptime(e_str, fmt).date().isoformat()
                return s, e
            except ValueError:
                continue
    m2 = re.search(r'(\w+)\s+(\d{1,2})\s*-\s*(\d{1,2}),?\s*(\d{4})', text)
    if m2:
        month, day1, day2, year = m2.group(1), m2.group(2), m2.group(3), m2.group(4)
        for fmt in ['%b %d %Y', '%B %d %Y']:
            try:
                s = datetime.datetime.strptime(f'{month} {day1} {year}', fmt).date().isoformat()
                e = datetime.datetime.strptime(f'{month} {day2} {year}', fmt).date().isoformat()
                return s, e
            except ValueError:
                continue
    m3 = re.search(r'(\w+ \d{1,2},?\s*\d{4})', text)
    if m3:
        s_str = m3.group(1).strip()
        for fmt in ['%b %d, %Y', '%B %d, %Y', '%b %d %Y', '%B %d %Y']:
            try:
                s = datetime.datetime.strptime(s_str, fmt).date().isoformat()
                return s, s
            except ValueError:
                continue
    return None, None


def scrape_devpost() -> list:
    results = []
    page = 1
    max_pages = 5

    while page <= max_pages:
        try:
            resp = requests.get(
                'https://devpost.com/api/hackathons',
                params={
                    'page': page,
                    'per_page': 48,
                    'status[]': 'upcoming',
                    'order_by': 'deadline',
                },
                timeout=REQUEST_TIMEOUT,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; hackathon-scraper/1.0)',
                    'Accept': 'application/json',
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f'Devpost page {page}: error — {e}')
            break

        hackathons = data.get('hackathons', [])
        if not hackathons:
            break

        for h in hackathons:
            try:
                name = h.get('title', '').strip()
                if not name:
                    continue

                url = h.get('url', '').strip()
                location_info = h.get('displayed_location', {})
                location = location_info.get('location', 'Virtual') if location_info else 'Virtual'

                if not location or location.lower() in ('', 'online', 'virtual'):
                    location = 'Virtual'
                    mode = 'Virtual'
                elif 'hybrid' in location.lower():
                    mode = 'Hybrid'
                else:
                    mode = 'In-Person'

                prize_amount = h.get('prize_amount', '')
                if prize_amount and str(prize_amount) not in ('0', ''):
                    try:
                        amount = int(float(str(prize_amount).replace(',', '').replace('$', '')))
                        prize_pool = f'${amount:,}'
                    except Exception:
                        prize_pool = 'Unknown'
                else:
                    prize_pool = 'Unknown'

                period = h.get('submission_period_dates', '') or ''
                start_date = TODAY
                end_date = TODAY
                parsed_start, parsed_end = _parse_devpost_dates(period)
                if parsed_start:
                    start_date = parsed_start
                    end_date = parsed_end or parsed_start

                results.append({
                    'name': name,
                    'organizer': h.get('organization_name', 'Unknown') or 'Unknown',
                    'location': location,
                    'mode': mode,
                    'start_date': start_date,
                    'end_date': end_date,
                    'open_to': 'All',
                    'prize_pool': prize_pool,
                    'url': url,
                    'date_added': TODAY,
                    '_source': 'devpost',
                })
            except Exception as e:
                print(f'Devpost entry parse error: {e}')

        if len(hackathons) < 48:
            break
        page += 1
        time.sleep(REQUEST_DELAY)

    print(f'Devpost: {len(results)} raw events')
    return results


def scrape_devfolio() -> list:
    results = []
    try:
        resp = requests.get(
            'https://devfolio.co/api/search/hackathons',
            params={'status': 'upcoming', 'limit': 48},
            timeout=REQUEST_TIMEOUT,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; hackathon-scraper/1.0)',
                'Accept': 'application/json',
            },
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f'Devfolio: fetch error — {e}')
        return results

    hackathons = data if isinstance(data, list) else data.get('hackathons', []) or data.get('results', [])

    for h in hackathons:
        try:
            name = h.get('name', '') or h.get('title', '')
            if not name:
                continue
            name = name.strip()

            slug = h.get('slug', '') or h.get('id', '')
            url = h.get('url', '') or (f'https://devfolio.co/hackathons/{slug}' if slug else '')

            location = h.get('location', '') or 'Virtual'
            if not location or location.lower() in ('online', 'virtual', ''):
                location = 'Virtual'
                mode = 'Virtual'
            elif 'hybrid' in location.lower():
                mode = 'Hybrid'
            else:
                mode = 'In-Person'

            start_date = h.get('starts_at', h.get('start_date', TODAY))[:10] if h.get('starts_at') or h.get('start_date') else TODAY
            end_date = h.get('ends_at', h.get('end_date', start_date))[:10] if h.get('ends_at') or h.get('end_date') else start_date

            prize_info = h.get('prizes', '') or h.get('prize_amount', '')
            prize_pool = 'Unknown'
            if prize_info:
                m = re.search(r'\$[\d,]+', str(prize_info))
                if m:
                    prize_pool = m.group(0)

            results.append({
                'name': name,
                'organizer': h.get('organization', {}).get('name', 'Unknown') if isinstance(h.get('organization'), dict) else 'Unknown',
                'location': location,
                'mode': mode,
                'start_date': start_date,
                'end_date': end_date,
                'open_to': 'All',
                'prize_pool': prize_pool,
                'url': url,
                'date_added': TODAY,
                '_source': 'devfolio',
            })
        except Exception as e:
            print(f'Devfolio entry parse error: {e}')

    print(f'Devfolio: {len(results)} raw events')
    return results


_HACKCLUB_SKIP_URL_PATTERNS = [
    'list-of-hackathons-in',
    'submissions/new',
    'hackathons.hackclub.com/#',
    'github.com',
    'twitter.com',
    'discord.gg',
]
_HACKCLUB_SKIP_NAMES = {
    'here', 'submit', 'open source on github', 'add your event', 'submitadd your event',
    'view all', 'see all', 'learn more', 'apply', 'register',
}
_GENERIC_GEO_NAMES = {
    'los angeles', 'chicago', 'new york', 'the bay area', 'the usa', 'canada',
    'asia pacific', 'singapore', 'london', 'berlin', 'india', 'europe',
    'boston', 'seattle', 'austin', 'miami', 'toronto', 'bangalore',
}


def scrape_hackclub() -> list:
    results = []
    try:
        resp = requests.get(
            'https://hackathons.hackclub.com',
            timeout=REQUEST_TIMEOUT,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; hackathon-scraper/1.0)'},
        )
        resp.raise_for_status()
    except Exception as e:
        print(f'HackClub: fetch error — {e}')
        return results

    soup = BeautifulSoup(resp.text, 'html.parser')
    cards = soup.select('article, [class*="card"], [class*="event"], [class*="hackathon"]')
    if not cards:
        cards = soup.select('a[href]')

    for card in cards:
        try:
            if card.name == 'a':
                link_el = card
                href = card.get('href', '')
            else:
                link_el = card.select_one('a[href]')
                if not link_el:
                    continue
                href = link_el.get('href', '')

            if not href:
                continue

            if href.startswith('/'):
                href = 'https://hackathons.hackclub.com' + href

            if any(pat in href for pat in _HACKCLUB_SKIP_URL_PATTERNS):
                continue

            if href.startswith('https://hackathons.hackclub.com') and '/hackathons/' not in href:
                continue

            name_el = card.select_one('h2, h3, h4, [class*="name"], [class*="title"]')
            if not name_el and card.name != 'a':
                name_el = card.select_one('strong, b')
            name = name_el.get_text(strip=True) if name_el else card.get_text(strip=True)[:80]

            name = ' '.join(name.split())

            if not name or len(name) < 5:
                continue

            if name.lower() in _HACKCLUB_SKIP_NAMES:
                continue
            if name.lower() in _GENERIC_GEO_NAMES:
                continue

            location_el = card.select_one('[class*="location"], [class*="city"]')
            location = location_el.get_text(strip=True) if location_el else ''
            if not location:
                location = 'Virtual'
                mode = 'Virtual'
            else:
                mode = 'In-Person'

            results.append({
                'name': name,
                'organizer': 'Hack Club',
                'location': location,
                'mode': mode,
                'start_date': TODAY,
                'end_date': TODAY,
                'open_to': 'High School',
                'prize_pool': 'Unknown',
                'url': href,
                'date_added': TODAY,
                '_source': 'hackclub',
            })
        except Exception as e:
            print(f'HackClub card parse error: {e}')

    seen_urls = set()
    deduped = []
    for r in results:
        u = r.get('url', '')
        if u and u not in seen_urls:
            seen_urls.add(u)
            deduped.append(r)

    print(f'HackClub: {len(deduped)} raw events')
    return deduped


COMPETITOR_REPOS = [
    'https://raw.githubusercontent.com/Lucasgarciamdz/hackathons/main/README.md',
    'https://raw.githubusercontent.com/japrogramer/awesome-hackathons/master/README.md',
]


def parse_markdown_table(text: str) -> list:
    results = []
    in_table = False
    header_seen = False

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('|'):
            in_table = False
            header_seen = False
            continue

        if re.match(r'\|[-| :]+\|', line):
            in_table = True
            header_seen = True
            continue

        if in_table and header_seen and line.startswith('|'):
            cells = [c.strip() for c in line.strip('|').split('|')]
            if not cells:
                continue
            first_cell = cells[0]

            link_match = re.search(r'\[([^\]]+)\]\((https?://[^)]+)\)', first_cell)
            if link_match:
                name = link_match.group(1).strip()
                url = link_match.group(2).strip()
            else:
                name = re.sub(r'\*+', '', first_cell).strip()
                url = ''
                for cell in cells:
                    m = re.search(r'https?://[^\s\)]+', cell)
                    if m:
                        url = m.group(0)
                        break

            if not name or len(name) < 3:
                continue

            results.append({
                'name': name,
                'url': url,
            })

    return results


def scrape_competitor_repos() -> list:
    results = []
    for repo_url in COMPETITOR_REPOS:
        try:
            resp = requests.get(
                repo_url,
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; hackathon-scraper/1.0)'},
            )
            resp.raise_for_status()
            parsed = parse_markdown_table(resp.text)
            for item in parsed:
                results.append({
                    'name': item['name'],
                    'organizer': 'Unknown',
                    'location': 'Unknown',
                    'mode': 'In-Person',
                    'start_date': TODAY,
                    'end_date': TODAY,
                    'open_to': 'All',
                    'prize_pool': 'Unknown',
                    'url': item['url'],
                    'date_added': TODAY,
                    '_source': 'competitor-repo',
                })
            print(f'Competitor repo {repo_url}: {len(parsed)} entries')
            time.sleep(REQUEST_DELAY)
        except Exception as e:
            print(f'Competitor repo error ({repo_url}): {e}')

    return results


def scrape_known() -> list:
    if not KNOWN_FILE.exists():
        return []
    with open(KNOWN_FILE) as f:
        data = yaml.safe_load(f)
    results = []
    for h in data.get('hackathons', []):
        name = h.get('name', '').strip()
        url = normalize_url(h.get('url', '').strip())
        if not name or not url:
            continue
        results.append({
            'name': name,
            'organizer': h.get('organizer', 'Unknown').strip(),
            'location': h.get('location', 'Unknown').strip(),
            'mode': h.get('mode', 'In-Person'),
            'start_date': TODAY,
            'end_date': TODAY,
            'open_to': h.get('open_to', 'All'),
            'prize_pool': 'Unknown',
            'url': url,
            'date_added': TODAY,
            '_source': 'known',
        })
    print(f'Known hackathons: {len(results)} entries')
    return results


def seen_key(entry: dict) -> str:
    url_norm = normalize_url(entry.get('url', ''))
    if url_norm:
        return url_norm
    return f'{entry.get("name", "").lower().strip()}::{entry.get("organizer", "").lower().strip()}'


def main():
    listings = load_json(LISTINGS_FILE, [])
    seen = load_json(SEEN_FILE, {})

    candidates = []
    candidates.extend(scrape_known())
    candidates.extend(scrape_mlh())
    candidates.extend(scrape_devpost())
    candidates.extend(scrape_devfolio())
    candidates.extend(scrape_hackclub())
    candidates.extend(scrape_competitor_repos())

    print(f'\nTotal raw candidates: {len(candidates)}')

    upcoming = [c for c in candidates if not is_past(c.get('end_date', TODAY))]
    print(f'After filtering past events: {len(upcoming)}')

    added = 0
    for entry in upcoming:
        key = seen_key(entry)
        if key in seen:
            continue

        clean_entry = {k: v for k, v in entry.items() if not k.startswith('_')}

        if add_hackathon(listings, clean_entry, seen):
            added += 1
            print(f'Added: {clean_entry["name"]}')

            listings.sort(key=lambda e: e.get('start_date', ''))
            save_json(LISTINGS_FILE, listings)

            subprocess.run(['python3', '.github/scripts/rebuild_readme.py'], check=True)

            commit_entry(clean_entry)

        seen[key] = TODAY

    save_json(SEEN_FILE, seen)
    print(f'\nDone. New hackathons added: {added}')
    return added


if __name__ == '__main__':
    main()
