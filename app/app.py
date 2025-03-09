from __future__ import annotations

import reflex as rx

from app.pages.index import page

app = rx.App()
app.add_page(
    component=page,
    route="/",
    title="Title",
    description="Description",
    image="favicon",
    on_load=None,
    meta=[
        {
            "author": "elvis kahoro",
        },
    ],
)
