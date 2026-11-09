"""Reusable agent-facing blocks: copyable prompts, commands, tool calls."""

from __future__ import annotations

import reflex as rx

from web.components.core.hugeicon import hi
from web.components.ui.badge import badge
from web.components.ui.button import button
from web.components.ui.card import card
from web.components.ui.collapsible import collapsible
from web.components.ui.marker import marker
from web.components.ui.spinner import spinner

_TOGGLE_THEME_JS = """
const html = document.documentElement;
const next = html.classList.contains('dark') ? 'light' : 'dark';
html.classList.remove('light', 'dark');
html.classList.add(next);
html.style.colorScheme = next;
localStorage.setItem('theme', next);
"""


def theme_toggle() -> rx.Component:
    """Light/dark switch that flips the `.dark` class native themes key off."""
    return button(
        hi("SparklesIcon"),
        variant="ghost",
        size="icon",
        aria_label="Toggle theme",
        title="Toggle theme",
        on_click=rx.call_script(_TOGGLE_THEME_JS),
    )


def section(
    title: str,
    description: str,
    *children: rx.Component,
    anchor: str,
) -> rx.Component:
    """Page section with an anchor id so agents and humans can deep-link."""
    return rx.el.section(
        rx.el.div(
            rx.el.h2(title, class_name="text-2xl font-semibold tracking-tight"),
            rx.el.p(description, class_name="text-sm text-muted-foreground"),
            class_name="flex flex-col gap-1",
        ),
        *children,
        id=anchor,
        class_name="flex flex-col gap-6 scroll-mt-20",
    )


def feature_card(icon: str, title: str, body: str) -> rx.Component:
    """Card describing one agent-friendly property of the template."""
    return card.root(
        card.header(
            rx.el.div(
                hi(icon, class_name="size-5"),
                class_name="mb-2 flex size-9 items-center justify-center rounded-lg bg-muted",
            ),
            card.title(title),
            card.description(body),
        ),
    )


def prompt_block(label: str, prompt: str) -> rx.Component:
    """A prompt an agent (or human) can copy verbatim."""
    return card.root(
        card.header(
            card.title(label),
            card.action(
                button(
                    hi("Copy01Icon"),
                    "Copy",
                    variant="outline",
                    size="sm",
                    on_click=[
                        rx.set_clipboard(prompt),
                        rx.toast.success("Prompt copied"),
                    ],
                ),
            ),
        ),
        card.content(
            rx.el.pre(
                prompt,
                class_name=(
                    "whitespace-pre-wrap rounded-lg bg-muted p-3 font-mono "
                    "text-xs text-muted-foreground"
                ),
            ),
        ),
    )


def command_block(command: str, note: str) -> rx.Component:
    """One literal shell command with a one-line purpose and a copy button."""
    return rx.el.div(
        rx.el.div(
            rx.el.code(command, class_name="font-mono text-sm"),
            rx.el.span(note, class_name="text-xs text-muted-foreground"),
            class_name="flex min-w-0 flex-col gap-0.5",
        ),
        button(
            hi("Copy01Icon"),
            variant="ghost",
            size="icon-sm",
            aria_label=f"Copy {command}",
            title="Copy",
            on_click=[rx.set_clipboard(command), rx.toast.success("Copied")],
        ),
        class_name=(
            "flex items-center justify-between gap-3 rounded-lg border "
            "border-border px-3 py-2"
        ),
    )


def tool_call(
    name: rx.Var[str] | str,
    args: rx.Var[str] | str,
    result: rx.Var[str] | str,
    status: rx.Var[str] | str,
) -> rx.Component:
    """Collapsible tool-call row: status marker, call signature, result."""
    running = rx.cond(status == "running", True, False)
    return collapsible.root(
        collapsible.trigger(
            marker.root(
                marker.icon(
                    rx.cond(
                        running,
                        spinner(),
                        hi("Tick02Icon"),
                    ),
                ),
                marker.content(name, class_name="font-mono"),
            ),
            badge(status, variant="secondary"),
            class_name="flex w-full items-center justify-between gap-2",
        ),
        collapsible.panel(
            rx.el.div(
                rx.el.code(args, class_name="block font-mono text-xs"),
                rx.el.p(result, class_name="text-xs text-muted-foreground"),
                class_name="flex flex-col gap-1 rounded-lg bg-muted p-3",
            ),
        ),
        class_name="w-full",
    )
