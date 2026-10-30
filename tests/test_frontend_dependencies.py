"""Every JS package a page imports must be declared in ``reflex.lock/package.json``.

The Python-only CI jobs never build the frontend, so a component that pulls in
a package missing from the manifest would otherwise only fail at export time.
Relies on private Reflex attributes (``_pages``, ``_unevaluated_pages``,
``_compile_page``, ``_get_all_imports``); re-verify them when bumping Reflex.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).parent.parent
MANIFEST = ROOT_DIR / "reflex.lock" / "package.json"

# Specifiers that are not npm installs: Reflex-generated modules, absolute or
# relative paths, and URLs.
NON_PACKAGE_PREFIXES = ("$/", "/", ".", "http")


def split_import(lib: str) -> tuple[str, str | None] | None:
    """Split an import key into ``(package_name, pinned_version)``.

    Args:
        lib: A key from a component import dict, e.g. ``@scope/pkg/sub@1.0.0``.

    Returns:
        The package root and optional pinned version, or None if the key is
        not an npm package.
    """
    if not lib or lib.startswith(NON_PACKAGE_PREFIXES):
        return None
    scoped = lib.startswith("@")
    name_and_path, sep, version = (
        lib[1:].partition("@") if scoped else lib.partition("@")
    )
    if scoped:
        name_and_path = "@" + name_and_path
    parts = name_and_path.split("/")
    name = "/".join(parts[: 2 if scoped else 1])
    return name, (version if sep else None)


def declared_packages() -> dict[str, str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {**manifest["dependencies"], **manifest.get("devDependencies", {})}


def collect_page_imports() -> dict[str, set[str]]:
    """Compile every registered page and map package name to pinned versions."""
    from web.web import app  # noqa: PLC0415  # keep split_import tests cheap

    imports: dict[str, set[str]] = {}
    for route in list(app._unevaluated_pages):  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        app._compile_page(route)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        for lib in app._pages[route]._get_all_imports():  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            parsed = split_import(lib)
            if parsed is None:
                continue
            name, version = parsed
            imports.setdefault(name, set())
            if version:
                imports[name].add(version)
    return imports


@pytest.mark.parametrize(
    ("lib", "expected"),
    [
        ("clsx@2.1.1", ("clsx", "2.1.1")),
        ("@base-ui/react@1.6.0", ("@base-ui/react", "1.6.0")),
        ("@base-ui/react/dialog", ("@base-ui/react", None)),
        (
            "react-syntax-highlighter/dist/esm/styles/prism/one-dark",
            ("react-syntax-highlighter", None),
        ),
        ("react", ("react", None)),
        ("$/utils/state", None),
        ("", None),
    ],
)
def test_split_import(lib: str, expected: tuple[str, str | None] | None) -> None:
    assert split_import(lib) == expected


def test_all_page_imports_are_declared_in_manifest() -> None:
    declared = declared_packages()
    imports = collect_page_imports()

    missing = sorted(name for name in imports if name not in declared)
    assert not missing, (
        f"Packages imported by pages but absent from {MANIFEST.relative_to(ROOT_DIR)}: "
        f"{missing}. Run `uv run reflex export --frontend-only` and commit the "
        "updated reflex.lock, or stop importing the package."
    )

    mismatched = {
        name: (sorted(versions), declared[name])
        for name, versions in imports.items()
        if versions and declared[name] not in versions
    }
    assert not mismatched, f"Pinned versions differ from manifest: {mismatched}"
