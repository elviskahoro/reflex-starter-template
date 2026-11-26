"""STATUS: CURRENT (the FASTEST variant; see NOTES.md to choose a variant).

Variant 4, modal_app_proxy.py, is the newest and trades speed for a nicer expiry
experience. modal_app.py and modal_app_asgi.py are superseded.

Reflex on a Modal Server with Sticky Sessions, run by Granian.

- @app.server: Modal's low-latency HTTP/websocket primitive (no Function input
  queue).
- @modal.sessioned: every visitor gets a session pinned to one container, so
  Reflex's in-memory state and websocket reconnects stay on the same process.
- Granian (Reflex's own production server, written in Rust) serves the app.
- A small "front door" web function starts a session for each visitor and
  redirects them to the Server with the session token.

    modal deploy modal_app_server.py
    # visit the front door URL that deploy prints (not the Server URL)
"""

from __future__ import annotations

import http
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import modal

if TYPE_CHECKING:
    from starlette.requests import Request
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

APP_NAME = "reflex-starter-server"

# A session ends this many seconds after its last request. An open websocket
# counts as a request in flight, so a visitor looking at the page keeps their
# session. A short value lets idle containers shut down sooner (a container
# stays up while any session on it is active).
SESSION_IDLE_SECONDS = 120

# Cost guardrails: the front door is public and each session can start a
# container, so cap both. Raise these deliberately if real traffic needs it.
MAX_SERVER_CONTAINERS = 3
MAX_DOOR_CONTAINERS = 3

SESSION_COOKIE = "rx_door_session"

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
            # Visitor state is kept in this Modal Dict (see modal_state.py).
            # Unset to use memory.
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


door_image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "starlette", "httpx",
)


@app.function(image=door_image, max_containers=MAX_DOOR_CONTAINERS)
@modal.concurrent(max_inputs=50)
@modal.asgi_app()
def front_door() -> ASGIApp:
    """Public entry point: reuse the visitor's live session, or start one.

    The visitor is then redirected to the Server. The session token is kept in a
    cookie on the front door's own host, so a refresh or a return visit does not
    start another session. The token is checked against the Server first,
    because sessions expire on their own.
    """
    import httpx
    from starlette.applications import Starlette
    from starlette.responses import RedirectResponse
    from starlette.routing import Route

    async def session_is_alive(server_url: str, token: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                reply = await client.get(
                    f"{server_url.rstrip('/')}/ping",
                    headers={"Modal-Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError:
            return False
        return reply.status_code == http.HTTPStatus.OK

    async def enter(request: Request) -> RedirectResponse:
        """Redirect the visitor to the Server with a live session token."""
        server = modal.Server.from_name(APP_NAME, "ReflexServer")
        url = (await server.get_url.aio()).rstrip("/")
        token = request.cookies.get(SESSION_COOKIE)
        if token and not await session_is_alive(url, token):
            token = None
        if not token:
            creds = await server.sessions.start.aio(idle_timeout=SESSION_IDLE_SECONDS)
            token = creds.token
        response = RedirectResponse(
            f"{url}{request.url.path}?modal_session_token={token}", status_code=307,
        )
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=SESSION_IDLE_SECONDS,
            httponly=True,
            secure=True,
            samesite="lax",
        )
        return response

    return Starlette(routes=[Route("/{path:path}", enter), Route("/", enter)])
