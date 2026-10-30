"""Build the frontend and verify its JS dependencies are consistent.

Needs ``bun`` on PATH (no node). Runs, in order:

1. lockfile    ``bun install --frozen-lockfile`` against a copy of ``reflex.lock``.
2. build       ``reflex export --frontend-only`` (compiles pages, installs, bundles).
3. drift       the build must leave ``reflex.lock`` unchanged.
4. imports     every bare import in the generated ``.web`` sources is declared.
5. knip        ``bunx knip`` reports no unlisted dependencies in ``.web``.

Fast, build-free coverage of the same rule lives in
``tests/test_frontend_dependencies.py``.
"""  # noqa: INP001  # standalone script, not a package

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT_DIR = Path(__file__).resolve().parent.parent
LOCK_DIR = ROOT_DIR / "reflex.lock"
WEB_DIR = ROOT_DIR / ".web"

# Packages Vite/Reflex tooling reaches transitively; they are not ours to pin.
ALLOWED_UNLISTED = {"connect"}  # used by Reflex's vite-plugin-safari-cachebust.js
ALLOWED_PACKAGES = {"react", "react-dom", "react-router"} | ALLOWED_UNLISTED
IMPORT_RE = re.compile(
    r"""(?:\bfrom\s*|\bimport\s*\(?\s*|\bimport\s+)["']([^"']+)["']""",
)
SOURCE_SUFFIXES = {".js", ".jsx", ".mjs", ".ts", ".tsx"}
# Only the generated pages and their components; ``utils``/``components`` hold
# Reflex runtime helpers that no page loads.
SOURCE_DIRS = ("app", "app_components")


def run(*cmd: str, cwd: Path = ROOT_DIR) -> subprocess.CompletedProcess[str]:
    """Run a command capturing output."""
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)  # noqa: S603  # fixed argv, no shell


def package_root(spec: str) -> str | None:
    """Return the npm package for a bare import specifier, else None."""
    if spec.startswith((".", "/", "$/", "http", "node:", "virtual:")):
        return None
    parts = spec.split("/")
    return "/".join(parts[: 2 if spec.startswith("@") else 1])


def declared(package_json: Path) -> set[str]:
    """Return package names declared in a package.json."""
    data = json.loads(package_json.read_text(encoding="utf-8"))
    return set(data.get("dependencies", {})) | set(data.get("devDependencies", {}))


def snapshot_lock() -> dict[str, str]:
    """Map each reflex.lock file name to its text."""
    return {p.name: p.read_text(encoding="utf-8") for p in LOCK_DIR.iterdir()}


def check_lockfile() -> list[str]:
    """Check package.json and bun.lock agree."""
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("package.json", "bun.lock"):
            shutil.copy(LOCK_DIR / name, tmp)
        result = run("bun", "install", "--frozen-lockfile", cwd=Path(tmp))
    if result.returncode:
        return [f"bun install --frozen-lockfile failed:\n{result.stderr.strip()}"]
    return []


def check_build() -> list[str]:
    """Build the frontend with reflex export."""
    result = run(
        sys.executable,
        "-m",
        "reflex",
        "export",
        "--frontend-only",
        "--no-zip",
    )
    if result.returncode:
        return [
            f"reflex export failed:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}",
        ]
    return []


def check_drift() -> list[str]:
    """Fail if the build rewrote reflex.lock."""
    changed = [n for n, text in snapshot_lock().items() if text != LOCK_BEFORE.get(n)]
    if changed:
        names = ",".join(changed)
        return [f"The build rewrote reflex.lock/{{{names}}}; commit the update."]
    return []


def check_imports() -> list[str]:
    """Fail on generated imports missing from the manifest."""
    known = (
        declared(WEB_DIR / "package.json") & declared(LOCK_DIR / "package.json")
        | ALLOWED_PACKAGES
    )
    problems: dict[str, set[str]] = {}
    for dirname in SOURCE_DIRS:
        for path in (WEB_DIR / dirname).rglob("*"):
            if path.suffix not in SOURCE_SUFFIXES or not path.is_file():
                continue
            for spec in IMPORT_RE.findall(path.read_text(encoding="utf-8")):
                name = package_root(spec)
                if name and name not in known:
                    problems.setdefault(name, set()).add(
                        path.relative_to(WEB_DIR).as_posix(),
                    )
    return [
        f"{name} is imported but not declared in reflex.lock/package.json "
        f"(e.g. {min(files)})"
        for name, files in sorted(problems.items())
    ]


def check_knip() -> list[str]:
    """Fail on knip-reported unlisted dependencies."""
    result = run(
        "bunx",
        "knip",
        "--dependencies",
        "--reporter",
        "json",
        "--no-progress",
        cwd=WEB_DIR,
    )
    try:
        issues = json.loads(result.stdout)["issues"]
    except (json.JSONDecodeError, KeyError):
        return [
            f"knip produced no report:\n{result.stdout[-1000:]}{result.stderr[-1000:]}",
        ]
    unlisted = {
        item["name"] for issue in issues for item in issue["unlisted"]
    } - ALLOWED_UNLISTED
    return [f"knip: unlisted dependency {name}" for name in sorted(unlisted)]


LOCK_BEFORE = snapshot_lock()
CHECKS: list[tuple[str, Callable[[], list[str]]]] = [
    ("lockfile", check_lockfile),
    ("build", check_build),
    ("drift", check_drift),
    ("imports", check_imports),
    ("knip", check_knip),
]


def main() -> int:
    """Run all checks; return the process exit code."""
    if shutil.which("bun") is None:
        print("bun is required on PATH", file=sys.stderr)  # noqa: T201
        return 2
    failed = False
    for name, check in CHECKS:
        problems = check()
        print(f"[{'FAIL' if problems else ' ok '}] {name}")  # noqa: T201
        for problem in problems:
            print(f"       {problem}")  # noqa: T201
        failed |= bool(problems)
        if name == "build" and problems:
            break  # later checks need the generated .web directory
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
