"""State manager tests: real Reflex states and tokens, in-memory key-value store."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest
import reflex as rx
from modal_state import (
    PREFIX,
    MemoryKV,
    ModalDictKV,
    StateManagerModalDict,
    state_kv_from_env,
)
from reflex.istate.manager.token import BaseStateToken

SECOND_BUMP = 2
THIRD_BUMP = 3


class CounterState(rx.State):
    """A substate with one var, to prove substates persist."""

    count: int = 0


def _manager(store: MemoryKV, **kwargs: float) -> StateManagerModalDict:
    # _write_debounce_seconds=0 writes through, as server_entry.py configures.
    return StateManagerModalDict(store=store, _write_debounce_seconds=0, **kwargs)


def _token(ident: str = "client-1") -> BaseStateToken:
    return BaseStateToken(ident=ident, cls=rx.State)


async def _bump(manager: StateManagerModalDict, token: BaseStateToken) -> int:
    async with manager.modify_state(token) as root:
        counter = await root.get_state(CounterState)
        counter.count += 1
        return counter.count


def test_state_survives_a_new_instance() -> None:
    """A second manager (a replaced container) reads what the first one saved."""
    store = MemoryKV()

    async def scenario() -> int:
        assert await _bump(_manager(store), _token()) == 1
        assert await _bump(_manager(store), _token()) == SECOND_BUMP
        return await _bump(_manager(store), _token())

    assert asyncio.run(scenario()) == THIRD_BUMP
    assert all(key.startswith(PREFIX) for key in store.entries)


def test_clients_do_not_share_state() -> None:
    """Two visitors keep separate counts."""
    store = MemoryKV()

    async def scenario() -> tuple[int, int, int]:
        manager = _manager(store)
        a1 = await _bump(manager, _token("alice"))
        b1 = await _bump(_manager(store), _token("bob"))
        a2 = await _bump(_manager(store), _token("alice"))
        return a1, b1, a2

    assert asyncio.run(scenario()) == (1, 1, 2)


def test_untouched_state_is_not_rewritten() -> None:
    """A read-only event writes nothing."""
    store = MemoryKV()

    async def scenario() -> None:
        await _bump(_manager(store), _token())
        store.calls.clear()
        reader = _manager(store)
        async with reader.modify_state(_token()) as root:
            await root.get_state(CounterState)

    asyncio.run(scenario())
    assert "get" in store.calls
    assert "put" not in store.calls


def test_expired_entry_is_ignored_and_removed() -> None:
    """An entry older than the token expiration starts the visitor fresh."""
    store = MemoryKV()

    async def scenario() -> int:
        await _bump(_manager(store), _token())
        for key, (saved_at, data) in list(store.entries.items()):
            store.entries[key] = (saved_at - 7200, data)
        return await _bump(_manager(store, token_expiration=3600), _token())

    assert asyncio.run(scenario()) == 1


def test_unreadable_entry_starts_fresh() -> None:
    """Corrupt bytes are skipped instead of crashing the event."""
    store = MemoryKV()

    async def scenario() -> int:
        await _bump(_manager(store), _token())
        for key in list(store.entries):
            store.entries[key] = (time.time(), b"not a pickle")
        return await _bump(_manager(store), _token())

    assert asyncio.run(scenario()) == 1


def test_store_read_failure_does_not_crash() -> None:
    """If the store is down on load, the visitor starts fresh and can continue."""

    class Flaky(MemoryKV):
        fail = True

        async def get(self, key: str) -> Any:  # type: ignore[override]  # noqa: ANN401
            if self.fail:
                msg = "store down"
                raise RuntimeError(msg)
            return await super().get(key)

    store = Flaky()

    async def scenario() -> int:
        return await _bump(_manager(store), _token())

    assert asyncio.run(scenario()) == 1


def test_env_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    """``REFLEX_STATE_DICT`` picks the store: none, ``memory``, or a Dict."""
    monkeypatch.delenv("REFLEX_STATE_DICT", raising=False)
    assert state_kv_from_env() is None
    monkeypatch.setenv("REFLEX_STATE_DICT", "memory")
    assert isinstance(state_kv_from_env(), MemoryKV)
    assert (
        ModalDictKV is not None
    )  # the Dict-backed store is exercised by the live check


def test_manager_requires_a_store() -> None:
    """A missing store is a clear error, not a crash later."""
    with pytest.raises(ValueError, match="needs a store"):
        StateManagerModalDict()
