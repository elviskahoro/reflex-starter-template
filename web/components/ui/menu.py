import itertools
from typing import Any, ClassVar

import reflex as rx
from reflex.components.component import ComponentNamespace

from ..core.core import CoreComponent, cn

_menu_id_counter = itertools.count()


class ClassNames:
    TRIGGER = "inline-block list-none cursor-pointer [&::-webkit-details-marker]:hidden"
    TRIGGER_INNER = "flex w-fit items-center"
    CONTENT = (
        "absolute z-50 min-w-32 rounded-lg bg-popover p-1 text-popover-foreground "
        "shadow-md ring-1 ring-foreground/10 outline-none"
    )
    ITEM = (
        "group/menu-item relative flex cursor-default items-center gap-1.5 "
        "rounded-lg px-1.5 py-1 text-sm outline-hidden select-none "
        "hover:bg-accent hover:text-accent-foreground "
        "data-[variant=destructive]:text-destructive "
        "data-[variant=destructive]:hover:bg-destructive/10 "
        "data-[variant=destructive]:hover:text-destructive "
        "data-disabled:pointer-events-none data-disabled:opacity-50 "
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4"
    )
    SEPARATOR = "-mx-1 my-1 h-px bg-border"
    GROUP_LABEL = "px-1.5 py-1 text-xs font-medium text-muted-foreground"
    SHORTCUT = "ml-auto text-xs tracking-widest text-muted-foreground"
    SIDE_OFFSETS: ClassVar[dict[str, str]] = {
        "bottom": "top-full",
        "top": "bottom-full",
        "right": "left-full",
        "left": "right-full",
    }


class MenuRoot(CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> rx.Component:
        props.setdefault("id", f"menu-{next(_menu_id_counter)}")
        props["data-slot"] = "menu"
        cls.set_class_name("relative inline-block", props)

        props["on_mount"] = rx.call_script(
            """
            if (!window.__menuGlobalHandlersAttached) {
                window.__menuGlobalHandlersAttached = true;

                document.addEventListener('keydown', function (e) {
                    if (e.key === 'Escape') {
                        document
                            .querySelectorAll('details[data-slot="menu"][open]')
                            .forEach(function (el) { el.open = false; });
                    }
                });

                document.addEventListener('click', function (e) {
                    var closer = e.target && e.target.closest
                        ? e.target.closest('[data-close-menu="true"]')
                        : null;
                    var owner = closer
                        ? closer.closest('details[data-slot="menu"]')
                        : null;
                    if (owner) owner.open = false;
                    document
                        .querySelectorAll('details[data-slot="menu"][open]')
                        .forEach(function (el) {
                            if (!el.contains(e.target)) {
                                el.open = false;
                            }
                        });
                }, true);
            }
            """,
        )

        return rx.el.details(*children, **props)


class MenuTrigger(CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> rx.Component:
        props["data-slot"] = "menu-trigger"
        cls.set_class_name(ClassNames.TRIGGER, props)
        return rx.el.summary(
            rx.el.div(*children, class_name=ClassNames.TRIGGER_INNER),
            **props,
        )


class MenuContent(CoreComponent):
    @classmethod
    def create(
        cls,
        *children: Any,
        side: str = "bottom",
        side_offset: int = 4,
        align: str = "start",
        **props: Any,
    ) -> rx.Component:
        props["data-slot"] = "menu-content"
        props["data-side"] = side

        margin_key = {
            "bottom": "marginTop",
            "top": "marginBottom",
            "left": "marginRight",
            "right": "marginLeft",
        }.get(side, "marginTop")
        props["style"] = {margin_key: f"{side_offset}px", **props.get("style", {})}

        position_class = ClassNames.SIDE_OFFSETS.get(side, "top-full")
        if side in ("left", "right"):
            align_class = {
                "start": "top-0",
                "end": "bottom-0",
                "center": "top-1/2 -translate-y-1/2",
            }.get(align, "top-0")
        else:
            align_class = {
                "start": "left-0",
                "end": "right-0",
                "center": "left-1/2 -translate-x-1/2",
            }.get(align, "left-0")

        cls.set_class_name(cn(ClassNames.CONTENT, position_class, align_class), props)
        return rx.el.div(*children, **props)


class MenuItem(CoreComponent):
    """Menu row. ``close_on_click`` is handled by the delegated click listener
    that ``MenuRoot`` attaches (via ``data-close-menu``), so no build-time id is
    baked in and the item is safe inside ``rx.foreach``.
    """

    @classmethod
    def create(
        cls,
        *children: Any,
        close_on_click: bool = True,
        **props: Any,
    ) -> rx.Component:
        props["data-slot"] = "menu-item"
        cls.set_class_name(ClassNames.ITEM, props)

        variant = props.pop("variant", "default")
        props["data-variant"] = variant

        if close_on_click:
            props["data-close-menu"] = "true"

        return rx.el.div(*children, **props)


class MenuClose(CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> rx.Component:
        props["data-slot"] = "menu-close"
        props.setdefault("type", "button")
        props["data-close-menu"] = "true"

        cls.set_class_name(ClassNames.ITEM, props)
        return rx.el.div(*children, **props)


class MenuSeparator(CoreComponent):
    @classmethod
    def create(cls, **props: Any) -> rx.Component:
        props["data-slot"] = "menu-separator"
        cls.set_class_name(ClassNames.SEPARATOR, props)
        return rx.el.div(**props)


class MenuGroupLabel(CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> rx.Component:
        props["data-slot"] = "menu-group-label"
        cls.set_class_name(ClassNames.GROUP_LABEL, props)
        return rx.el.div(*children, **props)


class MenuShortcut(CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> rx.Component:
        props["data-slot"] = "menu-shortcut"
        cls.set_class_name(ClassNames.SHORTCUT, props)
        return rx.el.span(*children, **props)


class Menu(ComponentNamespace):
    root = staticmethod(MenuRoot.create)
    trigger = staticmethod(MenuTrigger.create)
    content = staticmethod(MenuContent.create)
    item = staticmethod(MenuItem.create)
    close = staticmethod(MenuClose.create)
    separator = staticmethod(MenuSeparator.create)
    group_label = staticmethod(MenuGroupLabel.create)
    shortcut = staticmethod(MenuShortcut.create)
    class_names = ClassNames


menu = Menu()
