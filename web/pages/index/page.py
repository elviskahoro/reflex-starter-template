"""Index page: Elvis Kahoro's Reflex starter template, agent-first."""

# reflex's factory members (rx.el.*, rx.foreach, rx.toast.provider) are typed
# partially Unknown; suppress member-Unknown here as web/web.py does per-line.
# pyright: reportUnknownMemberType=false

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

import reflex as rx

from web.components.agent import (
    command_block,
    feature_card,
    prompt_block,
    section,
    theme_toggle,
    tool_call,
)
from web.components.core.hugeicon import hi
from web.components.ui.accordion import accordion
from web.components.ui.attachment import attachment
from web.components.ui.avatar import avatar
from web.components.ui.badge import badge
from web.components.ui.bubble import bubble
from web.components.ui.button import button
from web.components.ui.card import card
from web.components.ui.marker import marker
from web.components.ui.message import message
from web.components.ui.separator import separator
from web.components.ui.tabs import tabs

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# (tool, arguments, result) rows replayed by the live "agent run" demo.
_SCRIPT: tuple[tuple[str, str, str], ...] = (
    ("read_file", 'path="AGENTS.md"', "Loaded repo workflow and verification rules."),
    ("run", "uv run tach check", "Module boundaries OK."),
    ("run", "uv run pytest -q", "Smoke tests passed."),
)

_BOOTSTRAP_PROMPT = (
    "Read AGENTS.md and README.md first. Then replace the example page in "
    "web/pages/index with <my product>. Build UI only from web/components/ui "
    "(the shared UI kit) and add new modules to tach.toml. Verify with "
    "`uv run tach check` and `uv run pytest -q` before you stop."
)
_ADD_COMPONENT_PROMPT = (
    "Add a <component> from https://native.buridan.dev/docs/components to "
    "web/components/ui, mirroring the existing files. Keep theming in "
    "assets/globals.css CSS variables; do not hard-code colors."
)
_THEME_PROMPT = (
    "Retheme the app: edit only the :root and .dark variable blocks in "
    "assets/globals.css (generate a preset at https://native.buridan.dev/create). "
    "Do not touch component files."
)


class IndexState(rx.State):
    """State for the live agent-run demo."""

    count: int = 0
    running: bool = False
    steps: list[dict[str, str]] = []  # noqa: RUF012  # reflex state vars are per-instance

    @rx.event
    async def run_agent(self) -> AsyncGenerator[None, None]:
        """Replay a scripted agent run, streaming each tool call to the UI."""
        if self.running:
            return
        self.count += 1
        self.running = True
        self.steps = []
        yield
        for name, args, result in _SCRIPT:
            self.steps.append(
                {"name": name, "args": args, "result": "…", "status": "running"},
            )
            yield
            await asyncio.sleep(0.7)
            self.steps[-1] = {
                "name": name,
                "args": args,
                "result": result,
                "status": "done",
            }
            yield
        self.steps.append(
            {
                "name": "ping_backend",
                "args": f"request={self.count}",
                "result": await self._get_greeting(),
                "status": "done",
            },
        )
        self.running = False

    async def _get_greeting(self) -> str:
        """Backend function that processes requests and returns status."""
        timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
        return f"Request #{self.count} processed at {timestamp}"


def _hero() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            badge("Reflex 0.10", variant="secondary"),
            badge("One UI kit", variant="outline"),
            badge("Agent-ready", variant="outline"),
            class_name="flex flex-wrap justify-center gap-2",
        ),
        rx.el.h1(
            "Elvis Kahoro's Reflex Starter Template",
            class_name=(
                "max-w-3xl text-balance text-center text-4xl font-semibold "
                "tracking-tight sm:text-5xl"
            ),
        ),
        rx.el.p(
            "Agents write code fast but guess at your conventions. This template "
            "writes the conventions down, enforces them, and gives the agent a way to "
            "check its own work, so its first attempt is one you can merge.",
            class_name="max-w-2xl text-balance text-center text-muted-foreground",
        ),
        rx.el.div(
            rx.el.a(
                button(hi("Copy01Icon"), "Prompt your agent", size="lg"),
                href="#prompts",
            ),
            rx.el.a(
                button(
                    "See the UI kit",
                    hi("ArrowUpRight01Icon"),
                    variant="outline",
                    size="lg",
                ),
                href="https://native.buridan.dev/components",
                target="_blank",
                rel="noreferrer",
            ),
            class_name="flex flex-wrap justify-center gap-3",
        ),
        class_name="flex flex-col items-center gap-6 py-16 sm:py-24",
    )


def _features() -> rx.Component:
    return section(
        "Why it works with agents",
        "Agents fail when a repo is ambiguous. Each choice here removes one kind of "
        "ambiguity.",
        rx.el.div(
            feature_card(
                "File02Icon",
                "One source of instructions",
                "Without a single written workflow, every agent invents its own. "
                "AGENTS.md and CLAUDE.md point to one guide.",
            ),
            feature_card(
                "HexagonIcon",
                "Mistakes fail loudly",
                "Agents drift into tangled imports. tach.toml pins the layers, so a "
                "wrong import is an error, not a review comment.",
            ),
            feature_card(
                "CheckmarkBadge01Icon",
                "Checkable work",
                "An agent that can run a fast test and a type check catches its own "
                "bugs before you see them.",
            ),
            feature_card(
                "PaintBucketIcon",
                "One place to restyle",
                "Colors, radius, and fonts live in CSS variables, so a redesign is a "
                "one-file change an agent can't half-finish.",
            ),
            class_name="grid gap-4 sm:grid-cols-2 lg:grid-cols-4",
        ),
        anchor="why",
    )


def _render_step(step: dict[str, str]) -> rx.Component:
    """Render one streamed tool-call row from backend state."""
    return tool_call(
        step["name"],
        step["args"],
        step["result"],
        step["status"],
    )


def _transcript() -> rx.Component:
    """Static conversation plus the live tool-call stream."""
    return card.root(
        card.header(
            card.title("What the agent sees"),
            card.description(
                "Showing the work builds trust. This trace streams each tool call "
                "from backend state, so you see what the agent did, not just the "
                "result.",
            ),
            card.action(
                button(
                    rx.cond(IndexState.running, "Running…", "Run demo"),
                    on_click=IndexState.run_agent,
                    disabled=IndexState.running,
                    size="sm",
                ),
            ),
        ),
        card.content(
            message.group(
                message.root(
                    message.content(
                        bubble.root(
                            bubble.content(
                                "Add a pricing page and make sure checks pass.",
                            ),
                            align="end",
                        ),
                    ),
                    align="end",
                ),
                message.root(
                    message.avatar(
                        avatar.root(avatar.fallback("EK"), size="sm"),
                    ),
                    message.content(
                        message.header("Agent"),
                        bubble.root(
                            bubble.content(
                                "On it. Reading AGENTS.md, then verifying boundaries "
                                "and tests.",
                            ),
                            variant="muted",
                        ),
                        rx.foreach(IndexState.steps, _render_step),
                        rx.cond(
                            IndexState.count > 0,
                            marker.root(
                                marker.content(
                                    f"Runs this session: {IndexState.count}",
                                ),
                                variant="separator",
                            ),
                        ),
                        attachment.root(
                            attachment.media(hi("File02Icon")),
                            attachment.content(
                                attachment.title("AGENTS.md"),
                                attachment.description("Workflow guide · read first"),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def _patterns() -> rx.Component:
    return section(
        "Prompts that stay on the rails",
        "Vague asks produce off-pattern code. These name the files, the constraint, "
        "and the check, for the three jobs agents get most.",
        tabs.root(
            tabs.list(
                tabs.trigger("Bootstrap", value="bootstrap"),
                tabs.trigger("Add component", value="component"),
                tabs.trigger("Retheme", value="theme"),
            ),
            tabs.content(
                prompt_block("Bootstrap a product", _BOOTSTRAP_PROMPT),
                value="bootstrap",
            ),
            tabs.content(
                prompt_block("Add a UI component", _ADD_COMPONENT_PROMPT),
                value="component",
            ),
            tabs.content(
                prompt_block("Apply a theme preset", _THEME_PROMPT),
                value="theme",
            ),
            default_value="bootstrap",
            class_name="w-full",
        ),
        _transcript(),
        anchor="prompts",
    )


def _commands() -> rx.Component:
    return section(
        "Done means verified",
        "An agent that stops without running these is guessing. Exact commands leave "
        "nothing to improvise.",
        rx.el.div(
            command_block("uv sync --group dev", "Install locked dependencies"),
            command_block("uv run reflex run", "Start frontend and backend"),
            command_block("uv run pytest -q", "Smoke tests (network tests skipped)"),
            command_block("uv run tach check", "Module boundaries"),
            command_block("uv run tach check-external", "Declared vs imported deps"),
            command_block("trunk check --all", "Lint gate (merge-blocking)"),
            command_block("rwx run .rwx/pyrefly.yml --wait", "Type check (pyrefly)"),
            command_block("rwx run .rwx/pyright.yml --wait", "Type check (pyright)"),
            class_name="flex flex-col gap-2",
        ),
        anchor="verify",
    )


def _faq() -> rx.Component:
    return section(
        "Why the conventions are what they are",
        "Each rule exists to keep an agent from making a choice you'd have to undo.",
        accordion.root(
            accordion.item(
                accordion.trigger("Why one UI kit?"),
                accordion.panel(
                    rx.el.p(
                        "Ad-hoc markup makes every page look different and every "
                        "review longer. All UI comes from web/components/ui (the UI "
                        "kit linked below), so new pages match by construction. Add "
                        "missing pieces from native.buridan.dev instead of "
                        "hand-rolling them.",
                    ),
                ),
                name="faq",
                open=True,
            ),
            accordion.item(
                accordion.trigger("Why CSS variables for styling?"),
                accordion.panel(
                    rx.el.p(
                        "Hard-coded colors scatter across files and can't be changed "
                        "safely. Components read tokens from assets/globals.css, so "
                        "light/dark and any retheme work everywhere at once.",
                    ),
                ),
                name="faq",
            ),
            accordion.item(
                accordion.trigger("Why declare every module?"),
                accordion.panel(
                    rx.el.p(
                        "Undeclared modules are how architecture erodes unnoticed. "
                        "Declaring each one in tach.toml makes `uv run tach check` "
                        "fail the moment an agent crosses a boundary.",
                    ),
                ),
                name="faq",
            ),
            class_name="w-full",
        ),
        anchor="faq",
    )


def _footer() -> rx.Component:
    return rx.el.footer(
        separator(),
        rx.el.p(
            "Elvis Kahoro's Reflex Starter Template · UI kit: ",
            rx.el.a(
                "native",
                href="https://github.com/elviskahoro/native",
                class_name="underline underline-offset-4",
            ),
            class_name="pt-6 text-center text-xs text-muted-foreground",
        ),
        class_name="pb-10",
    )


def page() -> rx.Component:
    """Render the landing page."""
    return rx.el.main(
        rx.el.header(
            rx.el.span("elvis kahoro / reflex-starter", class_name="font-mono text-xs"),
            theme_toggle(),
            class_name=(
                "sticky top-0 z-10 flex items-center justify-between border-b "
                "border-border bg-background/80 px-4 py-2 backdrop-blur"
            ),
        ),
        rx.el.div(
            _hero(),
            _features(),
            _patterns(),
            _commands(),
            _faq(),
            _footer(),
            class_name="mx-auto flex w-full max-w-5xl flex-col gap-16 px-4",
        ),
        rx.toast.provider(),
        class_name="min-h-screen bg-background text-foreground",
    )
