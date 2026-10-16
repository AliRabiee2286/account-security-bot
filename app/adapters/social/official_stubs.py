"""Provider capability matrix encoded as explicit safe defaults.

Instagram: Professional accounts can be read; feed post/story deletion is not supported by
current documented API, so remove_owned_post returns False and incident flow becomes manual.
X: owned post deletion is supported with user OAuth write scope.
Telegram Bot: only bot-managed chat messages are in scope, never personal user posts/stories.
"""

from __future__ import annotations

from app.adapters.social.base import SocialPost, register


@register("instagram")
class InstagramProvider:
    code = "instagram"

    async def recent_posts(
        self, *, access_token: str, provider_user_id: str, limit: int = 25
    ) -> list[SocialPost]:
        raise NotImplementedError("Phase 4: official Instagram Graph API client")

    async def remove_owned_post(self, *, access_token: str, provider_post_id: str) -> bool:
        return False

    async def revoke(self, *, access_token: str) -> None:
        raise NotImplementedError("Phase 4: official token revocation")


@register("x")
class XProvider:
    code = "x"

    async def recent_posts(
        self, *, access_token: str, provider_user_id: str, limit: int = 25
    ) -> list[SocialPost]:
        raise NotImplementedError("Phase 4: official X API v2 client")

    async def remove_owned_post(self, *, access_token: str, provider_post_id: str) -> bool:
        raise NotImplementedError("Phase 4: official X API v2 client")

    async def revoke(self, *, access_token: str) -> None:
        raise NotImplementedError("Phase 4: official token revocation")


@register("telegram")
class TelegramBotProvider:
    code = "telegram"

    async def recent_posts(
        self, *, access_token: str, provider_user_id: str, limit: int = 25
    ) -> list[SocialPost]:
        raise NotImplementedError("Only bot-managed chats are supported, not personal accounts")

    async def remove_owned_post(self, *, access_token: str, provider_post_id: str) -> bool:
        return False

    async def revoke(self, *, access_token: str) -> None:
        return None
