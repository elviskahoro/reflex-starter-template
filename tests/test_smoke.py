"""Smoke net for the starter template.

Builds `index_page()` so reflex's compile-time state-binding and
component plumbing run without booting the backend; the same code
`reflex export` runs in CI. status_card is exercised both via the
page factory and directly with literal inputs, plus against the
real IndexState Var shape the in-repo caller uses.

The earlier async-context test was dropped: `index_page()` is fully
synchronous, so awaiting in the test loop did not actually exercise
any async machinery. pytest-asyncio is intentionally NOT in the
dev group -- adding it back requires a real async regression, not
a placeholder.
"""

from __future__ import annotations

import reflex as rx

from web.components.status_card import status_card
from web.pages.index import (
    IndexState,
    page as index_page,
)


class _TestState(rx.State):
    """Empty `rx.State` subclass used as a handler host for direct status_card tests.

    reflex accepts plain functions or coroutines for `on_click` only via
    a State-bound `@rx.event` slot. `_TestState.dummy_handler` is the
    simplest such shape; the handler is never invoked because the
    tests do not call rx.event_chain. Declaring it on a real
    `rx.State` keeps reflex's static analyzer happy.
    """

    @rx.event
    async def dummy_handler(self) -> None:
        """Stub hand-off reference; smoke tests never trigger it."""


def test_index_page_builds_with_status_card() -> None:
    # Build the page. status_card is constructed inside the factory with
    # IndexState.message and IndexState.count (Var inputs), so its
    # signature, EventType wiring, and rx.Component return are all
    # exercised -- the same path production takes at `reflex export`.
    rendered = index_page()
    assert isinstance(rendered, rx.Component)

    # The render tree is a JSON-shaped dict. Stable user-visible copy
    # is the regression marker: a refactor that drops the heading or
    # status_card's markers breaks the test without leaning on the
    # isinstance guard above.
    tree = str(rendered.render())
    assert "Welcome to Reflex" in tree
    assert "Backend Status" in tree
    assert "Total requests" in tree


def test_status_card_accepts_literal_inputs() -> None:
    # Direct construction with literal str + int catches signature drift
    # before it breaks the only in-repo caller. The handler slot is
    # bound via `_TestState.dummy_handler` so reflex's EventSpec
    # resolution does not need to coerce a free function.
    rendered = status_card("Hello, smoke net!", 7, _TestState.dummy_handler)
    assert isinstance(rendered, rx.Component)

    tree = str(rendered.render())
    assert "Hello, smoke net!" in tree
    assert "Total requests: 7" in tree


def test_status_card_accepts_index_state_vars() -> None:
    # Drives status_card with reflex `Var` inputs the same way the
    # in-repo caller does. `IndexState.message` and `IndexState.count`
    # are Var references (not literal values); status_card accepts them
    # because its annotations (`str`, `int`) are wide enough to cover
    # `Var[str]` and `Var[int]` at runtime. A future tightening of
    # those annotations into `Literal[str]` / `Literal[int]` would
    # reject Vars here.
    rendered = status_card(
        IndexState.message,
        IndexState.count,
        IndexState.increment_and_greet,
    )
    assert isinstance(rendered, rx.Component)

    # Var-backed inputs do not render their resolved values here
    # (state is not bound at smoke-test time); instead the JS-side
    # identifier of the Var appears in the emitted tree. Asserting
    # on those identifiers keeps the test robust against reflex's
    # internal binding representation, while still proving the Vars
    # flowed through.
    tree = str(rendered.render())
    assert "index_state.message" in tree
    assert "index_state.count" in tree
