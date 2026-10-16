from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.db import unit_of_work
from app.core.telegram_init_data import InvalidInitData, validate_init_data
from app.modules.identity.onboarding import telegram_register

router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramInitDataBody(BaseModel):
    init_data: str = Field(min_length=1, max_length=8192)


@router.post("/telegram/register", status_code=202)
async def register_telegram(body: TelegramInitDataBody) -> dict[str, str]:
    """Only signed Telegram Mini App initData may create a pending registration."""
    settings = get_settings()
    try:
        identity = validate_init_data(
            body.init_data,
            bot_token=settings.telegram_bot_token.get_secret_value(),
        )
    except InvalidInitData as exc:
        raise HTTPException(status_code=401, detail="invalid Telegram identity proof") from exc
    async with unit_of_work() as session:
        dto = await telegram_register(
            session, telegram_user_id=identity.user_id, full_name=identity.first_name
        )
    return {"status": dto.status, "message": "registration pending approval"}
