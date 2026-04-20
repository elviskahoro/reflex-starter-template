from __future__ import annotations

from datetime import datetime

import reflex as rx


class IndexState(rx.State):
    count: int = 0
    message: str = "Click the button to test the backend"

    async def increment_and_greet(self) -> None:
        """Call backend logic to verify it works."""
        self.count += 1
        self.message = await self._get_greeting()

    async def _get_greeting(self) -> str:
        """Backend function that processes requests and returns status."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"Request #{self.count} processed at {timestamp}"


def page() -> rx.Component:
    # Welcome Page (Index)
    return rx.container(
        rx.color_mode.button(
            position="top-right",
        ),
        rx.vstack(
            rx.heading(
                "Welcome to Reflex!",
                size="9",
            ),
            rx.text(
                "Backend Status: ",
                size="5",
                as_="span",
            ),
            rx.text(
                IndexState.message,
                size="5",
                color="var(--accent-9)",
                font_weight="bold",
                as_="span",
            ),
            rx.button(
                "Test Backend",
                on_click=IndexState.increment_and_greet,
                size="3",
            ),
            rx.text(
                f"Total requests: {IndexState.count}",
                size="4",
            ),
            rx.link(
                rx.button("Check out our docs!"),
                href="https://reflex.dev/docs/getting-started/introduction/",
                is_external=True,
            ),
            spacing="5",
            justify="center",
            min_height="85vh",
        ),
    )
