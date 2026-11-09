---
name: rwx-reflex-preview
description: Set up, run, debug, and access RWX preview apps (.rwx/preview.yml) for this Reflex starter. Use when working on PR previews, `rwx run`, rwx.run URLs, or preview auth.
---

# RWX preview apps for Reflex

Config lives in `.rwx/preview.yml`. Docs: https://www.rwx.com/docs/apps and
https://www.rwx.com/blog/preview-your-web-apps-with-rwx. Stick to the docs and
`rwx <cmd> --help`; don't guess at syntax.

## Layout

Tasks: `code` (git/clone) -> `uv-install` (checksum-pinned uv) -> `deps`
(`uv sync --frozen`) -> `bun-install` (pinned bun) -> `reflex-export` (`reflex export --frontend-only`)
-> `system-deps` (caddy, unzip) -> `build` (unzips `frontend.zip` to
`/srv`) -> `preview` (`app:` task, port 3000, runs backend on :8000 +
Caddy via the repo Caddyfile) -> `share-link` (prints
`tasks.preview.app.url`).

`code`/`uv-install`/`deps`/`bun-install`/`reflex-export` are byte-identical to
`reflex-build.yml` so RWX's content cache reuses its export instead of
re-running it; keep them in lockstep.

## Commands

- Validate: `rwx lint .rwx/preview.yml` (also flags outdated package versions)
- Test: `rwx run .rwx/preview.yml --init pull-request-number=0 --wait`
  (a local run has no PR number, so `init.pull-request-number` must be passed)
- Local changes are included: `rwx run` uploads a git patch (unpushed commits,
  staged/unstaged/untracked files) applied on top of `event.git.sha` by the
  `code` task, so no push is needed. See the `rwx` skill for limits.
- Share: `rwx apps share pr-0 --expires-in 7d` prints a private-app link
  (`https://pr-0--<workspace>.rwx.run/rwx-share?code=...`); verified 200.
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
