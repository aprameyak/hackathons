#!/usr/bin/env python3
"""
Scrape multiple sources for upcoming hackathons and add new entries to
listings.json. Called by GitHub Actions (scrape-hackathons.yml) and by
run_scrape.py for local runs.

Sources:
  1. MLH           — https://mlh.io/seasons/2027/events (and 2026)
  2. Devpost API   — https://devpost.com/api/hackathons?...
  3. Devfolio API  — https://devfolio.co/api/search/hackathons?...
  4. HackClub      — https://hackathons.hackclub.com
  5. Competitor repos — markdown table parsing

Run from repo root: python3 .github/scripts/scrape_hackathons.py
"""

import json
import os
import re
import subprocess
import time
import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

LISTINGS_FILE = Path('listings.json')
SEEN_FILE = Path('.github/data/seen_hackathons.json')

REQUEST_TIMEOUT = 15
REQUEST_DELAY = 0.5

TODAY = datetime.date.today().isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    return url.strip().split('?')[0].rstrip('/')


def is_past(end_date: str) -> bool:
    """Return True if the hackathon has already ended."""
    try:
        return end_date < TODAY
    except Exception:
        return False


def add_hackathon(listings: list, entry: dict, seen: dict) -> bool:
    """
    Add entry to listings if not a duplicate. Returns True if added.
    Deduplicates by normalized URL and by name+organizer.
    """
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
    """Git add/commit a single new hackathon entry."""
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


# ---------------------------------------------------------------------------
# Source 1: MLH
# ---------------------------------------------------------------------------

def scrape_mlh() -> list:
    """Scrape MLH season pages for hackathon event cards."""
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

        # MLH event cards are typically <div class="event"> or <a class="event">
        cards = soup.select('div.event, a.event, .event-wrapper')
        if not cards:
            # fallback: look for any anchor with event-like class
            cards = soup.select('[class*="event"]')

        for card in cards:
            try:
                # Name
                name_el = card.select_one('h3, h2, .event-name, [class*="name"]')
                name = name_el.get_text(strip=True) if name_el else ''
                if not name:
                    continue

                # URL
                link_el = card if card.name == 'a' else card.select_one('a')
                href = link_el.get('href', '') if link_el else ''
                if href and not href.startswith('http'):
                    href = 'https://mlh.io' + href

                # Location / mode
                loc_el = card.select_one('.event-location, [class*="location"], [class*="city"]')
                location = loc_el.get_text(strip=True) if loc_el else 'Unknown'

                # Mode badge
                mode = 'In-Person'
                mode_el = card.select_one('[class*="hybrid"], [class*="virtual"], [class*="online"], [class*="mode"]')
                if mode_el:
                    badge_text = mode_el.get_text(strip=True).lower()
                    if 'hybrid' in badge_text:
                        mode = 'Hybrid'
                    elif 'virtual' in badge_text or 'online' in badge_text:
                        mode = 'Virtual'

                # Date
                date_el = card.select_one('.event-date, [class*="date"], time')
                date_text = date_el.get_text(strip=True) if date_el else ''
                start_date = TODAY  # placeholder — hard to parse reliably
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


# ---------------------------------------------------------------------------
# Source 2: Devpost API
# ---------------------------------------------------------------------------

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

                # Mode inference
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

                # Parse submission period dates
                # Devpost format examples:
                #   "Sep 01, 2026 - Sep 02, 2026"
                #   "Sep 1 – Sep 2, 2026"
                #   "September 1 - 2, 2026"
                period = h.get('submission_period_dates', '') or ''
                start_date = TODAY
                end_date = TODAY

                def _parse_devpost_dates(text):
                    """Return (start_iso, end_iso) or (None, None)."""
                    # Normalize dash variants
                    text = text.replace('–', '-').replace('—', '-')
                    # Pattern: "Mon DD, YYYY - Mon DD, YYYY"
                    m = re.search(
                        r'(\w+ \d{1,2},?\s*\d{4})\s*-\s*(\w+ \d{1,2},?\s*\d{4})',
                        text,
                    )
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
                    # Pattern: "Mon DD - DD, YYYY"
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
                    # Pattern: single date "Mon DD, YYYY"
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


# ---------------------------------------------------------------------------
# Source 3: Devfolio
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Source 4: HackClub
# ---------------------------------------------------------------------------

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
    # Target specific hackathon card containers — avoid broad link sweeps
    cards = soup.select('article, [class*="card"], [class*="event"], [class*="hackathon"]')
    if not cards:
        # Fallback: look for anchor tags that point to external hackathon sites
        cards = soup.select('a[href]')

    for card in cards:
        try:
            # If card is an <a> tag use it directly, otherwise find first link
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

            # Resolve relative URLs
            if href.startswith('/'):
                href = 'https://hackathons.hackclub.com' + href

            # Skip known garbage URL patterns
            if any(pat in href for pat in _HACKCLUB_SKIP_URL_PATTERNS):
                continue

            # Must link away from hackathons.hackclub.com itself (actual events live elsewhere)
            if href.startswith('https://hackathons.hackclub.com') and '/hackathons/' not in href:
                continue

            name_el = card.select_one('h2, h3, h4, [class*="name"], [class*="title"]')
            if not name_el and card.name != 'a':
                name_el = card.select_one('strong, b')
            name = name_el.get_text(strip=True) if name_el else card.get_text(strip=True)[:80]

            # Strip leading/trailing whitespace and collapse internal whitespace
            name = ' '.join(name.split())

            if not name or len(name) < 5:
                continue

            # Skip nav/footer link text
            if name.lower() in _HACKCLUB_SKIP_NAMES:
                continue
            # Skip entries that are just geographic names (city/region listing pages)
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

    # Deduplicate by url
    seen_urls = set()
    deduped = []
    for r in results:
        u = r.get('url', '')
        if u and u not in seen_urls:
            seen_urls.add(u)
            deduped.append(r)

    print(f'HackClub: {len(deduped)} raw events')
    return deduped


# ---------------------------------------------------------------------------
# Source 5: Competitor repos (markdown table parsing)
# ---------------------------------------------------------------------------

COMPETITOR_REPOS = [
    'https://raw.githubusercontent.com/Lucasgarciamdz/hackathons/main/README.md',
    'https://raw.githubusercontent.com/japrogramer/awesome-hackathons/master/README.md',
]


def parse_markdown_table(text: str) -> list:
    """Parse markdown table rows — extract name (column 0) and URL from markdown links."""
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

            # Extract name and URL from markdown link [name](url)
            link_match = re.search(r'\[([^\]]+)\]\((https?://[^)]+)\)', first_cell)
            if link_match:
                name = link_match.group(1).strip()
                url = link_match.group(2).strip()
            else:
                name = re.sub(r'\*+', '', first_cell).strip()
                # Look for URL in any cell
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


# ---------------------------------------------------------------------------
# Deduplication key for seen tracking
# ---------------------------------------------------------------------------

def seen_key(entry: dict) -> str:
    url_norm = normalize_url(entry.get('url', ''))
    if url_norm:
        return url_norm
    return f'{entry.get("name", "").lower().strip()}::{entry.get("organizer", "").lower().strip()}'


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    listings = load_json(LISTINGS_FILE, [])
    seen = load_json(SEEN_FILE, {})

    candidates = []
    candidates.extend(scrape_mlh())
    candidates.extend(scrape_devpost())
    candidates.extend(scrape_devfolio())
    candidates.extend(scrape_hackclub())
    candidates.extend(scrape_competitor_repos())

    print(f'\nTotal raw candidates: {len(candidates)}')

    # Filter out past hackathons
    upcoming = [c for c in candidates if not is_past(c.get('end_date', TODAY))]
    print(f'After filtering past events: {len(upcoming)}')

    added = 0
    for entry in upcoming:
        key = seen_key(entry)
        if key in seen:
            continue

        # Strip internal _source/_raw_date keys before writing
        clean_entry = {k: v for k, v in entry.items() if not k.startswith('_')}

        if add_hackathon(listings, clean_entry, seen):
            added += 1
            print(f'Added: {clean_entry["name"]}')

            # Sort listings by start_date ascending before saving
            listings.sort(key=lambda e: e.get('start_date', ''))
            save_json(LISTINGS_FILE, listings)

            # Rebuild README
            subprocess.run(['python3', '.github/scripts/rebuild_readme.py'], check=True)

            # Git commit this entry individually
            commit_entry(clean_entry)

        seen[key] = TODAY

    save_json(SEEN_FILE, seen)
    print(f'\nDone. New hackathons added: {added}')
    return added


if __name__ == '__main__':
    main()
