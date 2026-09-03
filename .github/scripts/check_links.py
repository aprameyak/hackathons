#!/usr/bin/env python3
"""
HEAD-check all non-empty URLs in listings.json.
Sets url: "" for dead links (4xx/5xx/timeout).
Rebuilds README after changes.

Run from repo root: python3 .github/scripts/check_links.py
"""

import json
import subprocess
import time
from pathlib import Path

import requests

LISTINGS_FILE = Path('listings.json')
README_FILE = Path('README.md')

REQUEST_DELAY = 0.75
REQUEST_TIMEOUT = 12

SKIP_DOMAINS = []  # add domains to skip if needed


def skip_domain(url: str) -> bool:
    return any(d in url for d in SKIP_DOMAINS)


def check_url(url: str) -> bool:
    if not url:
        return False
    if skip_domain(url):
        return True
    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; hackathon-link-checker/1.0)'},
        )
        return resp.status_code < 400
    except Exception:
        return False


def main():
    with open(LISTINGS_FILE) as f:
        listings = json.load(f)

    changed = False
    for entry in listings:
        url = entry.get('url', '').strip()
        if not url:
            continue

        is_live = check_url(url)
        time.sleep(REQUEST_DELAY)

        if not is_live:
            print(f'Marking closed: {entry["name"]}')
            entry['url'] = ''
            changed = True
        else:
            print(f'OK: {entry["name"]}')

    if changed:
        with open(LISTINGS_FILE, 'w') as f:
            json.dump(listings, f, indent=2)
            f.write('\n')
        subprocess.run(['python3', '.github/scripts/rebuild_readme.py'], check=True)
        print('Updated listings and README.')
    else:
        print('All links are live, no changes needed.')


if __name__ == '__main__':
    main()
