from typing import Any, cast

import reflex as rx
from reflex.components.component import ComponentNamespace
from reflex_components_core.el import (
    Dialog as BaseDialog,
    Div,
)

from ..core.core import CoreComponent, cn


class ClassNames:
    POPUP = (
        "hidden open:grid m-auto w-full max-w-[calc(100%-2rem)] gap-4 rounded-xl "
        "bg-popover p-4 text-sm text-popover-foreground ring-1 ring-foreground/10 "
        "outline-hidden sm:max-w-sm "
        "backdrop:bg-black/10 backdrop:supports-backdrop-filter:backdrop-blur-xs"
    )
    HEADER = "flex flex-col gap-2"
    TITLE = "text-base leading-none font-medium text-foreground"
    DESCRIPTION = "text-sm text-muted-foreground"
    FOOTER = (
        "-mx-4 -mb-4 flex flex-col-reverse gap-2 rounded-b-xl border-t "
        "border-foreground/10 bg-muted/50 p-4 sm:flex-row sm:justify-end"
    )
    CLOSE = (
        "rounded-xs opacity-70 transition-opacity hover:opacity-100 "
        "focus:outline-hidden text-muted-foreground"
    )
    CLOSE_ICON = "!absolute !top-2 !right-2"


GLOBAL_HANDLERS_JS = """
(function () {
    if (window.__dialogGlobalHandlersAttached) return;
    window.__dialogGlobalHandlersAttached = true;
    function popupFor(el) {
        var root = el.closest('[data-slot="dialog-root"]');
        return root
            ? root.querySelector('dialog[data-slot="dialog-content"]')
            : null;
    }
    document.addEventListener('click', function (e) {
        var target = e.target;
        if (!target || !target.closest) return;
        var trigger = target.closest('[data-slot="dialog-trigger"]');
        if (trigger) {
            var opened = popupFor(trigger);
            if (opened) opened.showModal();
            return;
        }
        var closer = target.closest('[data-slot="dialog-close"]');
        if (closer) {
            var closing = popupFor(closer);
            if (closing) closing.close();
            return;
        }
        if (
            target.matches('dialog[data-slot="dialog-content"]')
            && target.getAttribute('data-dismissible') === 'true'
        ) {
            // A native <dialog> is both the ::backdrop target (retargeted
            // outside clicks) and the hit-test box for the card itself, so
            // a target match alone can't tell a true backdrop click from an
            // interior click on the card's own padding/gaps. Only close when
            // the click landed outside the dialog's bounding box.
            var r = target.getBoundingClientRect();
            if (
                e.clientX < r.left || e.clientX > r.right
                || e.clientY < r.top || e.clientY > r.bottom
            ) {
                target.close();
            }
        }
    }, true);
})();
"""


class DialogRoot(CoreComponent):
    """Scoping wrapper that owns the delegated dialog click handler.

    A single capturing document ``click`` listener (attached once per page)
    resolves trigger / close / backdrop clicks from the runtime DOM, so no
    build-time element ids are baked in and ``rx.foreach`` copies stay
    independent.
    """

    @classmethod
    def create(cls, *children: Any, **props: Any) -> rx.Component:
        props["data-slot"] = "dialog-root"

        user_on_mount = props.pop("on_mount", None)
        mount_handlers = [rx.call_script(GLOBAL_HANDLERS_JS)]
        if user_on_mount is not None:
            if isinstance(user_on_mount, list):
                mount_handlers.extend(user_on_mount)
            else:
                mount_handlers.append(user_on_mount)
        props["on_mount"] = mount_handlers

        cls.set_class_name("contents", props)
        return rx.el.div(*children, **props)


class DialogTrigger(CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> rx.Component:
        custom_classes = props.pop("class_name", "")
        props["data-slot"] = "dialog-trigger"
        cls.set_class_name(cn("contents", custom_classes), props)
        return rx.el.div(*children, **props)


class DialogPopup(BaseDialog, CoreComponent):
    on_close: rx.EventHandler = cast("Any", None)
    on_cancel: rx.EventHandler = cast("Any", None)

    @classmethod
    def create(
        cls,
        *children: Any,
        dismissible: bool = True,
        on_open_change: rx.EventHandler | None = None,
        **props: Any,
    ) -> rx.Component:
        props["data-slot"] = "dialog-content"

        custom_classes = props.pop("class_name", "")

        cls.set_class_name(cn(ClassNames.POPUP, custom_classes), props)

        if on_open_change is not None:
            props["on_close"] = lambda: on_open_change(False)
        if not dismissible:
            props["on_cancel"] = rx.prevent_default
        else:
            props["data-dismissible"] = "true"

        return super().create(*children, **props)


class DialogClose(CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> rx.Component:
        custom_classes = props.pop("class_name", "")
        props["data-slot"] = "dialog-close"
        cls.set_class_name(cn("contents", custom_classes), props)
        return rx.el.div(*children, **props)


class DialogTitle(CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> rx.Component:
        props["data-slot"] = "dialog-title"
        cls.set_class_name(ClassNames.TITLE, props)
        return rx.el.h2(*children, **props)


class DialogDescription(CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> rx.Component:
        props["data-slot"] = "dialog-description"
        cls.set_class_name(ClassNames.DESCRIPTION, props)
        return rx.el.p(*children, **props)


class DialogHeader(Div, CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> Div:
        props["data-slot"] = "dialog-header"
        cls.set_class_name(ClassNames.HEADER, props)
        return super().create(*children, **props)


class DialogFooter(Div, CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> Div:
        props["data-slot"] = "dialog-footer"
        cls.set_class_name(ClassNames.FOOTER, props)
        return super().create(*children, **props)


class Dialog(ComponentNamespace):
    root = staticmethod(DialogRoot.create)
    trigger = staticmethod(DialogTrigger.create)
    popup = staticmethod(DialogPopup.create)
    close = staticmethod(DialogClose.create)
    title = staticmethod(DialogTitle.create)
    description = staticmethod(DialogDescription.create)
    header = staticmethod(DialogHeader.create)
    footer = staticmethod(DialogFooter.create)
    class_names = ClassNames


dialog = Dialog()
