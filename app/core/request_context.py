"""Request ID propagated across bot handler -> service -> worker -> external API calls."""

from __future__ import annotations

from contextvars import ContextVar

from app.core.ids import uuid7

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_actor: ContextVar[str | None] = ContextVar("actor", default=None)


def new_request_id() -> str:
    rid = uuid7().hex
    _request_id.set(rid)
    return rid


def set_request_id(rid: str) -> None:
    _request_id.set(rid)


def get_request_id() -> str:
    rid = _request_id.get()
    return rid if rid is not None else new_request_id()


def set_actor(actor: str | None) -> None:
    _actor.set(actor)


def get_actor() -> str | None:
    return _actor.get()
