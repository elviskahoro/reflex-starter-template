# ci/: Dagger checks (plain SDK program, no Dagger module)

Run locally with Docker + `dagger` CLI **0.21.8** + `uv`:

    ci/run.sh test            # pytest (extra args after `--` go to pytest)
    ci/run.sh tach            # tach check + tach check-external
    ci/run.sh all

`dagger-io` is pinned to 0.21.8 in `ci/pyproject.toml` / `ci/uv.lock`; keep the CLI,
SDK and engine image (`registry.dagger.io/engine:v0.21.8`) in lockstep.
On Dagger 1.x the entry point changes from `dagger run` to `dagger api with-session`.

**Dagger cannot run in Conductor cloud sandboxes** (no Docker). Validate in RWX:
`rwx run .rwx/tests.yml --wait` (commit or `git add` new files first; untracked
files are not sent).

## Layers

- A (RWX, cached): uv, dagger CLI (sha256-pinned), SDK venv (`ci/` lockfile only), engine image pre-pull.
- B (RWX): triggers, status checks, trunk lint, pyright/pyrefly, frontend, reflex build, nightly.
- C (Dagger): pytest (`pytest` task in tests.yml), tach (`tach-external` in trunk-check.yml).

## Environment

- `CI_PYTHON`: interpreter for the SDK (RWX sets it; locally uv provides it).
- `CI_RESULTS_DIR`: where `pytest-results.json` is exported (default repo root; Captain reads it).
- `CI_CACHE_DIR` / `CI_CACHE_WRITE=true`: optional uv-cache import/export hooks. Not yet wired to an RWX `tool-cache`.

## Caching

Inside Dagger: the install layer depends only on `pyproject.toml` + `uv.lock`; uv downloads use a cache volume.
In RWX: the install tasks are filtered, so source changes re-run only the final Dagger task.
Debug: `rwx logs <task-id>`, or run locally and inspect the Dagger TUI output.
