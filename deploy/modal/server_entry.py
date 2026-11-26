"""STATUS: CURRENT, shared by variants 3 and 4 (entrypoint run by Granian).

It runs inside the Server of modal_app_server.py. The older variants
(modal_app.py, modal_app_asgi.py) are superseded and stopped. Put new work here.

ASGI entrypoint that Granian runs inside the Modal Server container.

Reflex routes (websocket, uploads, ping) go to Reflex. Everything else is served
from the exported frontend, using Reflex's own precompressed static file server.

Granian loads this with:  granian --interface asgi --factory server_entry:create_app
"""

from __future__ import annotations

import os
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

_T0 = time.time()


def _log(msg: str) -> None:
    """Print a message with the time since import."""
    print(f"[timing] +{time.time() - _T0:5.2f}s {msg}", flush=True)


BACKEND_PREFIXES = ("/_event", "/_upload", "/ping", "/_health")


def create_app() -> ASGIApp:
    """Build the ASGI app: Reflex for backend routes, static files otherwise."""
    _log("create_app start")
    os.chdir("/app")
    sys.path.insert(0, "/app")

    from frontend_files import FrontendFiles

    from web.web import app as reflex_app

    _log("imported reflex and web.web")
    from modal_state import StateManagerModalDict, state_kv_from_env

    if (store := state_kv_from_env()) is not None:
        # Visitor state lives in a Modal Dict, so it outlives this container. Writes go
        # through (debounce 0) so a container being replaced loses nothing.
        manager = StateManagerModalDict(
            store=store,
            _write_debounce_seconds=float(
                os.environ.get("REFLEX_STATE_DEBOUNCE_SECONDS", "0"),
            ),
            debug=bool(os.environ.get("REFLEX_STATE_DEBUG")),
        )
        reflex_app._state_manager = manager  # pyright: ignore[reportPrivateUsage]
        _log("state manager: Modal Dict")
    reflex = reflex_app()
    _log("reflex app() compiled")
    static = FrontendFiles(directory="/srv", html=True, encodings=["gzip"])

    async def dispatch(scope: Scope, receive: Receive, send: Send) -> None:
        """Send backend paths to Reflex and everything else to static files."""
        path = scope.get("path", "")
        if scope["type"] in ("lifespan", "websocket") or path.startswith(
            BACKEND_PREFIXES,
        ):
            await reflex(scope, receive, send)
        else:
            await static(scope, receive, send)

    _log("create_app done")
    return dispatch
