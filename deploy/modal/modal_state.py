"""STATUS: CURRENT, shared by variants 3 and 4 (state manager used by server_entry.py).

The older variants (modal_app.py, modal_app_asgi.py) are superseded and stopped.
Put new work here.

A Reflex state manager that keeps client state in a Modal Dict.

Reflex ships three state managers: memory, disk and Redis. The disk manager
already has what a long-lived server needs (a per-token lock, an in-memory
cache, debounced write-behind, expiry), and it reaches storage through two
methods: ``load_state`` and ``set_state_for_substate``.
``StateManagerModalDict`` subclasses it and replaces only those two, so locking,
touched-state tracking, substate handling and pickling stay Reflex's own code
(``StateToken.serialize`` and ``StateToken.deserialize``). This is the Modal
counterpart of ``reflex-vercel/blob_state.py``, and it is much smaller because a
Modal Dict is a key-value store, not an object store behind a CDN:

- One key per state, overwritten in place. There are no immutable versions, no
  listing to find the newest, and no clean-up of old versions. Dict reads are not
  served from a CDN cache.
- Expiry is built in: a Dict entry expires after 7 days with no reads or writes.
  Reflex's own token expiration (one hour by default) is shorter, so each entry
  also records when it was saved and a load ignores an entry older than
  ``token_expiration``.
- No separate cache layer. The disk manager already keeps loaded states in
  memory, and Modal Sticky Sessions pin a visitor to one container, so the Dict
  is read once per state after a container start (or a move to another
  container) and then not again.
- Writes go through by default, so a container being replaced loses nothing.
  Raise the debounce to batch writes if the Dict call volume matters more than
  losing the last few seconds.

Not covered, and worth knowing:

- A Dict has no compare-and-set, so two containers saving the same client at once
  are last-writer-wins. Reflex's per-token lock serializes events inside one
  container, and Sticky Sessions keep one visitor on one container, so this only
  matters after a move between containers.
- Values are stored with cloudpickle by the Dict, and the state itself is
  Reflex's pickle bytes. Anyone who can write to the Dict can run code in the
  app, exactly as with the disk and Redis managers, so keep the Dict private to
  the workspace.
- Modal limits a Dict object to 100 MiB and recommends staying under 5 MiB.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import time
from hashlib import md5
from typing import TYPE_CHECKING, Any, Protocol, cast

from reflex.istate.manager.disk import StateManagerDisk
from reflex.state import BaseState
from typing_extensions import override

if TYPE_CHECKING:
    from reflex.istate.manager.token import TOKEN_TYPE, BaseStateToken, StateToken

logger = logging.getLogger(__name__)

PREFIX = "reflex-state/"
# A stored entry is a (saved_at, data) pair.
ENTRY_LENGTH = 2

# What one stored entry holds: when it was saved, and Reflex's serialized state bytes.
Entry = tuple[float, bytes]


class StateKV(Protocol):
    """The three key-value operations the state manager needs. All are async."""

    async def get(self, key: str) -> Entry | None:
        """Return the entry for ``key``, or None if missing."""
        ...

    async def put(self, key: str, entry: Entry) -> None:
        """Store ``entry`` under ``key``, replacing any earlier one."""
        ...

    async def delete(self, key: str) -> None:
        """Remove ``key``; removing a missing key is not an error."""
        ...


class ModalDictKV:
    """``StateKV`` on a ``modal.Dict``. Inside Modal no credentials are needed."""

    def __init__(self, name: str) -> None:
        """Open (and create if needed) the Dict called ``name``."""
        import modal

        self._dict = modal.Dict.from_name(name, create_if_missing=True)

    async def get(self, key: str) -> Entry | None:
        """Read one entry."""
        value = await self._dict.get.aio(key)
        if isinstance(value, tuple) and len(value) == ENTRY_LENGTH:
            return cast("Entry", value)
        return None

    async def put(self, key: str, entry: Entry) -> None:
        """Write one entry."""
        await self._dict.put.aio(key, entry)

    async def delete(self, key: str) -> None:
        """Remove one entry."""
        await self._dict.pop.aio(key, None)


class MemoryKV:
    """``StateKV`` in process memory. Tests and offline development."""

    def __init__(self) -> None:
        """Start empty."""
        self.entries: dict[str, Entry] = {}
        self.calls: list[str] = []

    async def get(self, key: str) -> Entry | None:
        """Read one entry."""
        self.calls.append("get")
        return self.entries.get(key)

    async def put(self, key: str, entry: Entry) -> None:
        """Write one entry."""
        self.calls.append("put")
        self.entries[key] = entry

    async def delete(self, key: str) -> None:
        """Remove one entry."""
        self.calls.append("delete")
        self.entries.pop(key, None)


def state_kv_from_env() -> StateKV | None:
    """Pick a store from ``REFLEX_STATE_DICT``.

    The value is a Dict name, ``memory``, or unset for none.

    ``memory`` is for local tests only; it is not shared between containers.
    """
    name = os.environ.get("REFLEX_STATE_DICT")
    if not name:
        return None
    if name == "memory":
        return MemoryKV()
    return ModalDictKV(name)


@dataclasses.dataclass
class StateManagerModalDict(StateManagerDisk):
    """Disk state manager semantics with a Modal Dict as the disk."""

    store: StateKV = dataclasses.field(default=cast("StateKV", None))

    # Log each load and save at warning level (Modal shows all levels, but this
    # stays greppable).
    debug: bool = False

    @override
    def __post_init__(self) -> None:
        """Skip the parent's local-directory setup; there is no directory."""
        if self.store is None:
            msg = "StateManagerModalDict needs a store"
            raise ValueError(msg)

    @staticmethod
    def _key(token: StateToken[Any]) -> str:
        """Return ``reflex-state/<client hash>/<state hash>``, as Reflex names files."""
        client = md5(token.ident.encode(), usedforsecurity=False).hexdigest()
        state = md5(str(token).encode(), usedforsecurity=False).hexdigest()
        return f"{PREFIX}{client}/{state}"

    @override
    def _purge_expired_states(self) -> None:
        """Nothing to sweep: the Dict expires idle entries and loads skip stale ones."""

    @override
    async def load_state(self, token: StateToken[TOKEN_TYPE]) -> TOKEN_TYPE | None:
        """Load one state, or None if it is missing, expired or unreadable."""
        key = self._key(token)
        try:
            entry = await self.store.get(key)
        except Exception:
            logger.warning("Could not read state from the store", exc_info=True)
            return None
        if entry is None:
            return None
        saved_at, data = entry
        if time.time() - saved_at > self.token_expiration:
            try:
                await self.store.delete(key)
            except Exception:
                logger.debug("Could not delete an expired state", exc_info=True)
            return None
        try:
            state = token.deserialize(data=data)
        except Exception:
            logger.warning("Skipping unreadable stored state %s", key, exc_info=True)
            return None
        if self.debug:
            logger.warning("modal_state load key=%s bytes=%d", key[-8:], len(data))
        return state

    @override
    async def set_state_for_substate(
        self,
        token: StateToken[TOKEN_TYPE],
        substate: TOKEN_TYPE,
    ) -> None:
        """Save a changed (touched) substate, then recurse into its substates."""
        if token.get_and_reset_touched_state(substate):
            data = token.serialize(substate)
            if data:
                key = self._key(token.with_cls(type(substate)))
                await self.store.put(key, (time.time(), data))
                if self.debug:
                    logger.warning(
                        "modal_state save key=%s bytes=%d",
                        key[-8:],
                        len(data),
                    )

        if isinstance(substate, BaseState):
            base_token = cast("BaseStateToken", token)
            for child in substate.substates.values():
                await self.set_state_for_substate(base_token, child)
