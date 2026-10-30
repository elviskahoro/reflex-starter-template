

<!-- entire-agent:begin -->
Read .entire/agent-guide.md for this repository's workflow, source inspection, and verification guidance.
@.entire/agent-guide.md
<!-- entire-agent:end -->

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
