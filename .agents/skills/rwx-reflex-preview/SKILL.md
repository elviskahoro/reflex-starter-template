---
name: rwx-reflex-preview
description: Set up, run, debug, and access RWX preview apps (.rwx/preview.yml) for this Reflex starter. Use when working on PR previews, `rwx run`, rwx.run URLs, or preview auth.
---

# RWX preview apps for Reflex

Config lives in `.rwx/preview.yml`. Docs: https://www.rwx.com/docs/apps and
https://www.rwx.com/blog/preview-your-web-apps-with-rwx. Stick to the docs and
`rwx <cmd> --help`; don't guess at syntax.

## Layout

Tasks: `code` (git/clone) -> `system-deps` (caddy, uv) -> `build`
(`uv sync`, `reflex export --frontend-only`, unzip to `/srv`) -> `preview`
(`app:` task, port 3000, runs backend on :8000 + Caddy via the repo Caddyfile)
-> `share-link` (prints `tasks.preview.app.url`).

## Commands

- Validate: `rwx lint .rwx/preview.yml` (also flags outdated package versions)
- Test: `rwx run .rwx/preview.yml --init pull-request-number=0 --wait`
  (a local run has no PR number, so `init.pull-request-number` must be passed)
- Logs: `rwx logs <run-id> --task <key> --output <dir>`; app URL is in the
  `share-link` task log.
- `rwx apps enable|disable <endpoint-or-url>`; `rwx runs list|show`.

## Gotchas learned

- `entrypoint.sh` hardcodes `/app/Caddyfile`; on RWX run the backend and
  `caddy run --config Caddyfile` directly with `PORT=3000`.
- Apps are private by default. Per the docs: set `app.public: true`, use
  `rwx apps share`, or send `X-RWX-Access-Token: $RWX_ACCESS_TOKEN`
  (needs `run:read`). Unauthenticated requests get a 302 to cloud.rwx.com.
- The exported frontend bakes in `http://localhost:8000` (see
  `assets/reflex-env-*.js`), so events fail ("Connection Error") on a preview.
  The current `build` task rewrites that file to use `location.origin`. This is
  NOT documented by RWX or Reflex and an event/WebSocket round trip is still
  unverified; prefer a documented fix (`api_url` / `REFLEX_API_URL` at export)
  if the preview URL can be known at build time.
- Verified: `/` returns 200 and `/ping` returns `pong` with the token header.
