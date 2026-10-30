"""Regression: `cn()` imports must not carry a slash-suffixed package_path."""

from __future__ import annotations

from web.components.ui.core import cn


def _import_vars(package: str) -> list:
    imports = cn("a", "b")._get_all_var_data().imports  # noqa: SLF001
    return [iv for pkg, ivs in imports if pkg == package for iv in ivs]


def test_clsx_import_has_empty_package_path() -> None:
    ivs = _import_vars("clsx")
    assert ivs
    assert all(iv.package_path == "" for iv in ivs)
    assert all(iv.is_default for iv in ivs)


def test_tailwind_merge_import_has_empty_package_path() -> None:
    ivs = _import_vars("tailwind-merge")
    assert ivs
    assert all(iv.package_path == "" for iv in ivs)


def test_no_agpl_dependency() -> None:
    imports = cn("a")._get_all_var_data().imports  # noqa: SLF001
    assert "clsx-for-tailwind" not in {pkg for pkg, _ in imports}
