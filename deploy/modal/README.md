# Deploying to Modal

Two ways to run this app on [Modal](https://modal.com), next to the Railway setup
(`Dockerfile`, `DEPLOYMENT.md`). Each deploys as its own Modal app and scales to zero.
Both run Reflex under Granian with one worker, and keep visitor state in a Modal Dict
(`REFLEX_STATE_DICT`, default `reflex-state`) so it survives a container replacement.

Install the client once: `uv tool install "modal[api-proxy-support]"`, then `modal token new`.
The Modal client is not an app dependency; do not add it to `pyproject.toml`.

```bash
cd deploy/modal
modal deploy modal_app_server.py   # variant 3: server + front door
modal deploy modal_app_proxy.py    # variant 4: server + proxy
```

## Choosing a variant

| Question | Variant 3 (`modal_app_server.py`) | Variant 4 (`modal_app_proxy.py`) |
| --- | --- | --- |
| Visitors reopen old tabs or bookmarks after a couple of minutes? | No, or always via one shared link | **Yes** |
| Own domain, or one stable address in the browser? | No | **Yes** (proxy is an `asgi_app`; untested with a real domain) |
| Raw speed, or mostly static pages? | **Yes** (~0.21 s median per request) | No (~0.6 s) |
| Many visitors holding live websockets? | **Yes** | Careful: each websocket holds one proxy call, ~100 per container, 3 containers |
| Internal tool or demo you hand out yourself? | **Yes** | Works, slower for little gain |
| Public site for people you do not control? | Only if the front door link is the only one shared | **Yes** |

- Public-facing and unsure: variant 4. Internal, demo, or latency-sensitive: variant 3.
- Variant 3: share the front door (`*.modal.run`), not the Server (`*.modal.direct`).
  An expired session shows a plain Modal `404 Unknown or expired session`.
  Variant 4: share the proxy address; it starts a new session and retries once.
- Both read and write the same Dict, so a visitor's state follows them between variants.
- No per-visitor state needed: either works; prefer variant 3 and drop `REFLEX_STATE_DICT`.
- Two apps in one workspace must set different `REFLEX_STATE_DICT` names, or they share state.

## Constraints

- One Granian worker (more needs Redis). Each Server, front door and proxy is capped at 3
  containers; sessions end after 120 s idle. Both variants are public with no login.
- `server_entry.py` assigns Reflex's private `_state_manager` (no public hook). Re-check
  after a Reflex upgrade; `tests/test_modal_state.py` should catch a break.
- A Dict value is limited to 100 MiB (Modal recommends < 5 MiB), entries expire after
  7 days idle, and concurrent saves of one visitor are last-writer-wins.
- Cold starts measured at ~10 s (variant 3) and ~18 s (variant 4), mostly Modal.
- `modal_app_proxy.py` repeats `modal_app_server.py`'s image on purpose (Modal does not
  mount sibling modules); change both together.
- The images are built from the repo root and its `uv.lock`; the export lands in `/srv`,
  the app in `/app`.
- Not verified: custom domain, memory snapshots with Granian, many simultaneous
  websockets on the proxy, real-device browsers.

## Sandbox and agent notes

1. Plain `modal` fails with a `python-socks` ImportError behind an HTTP proxy; use the
   `api-proxy-support` extra.
2. Allow-list `api.modal.com`, `modal.com`, then each deployed host exactly
   (`*.modal.run`, `*.modal.direct`), or checks return `000` or a proxy 403.
3. Non-interactive login: `script -qc "modal token new --no-verify" /tmp/modal-login.log </dev/null >/dev/null 2>&1 &`,
   read the `https://modal.com/token-flow/...` link from the log, hand it to the account
   owner, confirm with `modal profile current`. Never print or commit `~/.modal.toml`.
4. `modal app stop <app> --yes` needs `--yes` when non-interactive. "No changes detected"
   on redeploy is normal; old containers can answer for a few minutes after a deploy.
5. Verify in a real browser, not only `curl`: open the app, wait ~7 s for the websocket,
   change some state, replace the Server container, reload, expect the state back. For
   variant 4, also let the 120 s session expire and return on the same address.
   Playwright's Chromium needs `proxy: { server: process.env.HTTPS_PROXY }` in a sandbox.

## Tests

`uv run pytest -q` runs `tests/test_modal_state.py`, `tests/test_frontend_files.py` and
`tests/test_proxy_core.py` (pytest's `pythonpath` includes this folder).
