"""Export a marimo notebook to MDX that is safe to hand to an MDX compiler.

``marimo export md --flavor mdx`` emits prose unescaped, so ``List<int>``,
``{"a": 1}``, LaTeX braces, HTML comments or a line starting with ``import``
break (or inject code into) the MDX build. This script runs the export and
post-processes only the text outside code fences.

Usage: ``uv run python scripts/export_notebook_mdx.py notebook.py -o out.mdx``
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Separator marimo emits between consecutive markdown cells; must survive.
CELL_SEPARATOR = "{/* */}"
_FENCE_OPEN = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,})(?P<info>.*)$")
_HTML_COMMENT = re.compile(r"<!--(.*?)-->")
_ESM_LINE = re.compile(r"^(\s*)(import|export)\b")
_HIDDEN_META = re.compile(r"(?:^|\s)(?:hide-code|disabled)=true(?:\s|$)")
_DROPPED_FRONTMATTER_KEYS = ("marimo-version",)


def _escape_inline(line: str) -> str:
    """Escape ``{``, ``}`` and ``<`` outside inline code spans."""
    out: list[str] = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line):
            out.append(line[i : i + 2])  # already escaped
            i += 2
        elif ch == "`":
            run = len(line[i:]) - len(line[i:].lstrip("`"))
            end = line.find("`" * run, i + run)
            if end == -1:
                out.append(line[i : i + run])
                i += run
            else:
                out.append(line[i : end + run])
                i = end + run
        elif ch in "{}<":
            out.append("\\" + ch)
            i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _escape_prose_line(line: str) -> str:
    if line.strip() == CELL_SEPARATOR:
        return line
    line = _HTML_COMMENT.sub(
        lambda m: "\x00" + m.group(1).replace("*/", "* /") + "\x01",
        line,
    )
    # Split on the comment markers so the comment body is never escaped.
    parts = re.split(r"(\x00.*?\x01)", line)
    rendered = [
        "{/*" + p[1:-1] + "*/}" if p.startswith("\x00") else _escape_inline(p)
        for p in parts
    ]
    result = "".join(rendered)
    return _ESM_LINE.sub(r"\1\\\2", result, count=1)


def _split_frontmatter(text: str) -> tuple[list[str], list[str]]:
    lines = text.split("\n")
    if lines and lines[0] == "---":
        for idx in range(1, len(lines)):
            if lines[idx] == "---":
                return lines[: idx + 1], lines[idx + 1 :]
    return [], lines


def sanitize_mdx(text: str) -> str:
    """Make marimo's MDX export safe to compile.

    Escapes prose, drops ``marimo-config`` fences and fences marked
    ``hide-code``/``disabled``, and strips ``marimo-version`` frontmatter.
    """
    front, body = _split_frontmatter(text)
    front = [
        line
        for line in front
        if not any(line.startswith(f"{k}:") for k in _DROPPED_FRONTMATTER_KEYS)
    ]
    out: list[str] = list(front)
    fence_len = 0  # 0 = not inside a fence
    drop = False
    for line in body:
        if fence_len:
            closing = re.fullmatch(r" {0,3}(`{3,})\s*", line)
            if closing and len(closing.group(1)) >= fence_len:
                fence_len = 0
                if not drop:
                    out.append(line)
                drop = False
            elif not drop:
                out.append(line)
            continue
        opened = _FENCE_OPEN.match(line)
        if opened:
            fence_len = len(opened.group("fence"))
            info = opened.group("info").strip()
            drop = info.startswith("marimo-config") or bool(_HIDDEN_META.search(info))
            if not drop:
                out.append(line)
            continue
        out.append(_escape_prose_line(line))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out))


def export(notebook: Path) -> str:
    """Run ``marimo export md --flavor mdx`` and return sanitized MDX."""
    proc = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "marimo",
            "export",
            "md",
            str(notebook),
            "--flavor",
            "mdx",
            "-o",
            "/dev/stdout",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return sanitize_mdx(proc.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(export(args.notebook), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
