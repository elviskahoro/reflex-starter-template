from typing import Any

import reflex as rx
from reflex.components.component import ComponentNamespace
from reflex_components_core.el import Div

from ..core.core import CoreComponent, cn


class ClassNames:
    ROOT = (
        "group/tabs flex gap-2 "
        "data-[orientation=horizontal]:flex-col "
        "data-[orientation=vertical]:flex-row"
    )

    LIST = (
        "group/tabs-list inline-flex w-fit items-center justify-center rounded-lg p-[3px] text-muted-foreground "
        "group-data-[orientation=horizontal]/tabs:h-8 group-data-[orientation=vertical]/tabs:h-fit group-data-[orientation=vertical]/tabs:flex-col "
        "data-[variant=line]:rounded-none data-[variant=default]:bg-muted data-[variant=line]:gap-1 data-[variant=line]:bg-transparent"
    )

    TRIGGER = (
        "relative inline-flex h-[calc(100%-1px)] flex-1 items-center justify-center gap-1.5 rounded-md border border-transparent px-1.5 py-0.5 text-sm font-medium whitespace-nowrap text-foreground/60 transition-all "
        "group-data-[orientation=vertical]/tabs:w-full group-data-[orientation=vertical]/tabs:justify-start hover:text-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-1 focus-visible:outline-ring disabled:pointer-events-none disabled:opacity-50 "
        "has-data-[icon=inline-end]:pr-1 has-data-[icon=inline-start]:pl-1 aria-disabled:pointer-events-none aria-disabled:opacity-50 dark:text-muted-foreground dark:hover:text-foreground "
        "group-data-[variant=default]/tabs-list:data-[active=true]:shadow-sm group-data-[variant=line]/tabs-list:data-[active=true]:shadow-none [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 "
        "group-data-[variant=line]/tabs-list:bg-transparent group-data-[variant=line]/tabs-list:data-[active=true]:bg-transparent dark:group-data-[variant=line]/tabs-list:data-[active=true]:border-transparent dark:group-data-[variant=line]/tabs-list:data-[active=true]:bg-transparent "
        "data-[active=true]:bg-background data-[active=true]:text-foreground dark:data-[active=true]:border-input dark:data-[active=true]:bg-input/30 dark:data-[active=true]:text-foreground "
        "after:absolute after:bg-foreground after:opacity-0 after:transition-opacity group-data-[orientation=horizontal]/tabs:after:inset-x-0 group-data-[orientation=horizontal]/tabs:after:bottom-[-5px] group-data-[orientation=horizontal]/tabs:after:h-0.5 group-data-[orientation=vertical]/tabs:after:inset-y-0 group-data-[orientation=vertical]/tabs:after:-right-1 group-data-[orientation=vertical]/tabs:after:w-0.5 group-data-[variant=line]/tabs-list:data-[active=true]:after:opacity-100 cursor-pointer"
    )

    CONTENT = "flex-1 text-sm outline-none hidden data-[active=true]:block"


GLOBAL_HANDLERS_JS = """
(function () {
    function syncGroup(root) {
        var rootValue = root.dataset.value;
        root.querySelectorAll('[data-slot="tabs-trigger"]').forEach(function (el) {
            if (el.closest('[data-slot="tabs"]') !== root) return;
            el.setAttribute(
                'data-active',
                el.getAttribute('data-value') === rootValue ? 'true' : 'false'
            );
        });
        root.querySelectorAll('[data-slot="tabs-content"]').forEach(function (el) {
            if (el.closest('[data-slot="tabs"]') !== root) return;
            el.setAttribute(
                'data-active',
                el.getAttribute('data-value') === rootValue ? 'true' : 'false'
            );
        });
    }
    if (!window.__tabsGlobalHandlersAttached) {
        window.__tabsGlobalHandlersAttached = true;
        document.addEventListener('click', function (e) {
            var target = e.target;
            var trigger = target && target.closest
                ? target.closest('[data-slot="tabs-trigger"]')
                : null;
            if (!trigger) return;
            var root = trigger.closest('[data-slot="tabs"]');
            if (!root) return;
            root.dataset.value = trigger.getAttribute('data-value');
            syncGroup(root);
        });
    }
    document.querySelectorAll('[data-slot="tabs"]').forEach(function (root) {
        syncGroup(root);
    });
})();
"""


class TabsRoot(Div, CoreComponent):
    """The main tabs container and active-state owner.

    ``create`` attaches a single delegated document ``click`` listener on mount
    (guarded by ``window.__tabsGlobalHandlersAttached`` so it is only attached
    once per page) plus a one-shot mount pass that marks every trigger and
    content panel against its own root's ``data-value``. The listener resolves
    the clicked trigger from the runtime DOM event target and reads its rendered
    ``data-value`` attribute, so the same script powers active-tab highlight and
    panel visibility for every Tabs instance on the page -- including triggers
    and panels produced by ``rx.foreach`` or a single trigger/content instance
    placed in multiple positions.

    This deliberately avoids keys/bakes that run once at template-build time
    inside ``create()``: a build-time element id would be shared across every
    rendered copy (duplicate DOM ids + ``getElementById`` resolving to the first
    copy), and interpolating the per-item ``value`` Var into the JS source would
    bake the Var's placeholder name as a string literal that matches no trigger.
    Both failure modes are structural to ``rx.foreach`` usage and are fixed here
    by reading everything off the runtime DOM at click/mount time. The content
    half uses the same mechanism (a static ``data-[active=true]:block`` variant
    over a runtime ``data-active`` attribute) instead of baking ``value`` into a
    Tailwind class, so data-driven panels become visible instead of staying
    ``hidden`` forever.
    """

    @classmethod
    def create(cls, *children: Any, **props: Any) -> Div:
        orientation = props.pop("orientation", "horizontal")
        default_value = props.pop("default_value", "")

        props["data-slot"] = "tabs"
        props["data-orientation"] = orientation
        props["data-value"] = default_value

        user_on_mount = props.pop("on_mount", None)
        mount_handlers = [rx.call_script(GLOBAL_HANDLERS_JS)]
        if user_on_mount is not None:
            if isinstance(user_on_mount, list):
                mount_handlers.extend(user_on_mount)
            else:
                mount_handlers.append(user_on_mount)
        props["on_mount"] = mount_handlers

        cls.set_class_name(ClassNames.ROOT, props)

        return super().create(*children, **props)


class TabsList(Div, CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> Div:
        variant = props.pop("variant", "default")

        props["data-slot"] = "tabs-list"
        props["data-variant"] = variant

        cls.set_class_name(ClassNames.LIST, props)

        return super().create(*children, **props)


class TabsTrigger(CoreComponent):
    """A clickable tabs navigation button.

    Active-tab highlight is driven entirely by the delegated click listener that
    ``tabs.root`` attaches on mount (see ``components/ui/tabs.py``). The trigger
    itself carries no build-time id or inline JS, so it is safe to render many of
    them from a single ``create()`` call -- including inside ``rx.foreach`` or by
    placing one trigger instance in multiple positions -- without producing
    duplicate DOM ids or baking a per-item ``value`` Var into the JS source.
    """

    @classmethod
    def create(cls, *children: Any, **props: Any) -> rx.Component:
        custom_classes = props.pop("class_name", "")
        value = props.pop("value", "")

        props["data-slot"] = "tabs-trigger"
        props["data-value"] = value
        props["type"] = "button"

        cls.set_class_name(cn(ClassNames.TRIGGER, custom_classes), props)
        return rx.el.button(*children, **props)


class TabsContent(Div, CoreComponent):
    """A single tab panel shown for exactly one trigger value.

    Visibility is driven entirely by ``data-active`` set on the panel by the
    delegated click/mount listener that ``tabs.root`` attaches (see
    ``components/ui/tabs.py``): it reads the root's rendered ``data-value`` and
    the panel's rendered ``data-value`` off the DOM at click/mount time and sets
    ``data-active`` accordingly. The panel carries no build-time class derived
    from its ``value``, so it renders correctly even when built from
    ``rx.foreach`` with ``value=item`` -- a ``Var`` ``value`` never bakes into a
    build-time Tailwind class that the v4 extractor cannot turn into CSS, which
    previously left data-driven panels ``hidden`` forever.
    """

    @classmethod
    def create(cls, *children: Any, **props: Any) -> Div:
        value = props.pop("value", "")

        props["data-slot"] = "tabs-content"
        props["data-value"] = value

        cls.set_class_name(ClassNames.CONTENT, props)

        return super().create(*children, **props)


class Tabs(ComponentNamespace):
    root = staticmethod(TabsRoot.create)
    list = staticmethod(TabsList.create)
    trigger = staticmethod(TabsTrigger.create)
    content = staticmethod(TabsContent.create)
    class_names = ClassNames


tabs = Tabs()
