import reflex as rx
from reflex.plugins.sitemap import SitemapPlugin

config = rx.Config(
    app_name="web",
    plugins=[SitemapPlugin(), rx.plugins.RadixThemesPlugin()],
    show_built_with_reflex=False,
)
