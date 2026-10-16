"""FastAPI app for the Telegram webhook, health check, and secure forms."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request, Response

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.request_context import new_request_id
from app.core.webhook_guard import HEADER, is_valid_webhook
from app.entrypoints.api.approval import router as approval_router
from app.entrypoints.api.auth import router as auth_router
from app.entrypoints.api.forms import router as forms_router
from app.entrypoints.api.incidents import router as incidents_router
from app.entrypoints.bot.handlers import router as core_router

settings = get_settings()
configure_logging(settings.log_level)
log = get_logger(__name__)
bot = Bot(token=settings.telegram_bot_token.get_secret_value())
dp = Dispatcher()
dp.include_router(core_router)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await bot.set_webhook(
        f"{settings.public_base_url}/telegram/webhook",
        secret_token=settings.telegram_webhook_secret.get_secret_value(),
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
    )
    yield
    await bot.session.close()


app = FastAPI(lifespan=lifespan, docs_url=None if settings.is_prod else "/docs", redoc_url=None)
app.include_router(forms_router)
app.include_router(incidents_router)
app.include_router(auth_router)
app.include_router(approval_router)


@app.middleware("http")
async def request_id_mw(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    rid = new_request_id()
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/telegram/webhook", include_in_schema=False)
async def telegram_webhook(
    request: Request,
    secret: str | None = Header(default=None, alias=HEADER),
) -> Response:
    if not is_valid_webhook(secret, settings.telegram_webhook_secret.get_secret_value()):
        log.warning("webhook.rejected", client=request.client.host if request.client else None)
        raise HTTPException(status_code=403)
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return Response(status_code=200)
