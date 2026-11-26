"""FrontendFiles: serve slashless pages and keep HTML fresh across redeploys."""

from __future__ import annotations

import asyncio
import http
from typing import TYPE_CHECKING

from frontend_files import ASSET_CACHE_CONTROL, HTML_CACHE_CONTROL, FrontendFiles

if TYPE_CHECKING:
    from pathlib import Path


def _site(root: Path) -> None:
    (root / "assets").mkdir()
    (root / "counter").mkdir()
    (root / "index.html").write_text("<html>home</html>")
    (root / "404.html").write_text("<html>not found</html>")
    (root / "counter" / "index.html").write_text("<html>counter</html>")
    (root / "assets" / "app-abc123.js").write_text("console.log(1)")


async def _get(
    app: FrontendFiles,
    path: str,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    sent: list[dict] = []
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers or [],
        "server": ("172.20.0.9", 8000),
        "scheme": "http",
        "root_path": "",
    }

    first = True

    async def receive() -> dict:
        # One request body, then wait like a real client that stays connected.
        nonlocal first
        if first:
            first = False
            return {"type": "http.request", "body": b"", "more_body": False}
        await asyncio.Event().wait()
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        sent.append(message)

    await app(scope, receive, send)
    start = next(m for m in sent if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in sent if m["type"] == "http.response.body"
    )
    return (
        start["status"],
        {k.decode().lower(): v.decode() for k, v in start["headers"]},
        body,
    )


def test_page_without_trailing_slash_is_served_not_redirected(tmp_path: Path) -> None:
    _site(tmp_path)
    app = FrontendFiles(directory=tmp_path, html=True)
    status, headers, body = asyncio.run(_get(app, "/counter"))
    assert status == http.HTTPStatus.OK
    assert b"counter" in body
    assert "location" not in headers


def test_html_is_never_not_modified(tmp_path: Path) -> None:
    _site(tmp_path)
    app = FrontendFiles(directory=tmp_path, html=True)
    _, first, _ = asyncio.run(_get(app, "/"))
    assert first["cache-control"] == HTML_CACHE_CONTROL
    status, _, _ = asyncio.run(
        _get(app, "/", [(b"if-none-match", first["etag"].encode())]),
    )
    assert status == http.HTTPStatus.OK


def test_hashed_assets_are_immutable(tmp_path: Path) -> None:
    _site(tmp_path)
    app = FrontendFiles(directory=tmp_path, html=True)
    status, headers, _ = asyncio.run(_get(app, "/assets/app-abc123.js"))
    assert status == http.HTTPStatus.OK
    assert headers["cache-control"] == ASSET_CACHE_CONTROL


def test_missing_page_is_404(tmp_path: Path) -> None:
    _site(tmp_path)
    app = FrontendFiles(directory=tmp_path, html=True)
    status, _, _ = asyncio.run(_get(app, "/nope"))
    assert status == http.HTTPStatus.NOT_FOUND
