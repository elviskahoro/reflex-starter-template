
<!-- entire-agent:begin -->
Read .entire/agent-guide.md for this repository's workflow, source inspection, and verification guidance.
@.entire/agent-guide.md
<!-- entire-agent:end -->

## Working issues and labels

Canonical protocol: https://github.com/elviskahoro/oss-hq/blob/main/AGENT-LABELS.md

| Label | Meaning |
| --- | --- |
| `status::in_progress` | Claimed and being worked on by an agent. Do not pick up. |
| `status::blocked` | Waiting on another issue in this repo ("blocked by #N"). |
| `status::blocked-external` | Waiting on something outside the repo (another repo, upstream, a vendor). |
| `status::deferred` | Parked on purpose; revisit date is in a comment. |
| `needs-human` | A person must decide. Agents must not pick up. |
| `gas-city` | Routed to Gas City. Conductor dispatch must not pick up. |
| `stale-claim` | Claim has no recent heartbeat; reclaimable. |

### Picking up work

1. Never pick up an issue labeled `needs-human`, `status::in_progress`,
   `status::blocked`, `status::blocked-external`, `status::deferred`, or `gas-city`.
2. An issue labeled `stale-claim` may be reclaimed. Re-claim it and comment that
   you took over.

### Claiming (required before any work)

3. When you start an issue, claim it first: add `status::in_progress`, assign
   yourself, and leave a one-line "starting" comment.
4. If `status::in_progress` is already present, stop. Two agents must never work
   one issue.
5. Re-read the labels right after claiming. If another agent claimed at the same
   moment, back off.
6. For long-running work, comment periodically so the claim does not become a
   `stale-claim`. (Heartbeat interval and what sets `stale-claim` are not yet
   defined.)

### Releasing

7. When done, put `Closes #N` in the PR body and remove `status::in_progress` once
   the PR is open. Merge closes the issue.
8. If you abandon or fail, remove `status::in_progress` and comment what happened
   and what remains. Never leave a dead claim.
9. If you need a decision you cannot make, remove `status::in_progress`, add
   `needs-human`, and comment the exact question. Do not guess. Never remove
   `needs-human` yourself.

### Blocked and deferred

10. Blocked by another issue in this repo: add `status::blocked`, comment
    "blocked by #N", and release the claim.
11. Blocked by something outside the repo: add `status::blocked-external`, comment
    what you are waiting on, and release the claim.
12. Never set `status::deferred` yourself. Only a human parks work.

### Visibility

13. gh-dash hides issues labeled `status::*` and `gas-city`, so label hygiene
    decides what humans see.

## RWX CLI

Full guide: `rwx` skill in `.agents/skills/rwx/`. Auth: tokens are injected as
`RWX_ACCESS_TOKEN_<WORKSPACE>` / `RWC_ACCESS_TOKEN_<WORKSPACE>`; the CLI reads only
`RWX_ACCESS_TOKEN`, so export the one matching the repo owner (never print it):

```bash
OWNER=$(git remote get-url origin | sed -E 's#.*[:/]([^/]+)/[^/]+(\.git)?$#\1#' | tr a-z A-Z)
export RWX_ACCESS_TOKEN="$(printenv "RWX_ACCESS_TOKEN_$OWNER" || printenv "RWC_ACCESS_TOKEN_$OWNER")"
```

- `rwx run .rwx/<file>.yml --wait` runs a pipeline on your local changes (no push
  needed); `--target <task>`, `--init key=value`, `--json`.
- `rwx results <run-id>`, `rwx logs <task-id>`, `rwx artifacts`, `rwx runs list`.
- `rwx run .rwx/pyright.yml --wait` / `pyrefly.yml` for type checks without a `.venv`.
- `rwx sandbox exec -- <cmd>`, `rwx lint .rwx/<file>.yml`, `rwx docs search|pull`.

## RWX PR previews

`.rwx/preview.yml` defines the preview app (see the `rwx-reflex-preview` skill in
`.agents/skills/`). Validate with `rwx lint .rwx/preview.yml`; test with
`rwx run .rwx/preview.yml --init pull-request-number=0 --wait`. Previews are
private: access them with the `X-RWX-Access-Token` header (RWX docs). Only use
behavior documented in the RWX docs or `rwx --help`. Known open issue: the
frontend's baked-in `localhost:8000` API URL is patched in the build step
(undocumented workaround, WebSocket events unverified).

## Build & Test

```bash
uv sync --group dev          # install locked deps into .venv
uv run pytest -q             # smoke tests (`network`-marked tests deselected)
uv run tach check            # module boundaries
uv run tach check-external   # declared vs imported dependencies
uv run python scripts/check_frontend.py  # JS deps vs reflex.lock (needs bun; ~1 min)
trunk check --all            # lint (run uv sync first: pyright/pyrefly use .venv)
```

## Conventions

- Layers are `web.web` -> `web.pages.*` -> `web.components.*`, enforced by
  `tach.toml`; new modules need an explicit entry there.
- `tach check-external` is its own task in `.rwx/trunk-check.yml`, not a Trunk
  linter: Trunk lints from a sandbox holding only the diff, which makes every
  dependency look unused.
- `uv` ignores packages published in the last 7 days (`[tool.uv] exclude-newer`);
  pyrefly/pyright/tach pins must match between `pyproject.toml` and
  `.trunk/trunk.yaml`.
- RWX: a green run is not proof a step worked. Read task logs (`rwx logs`) for
  steps that talk to third parties.
- Use non-interactive flags (`-y`, `-f`, `trunk ... --ci < /dev/null`) in
  scripted commands.

## Git workflow

- Commit only when the user explicitly asks; show what will be committed first.
- Do not push to the remote unless explicitly asked.
- Ask before using any escape hatch that bypasses a check (skip flags,
  `--no-verify`, lint/type ignores).

## CI logic (Dagger)

pytest and `tach` run through `ci/` (plain Dagger SDK program, see `ci/README.md`):
`ci/run.sh test|tach|all`. Dagger needs Docker, so it cannot run in Conductor
cloud sandboxes; validate with `rwx run .rwx/tests.yml --wait` (stage new files
with `git add` first).
