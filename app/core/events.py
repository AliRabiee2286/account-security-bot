"""D-009 rule 3: in-process domain event bus. Modules publish facts; others subscribe.

Events that trigger external side effects must ALSO be written to the outbox table in the
same DB transaction (see app.core.outbox) so nothing is lost on crash.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar

from app.core.ids import uuid7
from app.core.request_context import get_request_id


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    name: ClassVar[str] = "domain_event"
    event_id: str = field(default_factory=lambda: uuid7().hex)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    request_id: str = field(default_factory=get_request_id)


Handler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        # Handlers run sequentially and errors propagate: an in-process subscriber failing
        # is a bug and must roll back the surrounding transaction.
        for handler in self._handlers.get(type(event), []):
            await handler(event)


bus = EventBus()
