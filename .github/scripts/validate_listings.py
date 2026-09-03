#!/usr/bin/env python3
"""
Validate listings.json for the hackathons tracker repo.
Exits 0 if clean, 1 if violations are found.

Run from repo root: python3 .github/scripts/validate_listings.py
"""

import json
import re
import sys
from pathlib import Path

LISTINGS_FILE = Path('listings.json')

VALID_MODES = {'In-Person', 'Virtual', 'Hybrid'}
VALID_OPEN_TO = {'College', 'High School', 'All', 'Grad'}
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
PRIZE_RE = re.compile(r'^\$[\d,]+$|^Unknown$')


def validate_entry(entry: dict) -> list:
    violations = []
    name = entry.get('name', '<unknown>')

    # Required fields
    for field in ['name', 'organizer', 'location', 'mode', 'start_date',
                  'end_date', 'open_to', 'prize_pool', 'url', 'date_added']:
        if field not in entry:
            violations.append(f'missing required field: {field}')

    # mode
    mode = entry.get('mode', '')
    if mode and mode not in VALID_MODES:
        violations.append(f'invalid mode: {mode!r} (must be one of {sorted(VALID_MODES)})')

    # open_to
    open_to = entry.get('open_to', '')
    if open_to and open_to not in VALID_OPEN_TO:
        violations.append(f'invalid open_to: {open_to!r} (must be one of {sorted(VALID_OPEN_TO)})')

    # date format
    start = entry.get('start_date', '')
    end = entry.get('end_date', '')
    date_added = entry.get('date_added', '')

    if start and not DATE_RE.match(start):
        violations.append(f'start_date not YYYY-MM-DD: {start!r}')
    if end and not DATE_RE.match(end):
        violations.append(f'end_date not YYYY-MM-DD: {end!r}')
    if date_added and not DATE_RE.match(date_added):
        violations.append(f'date_added not YYYY-MM-DD: {date_added!r}')

    # start <= end
    if start and end and DATE_RE.match(start) and DATE_RE.match(end):
        if start > end:
            violations.append(f'start_date {start!r} is after end_date {end!r}')

    # url: empty or starts with https://
    url = entry.get('url', '')
    if url and not url.startswith('https://'):
        violations.append(f'url must start with https:// or be empty: {url!r}')

    # prize_pool format
    prize = entry.get('prize_pool', '')
    if prize and not PRIZE_RE.match(prize):
        violations.append(
            f'prize_pool must be "Unknown" or "$X,XXX" format: {prize!r}'
        )

    return [(name, v) for v in violations]


def validate_duplicate_urls(listings: list) -> list:
    seen = {}
    violations = []
    for entry in listings:
        url = entry.get('url', '').strip()
        if not url:
            continue
        norm = url.split('?')[0].lower().rstrip('/')
        if norm in seen:
            other = seen[norm]
            violations.append((
                entry.get('name', ''),
                f'duplicate URL also used by {other.get("name")!r}',
            ))
        else:
            seen[norm] = entry
    return violations


def main():
    if not LISTINGS_FILE.exists():
        print(f'{LISTINGS_FILE} not found')
        sys.exit(1)

    with open(LISTINGS_FILE) as f:
        listings = json.load(f)

    all_violations = []
    for entry in listings:
        all_violations.extend(validate_entry(entry))
    all_violations.extend(validate_duplicate_urls(listings))

    print(f'Validated {len(listings)} listing(s)')
    if all_violations:
        print(f'Found {len(all_violations)} violation(s):')
        for name, reason in all_violations:
            print(f'  - {name}: {reason}')
        sys.exit(1)

    print('All listings pass validation checks')
    sys.exit(0)


if __name__ == '__main__':
    main()
