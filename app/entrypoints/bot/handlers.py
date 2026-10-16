"""Thin handlers: parse input -> call module api -> render text. No business logic, no DB."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from app.core.db import unit_of_work
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.request_context import set_actor
from app.entrypoints.bot import texts
from app.modules.identity import api as identity

router = Router(name="core")
log = get_logger(__name__)


@router.message(CommandStart())
async def start(message: Message) -> None:
    if message.from_user is None:
        return
    set_actor(f"tg:{message.from_user.id}")
    async with unit_of_work() as s:
        emp = await identity.find_active_by_telegram(s, message.from_user.id)
    await message.answer(texts.WELCOME.format(name=emp.full_name) if emp else texts.ASK_NAME)


@router.message(Command("register"))
async def register(message: Message, command: CommandObject) -> None:
    if message.from_user is None:
        return
    try:
        req = identity.RegisterRequest(
            telegram_user_id=message.from_user.id, full_name=(command.args or "").strip()
        )
        async with unit_of_work() as s:
            await identity.register(s, req)
        await message.answer(texts.PENDING)
    except AppError as e:
        await message.answer(e.user_message)
    except ValueError:
        await message.answer(texts.ASK_NAME)


@router.message()
async def fallback(message: Message) -> None:
    # Never echo, never reveal whether the user exists (S-005).
    await message.answer(texts.NEVER_SEND_SECRETS)
