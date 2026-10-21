"""Status card: a reusable, state-agnostic component."""

from __future__ import annotations

from typing import TYPE_CHECKING

import reflex as rx

if TYPE_CHECKING:
    from reflex.event import EventType


def status_card(
    message: str,
    count: int,
    on_test: EventType[()],
) -> rx.Component:
    """Render a backend status message, a request counter, and a test button.

    Takes state values and handlers as arguments instead of importing a State,
    so any page can reuse it with its own state.
    """
    return rx.vstack(  # pyright: ignore[reportUnknownMemberType]  # reflex typing is partially Unknown
        rx.text(
            "Backend Status: ",
            size="5",
            as_="span",
        ),
        rx.text(
            message,
            size="5",
            color="var(--accent-9)",
            font_weight="bold",
            as_="span",
        ),
        rx.button(  # pyright: ignore[reportUnknownMemberType]  # reflex typing is partially Unknown
            "Test Backend",
            on_click=on_test,
            size="3",
        ),
        rx.text(
            f"Total requests: {count}",
            size="4",
        ),
        spacing="5",
    )
