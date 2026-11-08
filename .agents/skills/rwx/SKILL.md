---
name: rwx
description: Use the RWX CLI in this repo - authenticate with the injected access tokens, run `.rwx/*.yml` pipelines against local changes, read results and logs, run sandboxes, and create or edit RWX configs. Use when asked about RWX, when CI is red or failing, to run tests/type checks on RWX, to fetch run logs or artifacts, or to modify any file in `.rwx/`.
allowed-tools: Bash(rwx lint *), Bash(rwx docs *), Bash(rwx logs *), Bash(rwx artifacts *), Bash(rwx results *), Bash(rwx whoami), Bash(rwx * --help)
---

# RWX CLI in this repo

Check the CLI first: `rwx --version` and `rwx whoami`. For previews (`.rwx/preview.yml`) also see the `rwx-reflex-preview` skill.

## Auth: injected tokens, one per RWX workspace

Env vars `RWX_ACCESS_TOKEN_<WORKSPACE>` or `RWC_ACCESS_TOKEN_<WORKSPACE>` are injected, each scoped to one RWX workspace. List names only, never values:

```bash
env | grep -E '^RW[XC]_ACCESS_TOKEN_' | cut -d= -f1
```

The CLI reads only `RWX_ACCESS_TOKEN` (or `--access-token`). Export the token whose suffix matches the repo owner (uppercased owner from `git remote`, here `ELVISKAHORO`). Never print it:

```bash
OWNER=$(git remote get-url origin | sed -E 's#.*[:/]([^/]+)/[^/]+(\.git)?$#\1#' | tr a-z A-Z)
export RWX_ACCESS_TOKEN="$(printenv "RWX_ACCESS_TOKEN_$OWNER" || printenv "RWC_ACCESS_TOKEN_$OWNER")"
rwx whoami   # confirm organization
```

Run IDs, task IDs and logs resolve only under the workspace that owns them. If a lookup returns not-found or unauthorized, try the other workspace's token. On a laptop, `rwx login` works instead.

## Pipelines (`.rwx/`)

| File | GitHub trigger | Purpose |
| --- | --- | --- |
| `tests.yml` | PR/push | pytest smoke tests, tach |
| `trunk-check.yml` | PR/push | lint (Trunk), `tach check-external` |
| `frontend.yml` | PR/push | JS deps vs `reflex.lock` |
| `reflex-build.yml` | push to `main`/`trunk-merge/*` | Reflex export build |
| `preview.yml` | pull request | PR preview app |
| `smoke-nightly.yml` | push to `main` + cloud schedule | nightly smoke |
| `pyright.yml`, `pyrefly.yml` | none (manual) | on-demand type checks |

Every file has an `on.cli` trigger, so all can be started locally.

## Run a pipeline with local changes

`rwx run` sends a git patch; no commit or push needed for the changes themselves:

- Base: closest ancestor of local `HEAD` already on `origin` (`event.git.sha`). A `HEAD` that was never pushed cannot resolve, so push the branch once if a run fails to clone.
- Patch: unpushed commits, staged, unstaged and untracked files. `.gitignore`d files are excluded; Git LFS changes error out.
- `RWX_DISABLE_GIT_PATCH=1` disables patching.

```bash
rwx run .rwx/tests.yml --wait --fail-fast
rwx run .rwx/tests.yml --target <task-key> --wait     # one task plus dependencies
rwx run .rwx/pyright.yml --wait --init paths="web/foo.py web/bar.py"
rwx run .rwx/pyrefly.yml --wait
rwx run .rwx/tests.yml --title "wip: my change" --json
```

Keep `commit-sha: ${{ event.git.sha }}` in the `cli` trigger and `ref: ${{ init.commit-sha }}` on `git/clone`; that wiring makes the patch apply. Use pyright/pyrefly runs when there is no local `.venv` or memory is tight.

## Results, logs, artifacts

```bash
rwx runs list
rwx results <run-id>                              # status and failures (also: rwx results -h for branch/commit lookup)
rwx logs <task-id>
rwx logs <run-id> --task <task-key> --output /tmp/logs
rwx artifacts --help
rwx retry --help ; rwx cancel --help ; rwx debug --help ; rwx ssh --help
```

`rwx run` prints the run URL and ID; `--json` for parsing. A green run is not proof a step worked: read logs for steps that talk to third parties. "CI is red" means: `rwx results` for the branch, then `rwx logs` for the failing task.

## Other commands

- Sandboxes: `rwx sandbox exec -- <command>` (also `init`, `list`, `start`, `stop`, `reset`).
- Preview apps: `rwx apps --help`. Secrets and vars: `rwx vaults --help`. Crons: `rwx crons --help`. Dispatch workflows: `rwx dispatch --help`.
- Package/base-image versions: `rwx resolve`, `rwx update`.

## Create or modify configs

1. Pull the reference in full, without truncating: `rwx docs pull /migrating/rwx-reference`.
2. For anything else: `rwx docs search "<query>"`, then `rwx docs pull <path>` (e.g. `/docs/cli-triggers`, `/docs/cli-reference/rwx-run`). Use these, not WebFetch.
3. Edit, then validate: `rwx lint .rwx/<name>.yml`.
4. Prefer RWX packages, DAG parallelism and content-based caching.
5. Migrating GitHub Actions: upstream skills at https://github.com/rwx-cloud/skills (`migrate-from-gha`, `review-gha-migration`).

Only rely on behavior documented in RWX docs or `rwx --help`.
