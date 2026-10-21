"""Index page."""

from __future__ import annotations

from datetime import datetime

import reflex as rx

from web.components.status_card import status_card


class IndexState(rx.State):
    """State for the index page."""

    count: int = 0
    message: str = "Click the button to test the backend"

    @rx.event
    async def increment_and_greet(self) -> None:
        """Call backend logic to verify it works."""
        self.count += 1
        self.message = await self._get_greeting()

    async def _get_greeting(self) -> str:
        """Backend function that processes requests and returns status."""
        timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
        return f"Request #{self.count} processed at {timestamp}"


def page() -> rx.Component:
    """Render the welcome page."""
    # Welcome Page (Index)
    return rx.container(  # pyright: ignore[reportUnknownMemberType]  # reflex typing is partially Unknown
        rx.color_mode.button(  # pyright: ignore[reportUnknownMemberType]  # reflex typing is partially Unknown
            position="top-right",
        ),
        rx.vstack(  # pyright: ignore[reportUnknownMemberType]  # reflex typing is partially Unknown
            rx.heading(  # pyright: ignore[reportUnknownMemberType]  # reflex typing is partially Unknown
                "Welcome to Reflex!",
                size="9",
            ),
            status_card(
                message=IndexState.message,
                count=IndexState.count,
                on_test=IndexState.increment_and_greet,
            ),
            rx.link(  # pyright: ignore[reportUnknownMemberType]  # reflex typing is partially Unknown
                rx.button("Check out our docs!"),  # pyright: ignore[reportUnknownMemberType]  # reflex typing is partially Unknown
                href="https://reflex.dev/docs/getting-started/introduction/",
                is_external=True,
            ),
            spacing="5",
            justify="center",
            min_height="85vh",
        ),
    )
