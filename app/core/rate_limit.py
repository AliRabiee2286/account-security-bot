"""S-005: fixed-window rate limit in Redis, per user and per action."""

from __future__ import annotations

from typing import Protocol

from app.core.errors import RateLimited


class _Redis(Protocol):
    async def incr(self, key: str) -> int: ...
    async def expire(self, key: str, seconds: int) -> bool: ...


async def hit(redis: _Redis, *, subject: str, action: str, limit: int, window_s: int) -> None:
    key = f"rl:{action}:{subject}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window_s)
    if count > limit:
        raise RateLimited(action, subject=subject, count=count)
