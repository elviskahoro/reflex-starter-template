"""Reflex framework configuration."""

import reflex as rx
from reflex.plugins.sitemap import SitemapPlugin

config = rx.Config(
    app_name="web",
    plugins=[SitemapPlugin(), rx.plugins.TailwindV4Plugin()],
    show_built_with_reflex=False,
    telemetry_enabled=False,
)
