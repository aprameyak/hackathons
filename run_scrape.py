#!/usr/bin/env python3

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent

sys.path.insert(0, str(REPO_ROOT / '.github' / 'scripts'))

from scrape_hackathons import main  # noqa: E402

if __name__ == '__main__':
    main()
