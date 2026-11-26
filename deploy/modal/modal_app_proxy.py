"""STATUS: CURRENT (the NEWEST variant; see NOTES.md to choose a variant).

It is about 3x slower per request than modal_app_server.py in our load test, but
visitors never see the Server address or an expired-session 404.

Reflex on a sessioned Modal Server behind a reverse proxy.

Variant 3 (modal_app_server.py) redirects visitors to the Server's own
`*.modal.direct` address. That address shows in the browser, and once a session
expires, Modal's proxy answers it with a plain `404 Unknown or expired session`
that we cannot customize. This variant keeps visitors on the proxy's address: a
Modal Function receives every request, adds the session token itself, and starts
a fresh session if the Server says the old one is gone (see proxy_core.py).
Visitor state survives that, because it is stored in a Modal Dict keyed by
Reflex's own client token.

The proxy is a normal `asgi_app`, so it can sit on a custom domain (Team or
Enterprise plan):

    modal deploy modal_app_proxy.py
    REFLEX_CUSTOM_DOMAINS=app.example.com modal deploy modal_app_proxy.py

Trade-off versus variant 3: every request takes an extra hop through a Function,
and each open websocket uses one Function call. Variant 3 is the faster path.
Measure before choosing.

The image below repeats modal_app_server.py's on purpose: Modal does not mount
sibling modules automatically, so sharing it would risk breaking the deployed
variant 3. Keep the two in step.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import modal

if TYPE_CHECKING:
    from starlette.types import ASGIApp

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
# Keep the image small: no virtualenv, build output, VCS data, agent folders
# or deploy files.
APP_IGNORE = [
    "**/.venv",
    "**/.web",
    "**/__pycache__",
    "**/*.pyc",
    "**/.git",
    ".agents",
    ".claude",
    ".context",
    ".trunk",
    ".rwx",
    "deploy",
    "tests",
    "scripts",
    "ci",
]

APP_NAME = "reflex-starter-proxy"

# A session ends this many seconds after its last request. An open websocket
# counts as a request in flight. If it ends anyway, the proxy starts a new one,
# so the visitor does not notice.
SESSION_IDLE_SECONDS = 120

# Cost guardrails: the proxy is public and each session can start a container,
# so cap both.
MAX_SERVER_CONTAINERS = 3
MAX_PROXY_CONTAINERS = 3

# Optional custom domains, comma separated. The domain must already be added in
# Modal's workspace settings (Team or Enterprise plan) with its DNS record in
# place.
CUSTOM_DOMAINS = [
    d.strip()
    for d in os.environ.get("REFLEX_CUSTOM_DOMAINS", "").split(",")
    if d.strip()
]

app = modal.App(APP_NAME)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("curl", "unzip")
    .pip_install("uv")
    .add_local_dir(
        str(REPO_ROOT),
        remote_path="/app",
        copy=True,
        ignore=APP_IGNORE,
    )
    .run_commands(
        "cd /app && uv export --frozen --no-dev --no-hashes --no-emit-project"
        " -o /tmp/req.txt && uv pip install --system -r /tmp/req.txt",
        "cd /app && reflex init && reflex export --frontend-only",
        "mkdir -p /srv && unzip -q /app/frontend.zip -d /srv && rm /app/frontend.zip",
        "mkdir -p /app/.web/backend",
    )
    .add_local_file(str(HERE / "server_entry.py"), "/app/server_entry.py", copy=True)
    .add_local_file(str(HERE / "modal_state.py"), "/app/modal_state.py", copy=True)
    .add_local_file(
        str(HERE / "frontend_files.py"), "/app/frontend_files.py", copy=True,
    )
    .env(
        {
            "REFLEX_ENV": "prod",
            "PYTHONUNBUFFERED": "1",
            # Visitor state lives in this Modal Dict (see modal_state.py).
            # Shared with variant 3.
            "REFLEX_STATE_DICT": "reflex-state",
            "REFLEX_STATE_DEBUG": "1",
        },
    )
)


@app.server(
    image=image,
    port=8000,
    cpu=(1.0, 4.0),
    startup_timeout=180,
    scaledown_window=60,
    exit_grace_period=30,
    max_containers=MAX_SERVER_CONTAINERS,
)
@modal.sessioned()
class ReflexServer:
    """The sessioned Server that runs Reflex under Granian."""

    @modal.enter()
    def startup(self) -> None:
        """Start Granian when the container starts."""
        # One worker on purpose: Reflex keeps per-visitor state in process memory
        # and only supports several workers with Redis.
        subprocess.Popen(  # nosec B607 - granian is on PATH in the image
            [
                "granian",
                "--interface",
                "asgi",
                "--factory",
                "server_entry:create_app",
                "--host",
                "0.0.0.0",  # nosec B104 - must listen on all interfaces in the container
                "--port",
                "8000",
                "--workers",
                "1",
                "--ws",
            ],
            cwd="/app",
        )


proxy_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("starlette", "httpx", "websockets")
    .add_local_file(str(HERE / "proxy_core.py"), "/root/proxy_core.py")
)


@app.function(image=proxy_image, max_containers=MAX_PROXY_CONTAINERS, timeout=60 * 60)
@modal.concurrent(max_inputs=100)
@modal.asgi_app(custom_domains=CUSTOM_DOMAINS or None)
def proxy() -> ASGIApp:
    """Public entry point: hand every request and websocket to the Server."""
    from proxy_core import make_app

    class ModalSessions:
        """Start and find sessions on the Modal Server."""

        def __init__(self) -> None:
            """Look up the Server by name."""
            self._server = modal.Server.from_name(APP_NAME, "ReflexServer")
            self._url: str | None = None

        async def server_url(self) -> str:
            """Return the Server's address, fetched once."""
            if self._url is None:
                self._url = await self._server.get_url.aio()
            return self._url

        async def start(self) -> str:
            """Start a new session and return its token."""
            creds = await self._server.sessions.start.aio(
                idle_timeout=SESSION_IDLE_SECONDS,
            )
            return creds.token

    return make_app(ModalSessions(), cookie_max_age=24 * 60 * 60)
