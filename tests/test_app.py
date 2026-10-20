"""Tests for the app entrypoint."""

from __future__ import annotations

from web.web import app


def test_index_route_registered() -> None:
    """The index page is registered at the root route."""
    assert list(app._unevaluated_pages) == ["index"]  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]  # no public route listing
