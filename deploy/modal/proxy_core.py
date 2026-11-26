"""STATUS: CURRENT (variant 4, the proxy; used by modal_app_proxy.py).

Reverse proxy that fronts a sessioned Modal Server.

Why this exists. In variant 3 the front door redirects visitors to the Server's
own address (`*.modal.direct`), so the browser's address bar shows that address.
Sessions expire on their own, and a bookmark or old tab of the Server address
then gets a plain `404 Unknown or expired session` from Modal's proxy that we
cannot customize. Here the visitor only ever sees this proxy's address. The
proxy keeps the Modal session token in its own cookie, adds it to every request
it forwards, and when the Server says the session is gone it starts a new one
and retries once, so a visitor never sees the expiry. Visitor state survives the
move to a new session because it lives in a Modal Dict (see modal_state.py),
keyed by Reflex's own client token, not by session.

Trade-off. Every request now passes through a Modal Function before it reaches
the Server, which adds a hop and uses Function concurrency (each websocket holds
one call). Measure before relying on it. Pure logic lives here so it can be
tested without Modal; modal_app_proxy.py wires it up.
"""

from __future__ import annotations

import asyncio
import contextlib
import http
import logging
from typing import TYPE_CHECKING, Any, Protocol

import httpx
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request

logger = logging.getLogger(__name__)

COOKIE = "rx_proxy_session"
# What Modal's own proxy answers when a session token is unknown or expired.
EXPIRED_BODY = b"Unknown or expired session"
# Headers that describe one hop, not the message. They are never copied across
# the proxy.
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
    "host",
}
ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


class Sessions(Protocol):
    """What the proxy needs from Modal. A fake stands in for tests."""

    async def server_url(self) -> str:
        """The Server's address, for example ``https://x--y.us-east.modal.direct``."""
        ...

    async def start(self) -> str:
        """Start a new sticky session and return its token."""
        ...


def is_expired(status_code: int, body: bytes) -> bool:
    """Say whether Modal's proxy rejected the session token.

    In that case the request never ran.
    """
    return status_code == http.HTTPStatus.NOT_FOUND and body.strip() == EXPIRED_BODY


def upstream_headers(items: list[tuple[str, str]], token: str) -> list[tuple[str, str]]:
    """Build the request headers to send upstream.

    Drop hop-by-hop headers and our own cookie, and add the token.
    """
    out: list[tuple[str, str]] = []
    for name, value in items:
        lower = name.lower()
        if lower in HOP_BY_HOP:
            continue
        if lower == "cookie":
            kept = [
                part.strip()
                for part in value.split(";")
                if part.strip() and not part.strip().startswith(f"{COOKIE}=")
            ]
            if not kept:
                continue
            out.append((name, "; ".join(kept)))
            continue
        out.append((name, value))
    out.append(("Modal-Authorization", f"Bearer {token}"))
    return out


def downstream_headers(items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Response headers to send to the browser: drop hop-by-hop headers."""
    return [(n, v) for n, v in items if n.lower() not in HOP_BY_HOP]


async def _read_raw(reply: httpx.Response) -> bytes:
    """Return the response body exactly as sent.

    It is still gzipped if it was, so Content-Encoding stays true.
    """
    return b"".join([chunk async for chunk in reply.aiter_raw()])


def _set_cookie(response: Response, token: str, max_age: int) -> None:
    """Store the session token in the proxy's own cookie."""
    response.set_cookie(
        COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        secure=True,
        samesite="lax",
    )


def make_app(
    sessions: Sessions,
    *,
    cookie_max_age: int = 3600,
    client: httpx.AsyncClient | None = None,
    connect_ws: Callable[..., Awaitable[Any]] | None = None,
) -> Starlette:
    """Build the proxy as a Starlette app.

    ``client`` and ``connect_ws`` can be replaced in tests; by default an
    ``httpx`` client and the ``websockets`` library are used.
    """
    state: dict[str, httpx.AsyncClient] = {}

    def http_client() -> httpx.AsyncClient:
        """Return the injected client, or a shared default one."""
        if client is not None:
            return client
        if "client" not in state:
            state["client"] = httpx.AsyncClient(timeout=60, follow_redirects=False)
        return state["client"]

    async def forward(request: Request) -> Response:
        """Forward one HTTP request, retrying once if the session expired."""
        base = (await sessions.server_url()).rstrip("/")
        url = f"{base}{request.url.path}"
        if request.url.query:
            url += f"?{request.url.query}"
        body = await request.body()
        token = request.cookies.get(COOKIE)
        minted = False
        for attempt in range(2):
            if not token:
                token = await sessions.start()
                minted = True
            headers = upstream_headers(list(request.headers.items()), token)
            upstream = http_client().build_request(
                request.method,
                url,
                headers=headers,
                content=body,
            )
            reply = await http_client().send(upstream, stream=True)
            raw = await _read_raw(reply)
            await reply.aclose()
            if attempt == 0 and is_expired(reply.status_code, raw):
                # The request never ran, so it is safe to retry on a new session.
                token = None
                continue
            break
        response = Response(content=raw, status_code=reply.status_code)
        for name, value in downstream_headers(list(reply.headers.multi_items())):
            response.headers.append(name, value)
        if minted or request.cookies.get(COOKIE) != token:
            _set_cookie(response, token, cookie_max_age)
        return response

    async def relay(websocket: WebSocket) -> None:
        """Relay one websocket to the Server, retrying once if it expired."""
        connect = connect_ws
        if connect is None:
            from websockets.asyncio.client import connect as ws_connect

            connect = ws_connect
        base = (await sessions.server_url()).rstrip("/")
        url = base.replace("https://", "wss://", 1).replace("http://", "ws://", 1)
        url += websocket.url.path
        if websocket.url.query:
            url += f"?{websocket.url.query}"
        # A browser that asks for a subprotocol drops the connection unless the
        # answer names one. Pass the request on, and echo whatever the Server
        # chose.
        subprotocols = list(websocket.scope.get("subprotocols") or [])
        token = websocket.cookies.get(COOKIE)
        minted = False
        upstream = None
        for attempt in range(2):
            if not token:
                token = await sessions.start()
                minted = True
            try:
                upstream = await connect(
                    url,
                    additional_headers=[("Modal-Authorization", f"Bearer {token}")],
                    subprotocols=subprotocols or None,
                    open_timeout=30,
                    max_size=None,
                )
                break
            except Exception as error:  # noqa: BLE001
                response = getattr(error, "response", None)
                status = getattr(response, "status_code", None)
                if attempt == 0 and status == http.HTTPStatus.NOT_FOUND:
                    # Expired session: start a new one and try once more.
                    token = None
                    continue
                logger.warning("Could not open the upstream websocket: %r", error)
                await websocket.close(code=1011)
                return
        if upstream is None:  # pragma: no cover - the loop always sets it or returns
            return
        accept_headers: list[tuple[bytes, bytes]] = []
        if minted or websocket.cookies.get(COOKIE) != token:
            cookie = Response()
            _set_cookie(cookie, token, cookie_max_age)
            accept_headers = [(b"set-cookie", cookie.headers["set-cookie"].encode())]
        await websocket.accept(
            subprotocol=getattr(upstream, "subprotocol", None),
            headers=accept_headers,
        )

        async def client_to_server() -> None:
            """Copy browser messages to the Server."""
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    return
                if message.get("text") is not None:
                    await upstream.send(message["text"])
                elif message.get("bytes") is not None:
                    await upstream.send(message["bytes"])

        async def server_to_client() -> None:
            """Copy Server messages to the browser."""
            async for message in upstream:
                if isinstance(message, str):
                    await websocket.send_text(message)
                else:
                    await websocket.send_bytes(message)

        tasks = [
            asyncio.create_task(client_to_server()),
            asyncio.create_task(server_to_client()),
        ]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in tasks:
                task.cancel()
            await upstream.close()
            with contextlib.suppress(RuntimeError, WebSocketDisconnect):
                await websocket.close()

    return Starlette(
        routes=[
            WebSocketRoute("/{path:path}", relay),
            Route("/{path:path}", forward, methods=ALL_METHODS),
            Route("/", forward, methods=ALL_METHODS),
        ],
    )
