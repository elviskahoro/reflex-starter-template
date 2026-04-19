#!/usr/bin/env python3
"""Hide the 'Built with Reflex' watermark in the built frontend bundle.

Strategy: append a CSS rule to the global stylesheet that hides any anchor
pointing at the bare https://reflex.dev URL. The selector is exact-match,
so the demo's https://reflex.dev/docs/... link is unaffected.

Runs against the unzipped frontend output (default: /srv).
"""

import sys
from pathlib import Path

HIDE_RULE = 'a[href="https://reflex.dev"]{display:none!important}'
CSS_GLOB = "assets/__reflex_global_styles-*.css"


def hide_watermark(srv_dir: Path) -> bool:
    matches = sorted(srv_dir.glob(CSS_GLOB))
    if not matches:
        print(f"ERROR: no CSS file matched {srv_dir / CSS_GLOB}", file=sys.stderr)
        return False

    patched_any = False
    for css in matches:
        text = css.read_text()
        if HIDE_RULE in text:
            print(f"skip (already patched): {css}")
            continue
        css.write_text(text.rstrip() + "\n" + HIDE_RULE + "\n")
        print(f"patched: {css}")
        patched_any = True

    return patched_any or all(HIDE_RULE in m.read_text() for m in matches)


if __name__ == "__main__":
    srv = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/srv")
    sys.exit(0 if hide_watermark(srv) else 1)
