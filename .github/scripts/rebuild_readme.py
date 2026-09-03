#!/usr/bin/env python3
"""
Rebuild README.md table between TABLE_START listings / TABLE_END listings
from listings.json. Also updates the <!-- STATS --> line.

Run from repo root: python3 .github/scripts/rebuild_readme.py
"""

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

LISTINGS_FILE = Path('listings.json')
README_FILE = Path('README.md')
TODAY = date.today().isoformat()


def format_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%b %d').replace(' 0', ' ')
    except Exception:
        return date_str


def format_dates(start: str, end: str) -> str:
    """Format date range like 'Sep 19 – 20, 2026' or 'Feb 14 – 16, 2027'."""
    try:
        s = datetime.strptime(start, '%Y-%m-%d')
        e = datetime.strptime(end, '%Y-%m-%d')
        if s.month == e.month and s.year == e.year:
            return f'{s.strftime("%b")} {s.day}–{e.day}, {s.year}'
        elif s.year == e.year:
            return f'{s.strftime("%b")} {s.day} – {e.strftime("%b")} {e.day}, {s.year}'
        else:
            return f'{s.strftime("%b %d, %Y")} – {e.strftime("%b %d, %Y")}'
    except Exception:
        return f'{start} – {end}'


def apply_btn(url: str) -> str:
    if not url:
        return '🔒'
    return (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer">'
        f'<img src="https://i.imgur.com/u1KNU8z.png" width="118" alt="Apply">'
        f'</a>'
    )


def is_upcoming(entry: dict) -> bool:
    try:
        return entry['start_date'] >= TODAY
    except Exception:
        return False


def format_row(entry: dict) -> str:
    name = entry['name'].strip()
    organizer = entry.get('organizer', '').strip()
    location = entry.get('location', '').strip()
    mode = entry.get('mode', '').strip()
    dates_str = format_dates(entry['start_date'], entry['end_date'])
    open_to = entry.get('open_to', '').strip()
    prize = entry.get('prize_pool', 'Unknown').strip()
    url = entry.get('url', '').strip()
    date_added = format_date(entry.get('date_added', ''))
    btn = apply_btn(url)
    return f'| {name} | {organizer} | {location} | {mode} | {dates_str} | {open_to} | {prize} | {btn} | {date_added} |'


def build_table(entries: list) -> list:
    upcoming = [e for e in entries if is_upcoming(e)]
    past = [e for e in entries if not is_upcoming(e)]

    upcoming_sorted = sorted(upcoming, key=lambda e: e['start_date'])
    past_sorted = sorted(past, key=lambda e: e['start_date'], reverse=True)

    rows = []
    if upcoming_sorted:
        for entry in upcoming_sorted:
            rows.append(format_row(entry))
    if past_sorted:
        if upcoming_sorted:
            rows.append('| | | | | | | | | |')
        for entry in past_sorted:
            rows.append(format_row(entry))

    return rows


def replace_table(content: str, marker: str, rows: list) -> str:
    start_marker = f'<!-- TABLE_START {marker} -->'
    end_marker = f'<!-- TABLE_END {marker} -->'
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    if start_idx == -1 or end_idx == -1:
        print(f'ERROR: Could not find markers for table: {marker}')
        sys.exit(1)

    after_start = content[start_idx:]
    sep_match = re.search(r'\| [-| :]+\|\n', after_start)
    if not sep_match:
        print(f'ERROR: Could not find separator row for table: {marker}')
        sys.exit(1)

    header_end = start_idx + sep_match.end()
    header = content[start_idx:header_end]
    footer = content[end_idx:]

    body = '\n'.join(rows) + '\n' if rows else ''
    return content[:start_idx] + header + body + footer


def update_stats(content: str, total: int) -> str:
    return re.sub(
        r'<!-- STATS -->.*?<!-- /STATS -->',
        f'<!-- STATS -->{total} hackathons tracked<!-- /STATS -->',
        content,
    )


def main():
    if not LISTINGS_FILE.exists():
        print('ERROR: listings.json not found')
        sys.exit(1)
    if not README_FILE.exists():
        print('ERROR: README.md not found')
        sys.exit(1)

    with open(LISTINGS_FILE) as f:
        listings = json.load(f)

    print(f'Loaded {len(listings)} listings')

    with open(README_FILE, encoding='utf-8') as f:
        content = f.read()

    rows = build_table(listings)
    content = replace_table(content, 'listings', rows)
    content = update_stats(content, len(listings))

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print('README.md rebuilt successfully')


if __name__ == '__main__':
    main()
