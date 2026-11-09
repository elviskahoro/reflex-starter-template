from typing import Any

import reflex as rx
from reflex.components.component import ComponentNamespace
from reflex_components_core.el import Div, Span

from ..core.core import CoreComponent


class ClassNames:
    ROOT = (
        "group/avatar relative flex size-8 shrink-0 rounded-full select-none "
        "after:absolute after:inset-0 after:rounded-full after:border after:border-border "
        "after:mix-blend-darken data-[size=xl]:size-14 data-[size=lg]:size-10 "
        "data-[size=sm]:size-6 dark:after:mix-blend-lighten"
    )
    IMAGE = "aspect-square size-full rounded-full object-cover"
    FALLBACK = (
        "flex size-full items-center justify-center rounded-full bg-muted text-sm "
        "text-muted-foreground group-data-[size=sm]/avatar:text-xs"
    )
    BADGE = (
        "absolute right-0 bottom-0 z-10 inline-flex items-center justify-center "
        "rounded-full bg-primary text-primary-foreground bg-blend-color "
        "ring-2 ring-background select-none "
        "group-data-[size=sm]/avatar:size-2 group-data-[size=sm]/avatar:[&>svg]:hidden "
        "group-data-[size=default]/avatar:size-2.5 group-data-[size=default]/avatar:[&>svg]:size-2 "
        "group-data-[size=lg]/avatar:size-3 group-data-[size=lg]/avatar:[&>svg]:size-2"
    )
    GROUP = (
        "group/avatar-group flex -space-x-2 "
        "*:data-[slot=avatar]:ring-2 *:data-[slot=avatar]:ring-background"
    )
    GROUP_COUNT = (
        "relative flex size-8 shrink-0 items-center justify-center rounded-full "
        "bg-muted text-sm text-muted-foreground ring-2 ring-background "
        "group-has-data-[size=lg]/avatar-group:size-10 "
        "group-has-data-[size=sm]/avatar-group:size-6 "
        "[&>svg]:size-4 group-has-data-[size=lg]/avatar-group:[&>svg]:size-5 "
        "group-has-data-[size=sm]/avatar-group:[&>svg]:size-3"
    )


PROBE_IMAGES_JS = """
(function () {
    document.querySelectorAll('[data-slot="avatar-image"]').forEach(function (img) {
        var root = img.closest('[data-slot="avatar"]');
        var fallback = root
            ? root.querySelector('[data-slot="avatar-fallback"]')
            : null;
        var tester = new Image();
        tester.onload = function () {
            img.style.display = '';
            if (fallback) fallback.style.display = 'none';
        };
        tester.onerror = function () {
            img.style.display = 'none';
            if (fallback) fallback.style.display = 'flex';
        };
        tester.src = img.getAttribute('src') || '';
    });
})();
"""


class AvatarRoot(Div, CoreComponent):
    """Avatar container; probes its images on mount.

    The probe reads each image's rendered ``src`` from the DOM instead of baking
    a build-time id/``src`` into per-image JS, so it stays correct when avatars
    are rendered via ``rx.foreach``.
    """

    @classmethod
    def create(cls, *children: Any, **props: Any) -> Div:
        size = props.pop("size", "default")
        props["data-slot"] = "avatar"
        props["data-size"] = size

        user_on_mount = props.pop("on_mount", None)
        mount_handlers = [rx.call_script(PROBE_IMAGES_JS)]
        if user_on_mount is not None:
            if isinstance(user_on_mount, list):
                mount_handlers.extend(user_on_mount)
            else:
                mount_handlers.append(user_on_mount)
        props["on_mount"] = mount_handlers

        cls.set_class_name(ClassNames.ROOT, props)
        return super().create(*children, **props)


def avatar_image(**props: Any) -> rx.Component:
    props["data-slot"] = "avatar-image"

    user_on_mount = props.pop("on_mount", None)
    mount_handlers = [rx.call_script(PROBE_IMAGES_JS)]
    if user_on_mount is not None:
        if isinstance(user_on_mount, list):
            mount_handlers.extend(user_on_mount)
        else:
            mount_handlers.append(user_on_mount)
    props["on_mount"] = mount_handlers

    CoreComponent.set_class_name(ClassNames.IMAGE, props)
    return rx.el.img(**props)


class AvatarFallback(Span, CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> Span:
        props["data-slot"] = "avatar-fallback"
        props["style"] = {"display": "none", **props.get("style", {})}
        cls.set_class_name(ClassNames.FALLBACK, props)
        return super().create(*children, **props)


class AvatarBadge(Span, CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> Span:
        props["data-slot"] = "avatar-badge"
        cls.set_class_name(ClassNames.BADGE, props)
        return super().create(*children, **props)


class AvatarGroup(Div, CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> Div:
        props["data-slot"] = "avatar-group"
        cls.set_class_name(ClassNames.GROUP, props)
        return super().create(*children, **props)


class AvatarGroupCount(Div, CoreComponent):
    @classmethod
    def create(cls, *children: Any, **props: Any) -> Div:
        props["data-slot"] = "avatar-group-count"
        cls.set_class_name(ClassNames.GROUP_COUNT, props)
        return super().create(*children, **props)


class Avatar(ComponentNamespace):
    root = staticmethod(AvatarRoot.create)
    image = staticmethod(avatar_image)
    fallback = staticmethod(AvatarFallback.create)
    badge = staticmethod(AvatarBadge.create)
    group = staticmethod(AvatarGroup.create)
    group_count = staticmethod(AvatarGroupCount.create)
    class_names = ClassNames


avatar = Avatar()
