"""Official social API adapter contract. No scraper and no automated login."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, TypeVar


@dataclass(frozen=True)
class SocialPost:
    provider_id: str
    author_handle: str
    text: str
    published_at: datetime
    media_urls: tuple[str, ...] = ()


class SocialProvider(Protocol):
    code: str

    async def recent_posts(
        self, *, access_token: str, provider_user_id: str, limit: int = 25
    ) -> list[SocialPost]: ...
    async def remove_owned_post(self, *, access_token: str, provider_post_id: str) -> bool: ...
    async def revoke(self, *, access_token: str) -> None: ...


_REGISTRY: dict[str, type[SocialProvider]] = {}

ProviderT = TypeVar("ProviderT", bound=SocialProvider)


def register(code: str) -> Callable[[type[ProviderT]], type[ProviderT]]:
    def deco(cls: type[ProviderT]) -> type[ProviderT]:
        _REGISTRY[code] = cls
        return cls

    return deco
