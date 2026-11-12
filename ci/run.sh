#!/usr/bin/env bash
# Run a CI check through the Dagger engine: `ci/run.sh test|tach|all [args]`.
# Needs Docker + the dagger CLI (0.21.8). CI_PYTHON overrides the interpreter
# (RWX sets it to its prebuilt SDK venv); locally uv provisions it from ci/.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${CI_PYTHON:-}" ]]; then
  exec dagger run "${CI_PYTHON}" "${root}/ci/main.py" "$@"
fi
exec dagger run uv run --project "${root}/ci" --frozen python "${root}/ci/main.py" "$@"
