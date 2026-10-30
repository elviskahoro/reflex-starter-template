"""Guard against check-bypass flags in CI configuration.

Fails if any `.rwx/*.y*ml`, `.github/workflows/*.y*ml` or
`.github/dependabot.yml` line contains `--no-verify`, `--no-gpg-sign` or
`--admin`, so CI config cannot skip hooks, signing or merge protections.

`--force` and `--auto` are intentionally not banned: `--force-with-lease`
and `gh pr merge --auto` are legitimate and would be false positives.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CONFIG_GLOBS = (
    ".rwx/*.y*ml",
    ".github/workflows/*.y*ml",
    ".github/dependabot.yml",
)
BANNED_FLAGS = ("--no-verify", "--no-gpg-sign", "--admin")


def _config_files() -> list[Path]:
    return sorted(path for pattern in CONFIG_GLOBS for path in ROOT.glob(pattern))


def _find_violations(path: Path, flags: tuple[str, ...] = BANNED_FLAGS) -> list[str]:
    violations: list[str] = []
    for lineno, line in enumerate(path.read_text().splitlines(), start=1):
        violations.extend(
            f"{path.relative_to(path.parent.parent)}:{lineno}: {flag}"
            for flag in flags
            if re.search(rf"{re.escape(flag)}(?![\w-])", line)
        )
    return violations


def test_config_files_are_found() -> None:
    assert _config_files(), "no CI config matched; guard would be vacuous"


@pytest.mark.parametrize("path", _config_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_no_bypass_flags(path: Path) -> None:
    assert not _find_violations(path)


def test_scanner_detects_bypass_flag(tmp_path: Path) -> None:
    cfg = tmp_path / "ci" / "x.yml"
    cfg.parent.mkdir()
    cfg.write_text("run: git commit --no-verify\nrun: git push --force-with-lease\n")
    assert _find_violations(cfg) == ["ci/x.yml:1: --no-verify"]
