"""Dagger checks for this repo. Run via `ci/run.sh <subcommand>`.

Subcommands: test [pytest args...], tach, all.
Plain SDK program (no Dagger module). Same code path locally and in RWX; CI
differences come only from env vars (CI_CACHE_DIR, CI_CACHE_WRITE).
"""  # noqa: INP001  # standalone script, not a package

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import anyio
import dagger
from dagger import dag

ROOT = Path(__file__).resolve().parent.parent
PYTHON_IMAGE = "python:3.13-slim-bookworm"
UV_IMAGE = "ghcr.io/astral-sh/uv:0.11.13"
UV_CACHE = "/root/.cache/uv"
EXCLUDE = [
    ".git", ".venv", "**/__pycache__", ".pytest_cache", ".trunk", ".context",
    "web/.web", "web/.reflex", ".web", "node_modules", "ci", ".rwx",
]  # fmt: skip


def _cache_dir() -> Path | None:
    value = os.environ.get("CI_CACHE_DIR")
    return Path(value) if value else None


def _base() -> dagger.Container:
    """Toolchain + locked deps; only pyproject/uv.lock feed the install layer."""
    src = dag.host().directory(str(ROOT), exclude=EXCLUDE)
    uv_cache = dag.cache_volume("reflex-starter-uv")
    seed = _cache_dir()
    mount_kwargs: dict[str, object] = {}
    if seed and (seed / "uv-cache").is_dir():
        # Seeds the volume only when it is empty (fresh engine on the runner).
        mount_kwargs["source"] = dag.host().directory(str(seed / "uv-cache"))
    ctr = (
        dag.container()
        .from_(PYTHON_IMAGE)
        .with_file("/usr/local/bin/uv", dag.container().from_(UV_IMAGE).file("/uv"))
        .with_env_variable("UV_LINK_MODE", "copy")
        .with_env_variable("UV_PROJECT_ENVIRONMENT", "/opt/venv")
        .with_mounted_cache(UV_CACHE, uv_cache, **mount_kwargs)
        .with_workdir("/src")
        .with_file("/src/pyproject.toml", src.file("pyproject.toml"))
        .with_file("/src/uv.lock", src.file("uv.lock"))
        .with_exec(["uv", "sync", "--frozen", "--no-install-project", "--group", "dev"])
    )
    return ctr.with_directory("/src", src)


async def _export_cache(ctr: dagger.Container) -> None:
    seed = _cache_dir()
    if not seed or os.environ.get("CI_CACHE_WRITE") != "true":
        return
    out = ctr.with_exec(["sh", "-c", f"rm -rf /uv-cache && cp -a {UV_CACHE} /uv-cache"])
    await out.directory("/uv-cache").export(str(seed / "uv-cache"))


async def test(pytest_args: list[str]) -> None:
    """Run pytest in the container and propagate its exit code."""
    ctr = _base().with_exec(["mkdir", "-p", "/results"]).with_exec(
        [
            "/opt/venv/bin/pytest", "-q",
            "--report-log=/results/pytest-results.json", *pytest_args,
        ],
        expect=dagger.ReturnType.ANY,
    )  # fmt: skip
    results_dir = Path(os.environ.get("CI_RESULTS_DIR", str(ROOT)))
    await ctr.file("/results/pytest-results.json").export(
        str(results_dir / "pytest-results.json"),
    )
    await _export_cache(ctr)
    code = await ctr.exit_code()
    if code:
        print(await ctr.stdout(), file=sys.stdout)  # noqa: T201
        print(await ctr.stderr(), file=sys.stderr)  # noqa: T201
        raise SystemExit(code)
    print(await ctr.stdout())  # noqa: T201


async def tach() -> None:
    """Run tach check and check-external in the container."""
    ctr = _base()
    for cmd in (["check"], ["check-external"]):
        out = await ctr.with_exec(["/opt/venv/bin/tach", *cmd]).stdout()
        print(out)  # noqa: T201


async def main() -> None:
    """Parse arguments and dispatch to the selected checks."""
    parser = argparse.ArgumentParser(prog="ci/run.sh")
    parser.add_argument("command", choices=["test", "tach", "all"])
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    ns = parser.parse_args()
    extra = [a for a in ns.pytest_args if a != "--"]
    async with dagger.connection(dagger.Config(log_output=sys.stderr)):
        if ns.command in ("tach", "all"):
            await tach()
        if ns.command in ("test", "all"):
            await test(extra)


if __name__ == "__main__":
    anyio.run(main)
