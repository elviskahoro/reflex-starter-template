"""Tests for the index page."""

from __future__ import annotations

import asyncio

import reflex as rx
from hypothesis import (
    given,
    strategies as st,
)

from web.pages.index import page
from web.pages.index.page import IndexState


def test_page_returns_component() -> None:
    """The page function renders a Reflex component."""
    assert isinstance(page(), rx.Component)


@given(count=st.integers(min_value=0))
def test_greeting_mentions_request_count(count: int) -> None:
    """The greeting reports the current request number for any count."""
    state = IndexState()
    state.count = count
    greeting = asyncio.run(state._get_greeting())  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]  # exercising backend helper
    assert greeting.startswith(f"Request #{count} processed at ")
