#!/usr/bin/env python3
"""
Local scraper entrypoint for the hackathons tracker.
Run from repo root: python3 run_scrape.py

Imports and runs all scrapers from .github/scripts/scrape_hackathons.py.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent

# Make scripts importable
sys.path.insert(0, str(REPO_ROOT / '.github' / 'scripts'))

from scrape_hackathons import main  # noqa: E402

if __name__ == '__main__':
    main()
