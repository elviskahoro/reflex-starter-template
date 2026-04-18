from __future__ import annotations

import reflex as rx

from web.pages.index import page


async def ping_handler(request):
    return rx.response.Response(content="pong", status_code=200)


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

app.add_route("/ping", ping_handler, methods=["GET"])
