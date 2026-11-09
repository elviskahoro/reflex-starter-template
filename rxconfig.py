"""Reflex framework configuration."""

import reflex as rx
from reflex.plugins.sitemap import SitemapPlugin

config = rx.Config(
    app_name="web",
    plugins=[SitemapPlugin(), rx.plugins.TailwindV4Plugin()],
    # Feeds reflex's inline pre-paint script (same 'theme' localStorage key
    # and light/dark classes the theme toggle uses); dark-first, no flash.
    default_color_mode="dark",
    show_built_with_reflex=False,
    telemetry_enabled=False,
)
