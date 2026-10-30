"""`cn()` renders twMerge(clsx(...)) with the expected JS expression."""

from __future__ import annotations

from web.components.ui import cn


def test_cn_wraps_clsx_in_twmerge() -> None:
    assert str(cn("p-2", "p-4")) == '(twMerge((clsx("p-2", "p-4"))))'
