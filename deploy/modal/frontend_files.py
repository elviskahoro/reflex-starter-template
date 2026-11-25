"""STATUS: CURRENT, shared by variants 3 and 4 (page server used by server_entry.py).

The older variants (modal_app.py, modal_app_asgi.py) are superseded and stopped.
Put new work here.

Serve the exported Reflex frontend behind Modal's proxy, with deploy-safe caching.

Reflex's own ``PrecompressedStaticFiles`` (gzip sidecars, SPA routing) does the
serving. Two things need fixing on Modal, and the first was found by the Vercel
version of this project (``../reflex-vercel/frontend_files.py``):

- **Stale HTML after a redeploy.** Starlette builds an ETag from file size and
  modification time. A Reflex export has constant modification times, and a new
  build renames hashed assets to names of the same length, so ``index.html`` can
  keep its ETag while its content changes. A returning browser then gets
  "304 Not Modified", keeps the old page, and 404s on assets the new deployment
  no longer has. So HTML is never answered "not modified" and is sent
  ``Cache-Control: no-cache``, and files under ``/assets/`` (content-hashed
  names) are ``immutable`` for a year.
- **Broken redirect for pages without a trailing slash.** Reflex exports
  ``/counter`` as ``counter/index.html``. Starlette answers ``/counter`` with a
  redirect to ``/counter/`` built from the request's Host header, and behind a
  Modal Server that header is the container's internal address, so the browser
  is sent somewhere unreachable. This class serves ``/counter`` directly as
  ``/counter/`` instead of redirecting.
"""

from __future__ import annotations

import http
import os
from pathlib import Path
from typing import TYPE_CHECKING

from reflex.utils.precompressed_staticfiles import PrecompressedStaticFiles
from typing_extensions import override

if TYPE_CHECKING:
    from starlette.datastructures import Headers
    from starlette.responses import Response
    from starlette.types import Receive, Scope, Send

HTML_CACHE_CONTROL = "no-cache"
ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"


class FrontendFiles(PrecompressedStaticFiles):
    """``PrecompressedStaticFiles`` with safe caching and no internal redirects."""

    @override
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Serve ``/page`` as ``/page/`` when a folder with an index file exists."""
        if scope["type"] == "http" and self.directory is not None:
            path: str = scope.get("path", "")
            last = path.rsplit("/", 1)[-1]
            if path and not path.endswith("/") and "." not in last:
                relative = path.lstrip("/")
                if (Path(self.directory) / relative / "index.html").is_file():
                    scope = {**scope, "path": path + "/"}
                    if "raw_path" in scope:
                        scope["raw_path"] = scope["raw_path"] + b"/"
        await super().__call__(scope, receive, send)

    @override
    def is_not_modified(
        self, response_headers: Headers, request_headers: Headers
    ) -> bool:
        """Never revalidate HTML: its ETag does not change when the build does."""
        if response_headers.get("content-type", "").startswith("text/html"):
            return False
        return super().is_not_modified(response_headers, request_headers)

    @override
    def file_response(
        self,
        full_path: str | os.PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = http.HTTPStatus.OK,
    ) -> Response:
        """Build the response, then set the cache policy for HTML and hashed assets."""
        response = super().file_response(full_path, stat_result, scope, status_code)
        path = Path(os.fspath(full_path))
        if path.suffix.lower() == ".html":
            response.headers["Cache-Control"] = HTML_CACHE_CONTROL
        elif status_code == http.HTTPStatus.OK and "assets" in path.parts:
            response.headers["Cache-Control"] = ASSET_CACHE_CONTROL
        return response
