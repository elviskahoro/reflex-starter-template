"""Smoke net: page compiles and agent blocks accept literal and Var inputs."""

from __future__ import annotations

import reflex as rx

from web.components.agent import (
    command_block,
    prompt_block,
    tool_call,
)
from web.pages.index import page as index_page


def test_index_page_renders_branding_and_sections() -> None:
    """The landing page names the template and exposes anchored sections."""
    tree = str(index_page())
    assert "Elvis Kahoro" in tree
    for anchor in ("why", "prompts", "verify", "faq"):
        assert anchor in tree


def test_prompt_and_command_blocks_are_components() -> None:
    """Agent blocks return components for literal inputs."""
    assert isinstance(prompt_block("Label", "do the thing"), rx.Component)
    assert isinstance(command_block("uv run pytest -q", "tests"), rx.Component)


def test_tool_call_accepts_literals() -> None:
    """tool_call renders from plain strings."""
    assert isinstance(tool_call("run", "ls", "ok", "done"), rx.Component)
