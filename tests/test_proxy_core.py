"""Proxy logic tests with a fake Modal and a fake upstream Server. No network."""

from __future__ import annotations

import asyncio
import gzip
import http
from typing import TYPE_CHECKING, Any

import httpx
from proxy_core import COOKIE, EXPIRED_BODY, is_expired, make_app, upstream_headers
from starlette.testclient import TestClient

if TYPE_CHECKING:
    from collections.abc import Callable


def _resp(
    status: int, body: bytes | str = b"", headers: dict[str, str] | None = None
) -> httpx.Response:
    """A response that streams its body, like one from the network."""
    data = body.encode() if isinstance(body, str) else body
    return httpx.Response(status, headers=headers, stream=httpx.ByteStream(data))


class FakeSessions:
    """Hands out tokens t1, t2, ... and records how many were started."""

    def __init__(self) -> None:
        """Start with no sessions."""
        self.started = 0

    async def server_url(self) -> str:
        return "https://server.example.test"

    async def start(self) -> str:
        self.started += 1
        return f"t{self.started}"


def _client(
    handler: Callable[[httpx.Request], httpx.Response],
    sessions: FakeSessions | None = None,
    **kwargs: Any,  # noqa: ANN401
) -> tuple[TestClient, FakeSessions]:
    sessions = sessions or FakeSessions()
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TestClient(
        make_app(sessions, client=upstream, **kwargs), base_url="https://proxy.test"
    ), sessions


def test_new_visitor_gets_a_session_and_a_cookie() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _resp(200, "hello")

    client, sessions = _client(handler)
    reply = client.get("/counter")
    assert reply.status_code == http.HTTPStatus.OK
    assert reply.text == "hello"
    assert sessions.started == 1
    assert seen[0].headers["modal-authorization"] == "Bearer t1"
    assert str(seen[0].url) == "https://server.example.test/counter"
    assert COOKIE in reply.headers["set-cookie"]
    assert "HttpOnly" in reply.headers["set-cookie"]


def test_returning_visitor_reuses_their_session() -> None:
    client, sessions = _client(lambda _r: _resp(200, "ok"))
    client.get("/")
    client.get("/counter")
    client.get("/assets/x.js")
    assert sessions.started == 1


def test_expired_session_is_replaced_and_the_request_retried_once() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        token = request.headers["modal-authorization"]
        calls.append(token)
        if token == "Bearer old":  # noqa: S105
            return _resp(http.HTTPStatus.NOT_FOUND, EXPIRED_BODY)
        return _resp(http.HTTPStatus.OK, "fresh")

    client, sessions = _client(handler)
    client.cookies.set(COOKIE, "old")
    reply = client.get("/counter")
    assert reply.status_code == http.HTTPStatus.OK
    assert reply.text == "fresh"
    assert calls == ["Bearer old", "Bearer t1"]
    assert sessions.started == 1
    assert f"{COOKIE}=t1" in reply.headers["set-cookie"]


def test_an_app_404_is_passed_through_not_retried() -> None:
    client, sessions = _client(lambda _r: _resp(404, "<html>not found</html>"))
    reply = client.get("/nope")
    assert reply.status_code == http.HTTPStatus.NOT_FOUND
    assert "not found" in reply.text
    assert sessions.started == 1


def test_gzip_body_and_header_are_kept_together() -> None:
    body = gzip.compress(b"<html>compressed</html>")

    def handler(_request: httpx.Request) -> httpx.Response:
        headers = {"content-encoding": "gzip", "vary": "Accept-Encoding"}
        return _resp(200, body, headers)

    client, _ = _client(handler)
    reply = client.get("/", headers={"accept-encoding": "gzip"})
    assert reply.headers["content-encoding"] == "gzip"
    # The test client decodes it, so the pair is consistent.
    assert reply.content == b"<html>compressed</html>"


def test_post_body_and_query_are_forwarded() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _resp(204)

    client, _ = _client(handler)
    client.post("/_upload?x=1", content=b"payload")
    assert seen[0].content == b"payload"
    assert seen[0].url.query == b"x=1"


def test_our_cookie_never_reaches_the_server_but_others_do() -> None:
    headers = upstream_headers(
        [
            ("host", "proxy.test"),
            ("cookie", f"{COOKIE}=secret; theme=dark"),
            ("accept", "*/*"),
        ],
        "tok",
    )
    names = {n.lower(): v for n, v in headers}
    assert "host" not in names
    assert names["cookie"] == "theme=dark"
    assert names["modal-authorization"] == "Bearer tok"
    only_ours = upstream_headers([("cookie", f"{COOKIE}=secret")], "tok")
    assert "cookie" not in {n.lower() for n, _ in only_ours}


def test_is_expired_matches_only_modals_message() -> None:
    assert is_expired(404, b"Unknown or expired session\n")
    assert not is_expired(404, b"<html>404</html>")
    assert not is_expired(200, EXPIRED_BODY)


class FakeUpstreamSocket:
    """Echoes whatever it is sent, upper-cased, then ends when closed."""

    def __init__(self, subprotocol: str | None = None) -> None:
        """Start open, with an empty queue and an optional subprotocol."""
        self.subprotocol = subprotocol
        self.queue: asyncio.Queue[Any] = asyncio.Queue()
        self.closed = False

    async def send(self, message: str | bytes) -> None:
        upper = message.upper() if isinstance(message, str) else message
        await self.queue.put(upper)

    async def close(self) -> None:
        self.closed = True
        await self.queue.put(None)

    def __aiter__(self) -> FakeUpstreamSocket:
        """Iterate over the echoed messages."""
        return self

    async def __anext__(self) -> str | bytes:
        """Return the next echoed message until closed."""
        item = await self.queue.get()
        if item is None:
            raise StopAsyncIteration
        return item


def test_websocket_is_relayed_with_the_session_token() -> None:
    opened: list[tuple[str, list[tuple[str, str]]]] = []

    async def connect(
        url: str, additional_headers: list[tuple[str, str]], **_: object
    ) -> FakeUpstreamSocket:
        opened.append((url, additional_headers))
        return FakeUpstreamSocket()

    sessions = FakeSessions()
    app = make_app(sessions, connect_ws=connect)
    with TestClient(app, base_url="https://proxy.test").websocket_connect(
        "/_event/?EIO=4&transport=websocket"
    ) as ws:
        ws.send_text("hello")
        assert ws.receive_text() == "HELLO"
    assert opened[0][0] == "wss://server.example.test/_event/?EIO=4&transport=websocket"
    assert ("Modal-Authorization", "Bearer t1") in opened[0][1]
    assert sessions.started == 1


def test_websocket_retries_once_when_the_session_has_expired() -> None:
    class ExpiredError(Exception):
        response = type("R", (), {"status_code": http.HTTPStatus.NOT_FOUND})()

    attempts: list[str] = []

    async def connect(
        _url: str, additional_headers: list[tuple[str, str]], **_: object
    ) -> FakeUpstreamSocket:
        token = dict(additional_headers)["Modal-Authorization"]
        attempts.append(token)
        if token == "Bearer old":  # noqa: S105
            raise ExpiredError
        return FakeUpstreamSocket()

    sessions = FakeSessions()
    client = TestClient(
        make_app(sessions, connect_ws=connect), base_url="https://proxy.test"
    )
    client.cookies.set(COOKIE, "old")
    with client.websocket_connect("/_event/") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "PING"
    assert attempts == ["Bearer old", "Bearer t1"]


def test_websocket_subprotocol_is_negotiated_through_the_proxy() -> None:
    """A browser rejects a requested subprotocol unless it is echoed back."""
    asked: list[object] = []

    async def connect(
        _url: str,
        _additional_headers: list[tuple[str, str]] | None = None,
        subprotocols: list[str] | None = None,
        **_: object,
    ) -> FakeUpstreamSocket:
        asked.append(subprotocols)
        return FakeUpstreamSocket(subprotocol=(subprotocols or [None])[0])

    app = make_app(FakeSessions(), connect_ws=connect)
    client = TestClient(app, base_url="https://proxy.test")
    with client.websocket_connect(
        "/_event/", subprotocols=["reflex-v1", "other"]
    ) as ws:
        assert ws.accepted_subprotocol == "reflex-v1"
        ws.send_text("hi")
        assert ws.receive_text() == "HI"
    assert asked == [["reflex-v1", "other"]]
