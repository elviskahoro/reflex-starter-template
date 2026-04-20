#!/usr/bin/env python3
"""Remove the 'Built with Reflex' watermark from the built frontend bundle.

Strategy: find and remove the anchor element linking to https://reflex.dev
from all HTML files in the frontend output.

Runs against the unzipped frontend output (default: /srv).
"""

import re
import sys
from pathlib import Path


def remove_watermark(srv_dir: Path) -> bool:
    html_files = list(srv_dir.glob("**/*.html"))
    if not html_files:
        print(f"ERROR: no HTML files found in {srv_dir}", file=sys.stderr)
        return False

    removed_any = False
    for html_file in html_files:
        content = html_file.read_text()

        # Remove the "Built with Reflex" link element
        # Handles: <a href="https://reflex.dev" ...>...Built with Reflex...</a>
        pattern = r'<a[^>]*href=["\']https://reflex\.dev["\'][^>]*>.*?Built with Reflex.*?</a>'
        new_content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

        if new_content != content:
            html_file.write_text(new_content)
            print(f"removed watermark from: {html_file.relative_to(srv_dir)}")
            removed_any = True

    return removed_any


if __name__ == "__main__":
    srv = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/srv")
    sys.exit(0 if remove_watermark(srv) else 1)
