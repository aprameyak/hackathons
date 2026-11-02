#!/usr/bin/env python3

import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

LISTINGS_FILE = Path('listings.json')
README_FILE = Path('README.md')
TODAY = date.today().isoformat()
TBA_WINDOW = (date.today() - timedelta(days=45)).isoformat()


def format_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%b %d').replace(' 0', ' ')
    except Exception:
        return date_str


def format_dates(start: str, end: str) -> str:
    if not start:
        return 'Dates TBA'
    try:
        s = datetime.strptime(start, '%Y-%m-%d')
        e = datetime.strptime(end or start, '%Y-%m-%d')
        if s == e:
            return f'{s.strftime("%b")} {s.day}, {s.year}'
        if s.month == e.month and s.year == e.year:
            return f'{s.strftime("%b")} {s.day}–{e.day}, {s.year}'
        elif s.year == e.year:
            return f'{s.strftime("%b")} {s.day} – {e.strftime("%b")} {e.day}, {s.year}'
        else:
            return f'{s.strftime("%b")} {s.day}, {s.year} – {e.strftime("%b")} {e.day}, {e.year}'
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
    end = entry.get('end_date') or ''
    if not end:
        return (entry.get('date_added') or '') >= TBA_WINDOW
    return end >= TODAY


def cell(value: str) -> str:
    return ' '.join(str(value).split()).replace('|', '\\|')


def format_row(entry: dict) -> str:
    name = cell(entry['name'])
    organizer = cell(entry.get('organizer', ''))
    location = cell(entry.get('location', ''))
    mode = cell(entry.get('mode', ''))
    dates_str = format_dates(entry['start_date'], entry['end_date'])
    open_to = cell(entry.get('open_to', ''))
    prize = cell(entry.get('prize_pool', 'Unknown'))
    url = entry.get('url', '').strip()
    date_added = format_date(entry.get('date_added', ''))
    btn = apply_btn(url)
    return f'| {name} | {organizer} | {location} | {mode} | {dates_str} | {open_to} | {prize} | {btn} | {date_added} |'


def build_tables(entries: list) -> tuple:
    upcoming = [e for e in entries if is_upcoming(e)]
    past = [e for e in entries if not is_upcoming(e)]

    upcoming_sorted = sorted(upcoming, key=lambda e: (not e.get('start_date'), e.get('start_date', ''), e['name'].lower()))
    past_sorted = sorted(past, key=lambda e: e.get('start_date') or e.get('date_added', ''), reverse=True)

    return [format_row(e) for e in upcoming_sorted], [format_row(e) for e in past_sorted]


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

    upcoming, past = build_tables(listings)
    content = replace_table(content, 'listings', upcoming)
    content = replace_table(content, 'past', past)
    content = update_stats(content, len(listings))

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print('README.md rebuilt successfully')


if __name__ == '__main__':
    main()
