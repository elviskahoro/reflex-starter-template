"""Escaper tests for scripts/export_notebook_mdx.py, one per failure mode."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "export_notebook_mdx",
    Path(__file__).parent.parent / "scripts" / "export_notebook_mdx.py",
)
assert _SPEC is not None
assert _SPEC.loader is not None
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
sanitize = _MOD.sanitize_mdx


@pytest.mark.parametrize(
    ("src", "expected"),
    [
        ("List<int> and x<y", r"List\<int> and x\<y"),
        ("<b>x</b>", r"\<b>x\</b>"),
        ('{"a": 1}', r'\{"a": 1\}'),
        ("use {key} here", r"use \{key\} here"),
        (r"$$\frac{a}{b}$$", r"$$\frac\{a\}\{b\}$$"),
        ("<!-- note -->", "{/* note */}"),
        ("import x from 'y'", "\\import x from 'y'"),
        ("export const x = 1", "\\export const x = 1"),
        ("already \\{ escaped", "already \\{ escaped"),
        ("keep `{code}` span {x}", "keep `{code}` span \\{x\\}"),
        ("{/* */}", "{/* */}"),
    ],
)
def test_prose_escaping(src: str, expected: str) -> None:
    assert sanitize(src) == expected


def test_code_fences_untouched() -> None:
    src = "````python marimo\nx = {1: '<a>'}\n```\nimport os\n````\n{a}"
    assert sanitize(src) == src[:-3] + "\\{a\\}"


def test_hidden_and_config_fences_dropped() -> None:
    src = (
        "```marimo-config\n# /// script\n```\n"
        "```python marimo hide-code=true\nimport marimo as mo\n```\n"
        "```python marimo disabled=true\nx=1\n```\n"
        "```python marimo\ny=2\n```"
    )
    assert sanitize(src) == "```python marimo\ny=2\n```"


def test_frontmatter_version_dropped_and_not_escaped() -> None:
    src = "---\ntitle: 'A {v1}'\nmarimo-version: 0.25.1\n---\n\nText"
    assert sanitize(src) == "---\ntitle: 'A {v1}'\n---\n\nText"


def test_blank_lines_in_code_preserved() -> None:
    src = "```python marimo\na = 1\n\n\nb = 2\n```"
    assert sanitize(src) == src


def test_export_end_to_end(tmp_path: Path) -> None:
    nb = tmp_path / "nb.py"
    nb.write_text(
        "import marimo\napp = marimo.App()\n\n@app.cell\ndef _(mo):\n"
        '    mo.md("List<int> {a}")\n    return\n',
    )
    out = _MOD.export(nb)
    assert r"List\<int> \{a\}" in out
