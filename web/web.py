"""Reflex app entrypoint."""

from __future__ import annotations

import reflex as rx

from web.pages.index import page

app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Oxanium:wght@200..800&display=swap",
        "/globals.css",
    ],
)
app.add_page(  # pyright: ignore[reportUnknownMemberType]  # reflex typing is partially Unknown
    component=page,
    route="/",
    title="Elvis Kahoro's Reflex Starter Template",
    description=(
        "A Reflex starter that documents and enforces its conventions, "
        "so AI agents can extend it correctly on the first try."
    ),
    image="favicon",
    on_load=None,
    meta=[{"author": "elvis kahoro"}],
)
