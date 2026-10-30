"""Tailwind class merging: `cn()` built on `clsx` and `tailwind-merge`.

Both are MIT-licensed. Do not use `clsx-for-tailwind` (AGPL-3.0).
"""

from __future__ import annotations

from reflex.utils.imports import ImportVar
from reflex.vars import FunctionStringVar, Var, VarData

# package_path is set to "" explicitly; the default "/" makes Reflex emit a
# malformed slash-suffixed import path (buridan-ui#63, #73).
_clsx = FunctionStringVar.create(
    "clsx",
    _var_data=VarData(
        imports={"clsx": [ImportVar(tag="clsx", is_default=True, package_path="")]},
    ),
)
_twmerge = FunctionStringVar.create(
    "twMerge",
    _var_data=VarData(
        imports={"tailwind-merge": [ImportVar(tag="twMerge", package_path="")]},
    ),
)


def cn(*args: Var[str] | str) -> Var[str]:
    """Join class names with `clsx`, then resolve Tailwind conflicts with `twMerge`."""
    return _twmerge(_clsx(*args)).to(str)
