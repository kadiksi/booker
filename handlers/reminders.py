"""Напоминания: сначала время с телефона при /reminders, затем меню слотов; время слота — одним сообщением."""

from __future__ import annotations

import logging
from typing import TypedDict

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.client import SupabaseClient, SupabaseError
from services.i18n import norm_lang, slot_label, t
from services.reminder_service import (
    SLOT_KEYS_ORDERED,
    list_slot_keys_ordered,
    normalize_time_local,
)
from services.utc_offset_sync import infer_utc_offset_minutes, message_date_to_utc
from services.user_service import UserService

logger = logging.getLogger(__name__)

REM_CFG_PREFIX = "rem:cfg:"
REM_CLEAR_ALL = "rem:clear"


class _ReminderPending(TypedDict, total=False):
    phase: str  # "menu_phone_sync" | "reminder_time"
    slot_key: str


class _PendingReminderFilter(BaseFilter):
    def __init__(self, pending: dict[str, _ReminderPending]) -> None:
        self._pending = pending

    async def __call__(self, message: Message) -> bool:
        if not message.from_user or not message.text:
            return False
        if message.text.startswith("/"):
            return False
        return str(message.from_user.id) in self._pending


def _format_reminders_list(rows: list[dict], lang: str) -> str:
    by_key = {str(r.get("slot_key")): r for r in rows}
    lines = []
    for key in list_slot_keys_ordered():
        label = slot_label(lang, key)
        r = by_key.get(key)
        if r and r.get("enabled", True):
            lines.append(f"• {label}: {r.get('time_local')}")
        else:
            lines.append(f"• {label}: —")
    return t(lang, "reminders_intro") + "\n" + "\n".join(lines)


def build_reminder_router(
    db: SupabaseClient,
    user_service: UserService,
    pending_slots: dict[str, _ReminderPending],
) -> Router:
    router = Router()
    pending_filter = _PendingReminderFilter(pending_slots)

    def _reminder_menu_keyboard(lang: str) -> object:
        kb = InlineKeyboardBuilder()
        for key in list_slot_keys_ordered():
            label = slot_label(lang, key)
            kb.button(text=f"⏰ {label}", callback_data=f"{REM_CFG_PREFIX}{key}")
        kb.button(text=t(lang, "rem_clear_btn"), callback_data=REM_CLEAR_ALL)
        kb.adjust(1)
        return kb.as_markup()

    async def _send_reminder_menu(message: Message, telegram_id: str, lang: str) -> None:
        rows = await db.list_reading_reminders(telegram_id)
        body = _format_reminders_list(rows, lang)
        await message.answer(
            f"{body}\n\n{t(lang, 'reminders_hint')}",
            reply_markup=_reminder_menu_keyboard(lang),
            parse_mode="Markdown",
        )

    @router.message(Command("reminders"))
    async def cmd_reminders(message: Message) -> None:
        if not message.from_user:
            return
        telegram_id = str(message.from_user.id)
        lang = norm_lang(message.from_user.language_code)
        pending_slots.pop(telegram_id, None)
        try:
            await user_service.ensure_user(
                telegram_id,
                message.from_user.language_code if message.from_user else None,
            )
        except SupabaseError:
            logger.exception("cmd_reminders failed")
            await message.answer(t(lang, "err_reminders_load"))
            return

        pending_slots[telegram_id] = {"phase": "menu_phone_sync"}
        await message.answer(t(lang, "rem_menu_ask_phone"), parse_mode="Markdown")

    @router.callback_query(F.data.startswith(REM_CFG_PREFIX))
    async def on_reminder_configure(callback: CallbackQuery) -> None:
        if not callback.from_user or not callback.message or not callback.data:
            await callback.answer()
            return
        lang = norm_lang(callback.from_user.language_code)
        slot_key = callback.data[len(REM_CFG_PREFIX) :]
        if slot_key not in SLOT_KEYS_ORDERED:
            await callback.answer(t(lang, "unknown_slot"), show_alert=True)
            return
        telegram_id = str(callback.from_user.id)
        label = slot_label(lang, slot_key)
        pending_slots[telegram_id] = {"phase": "reminder_time", "slot_key": slot_key}
        await callback.answer()
        await callback.message.answer(t(lang, "rem_slot_time_prompt", label=label), parse_mode="Markdown")

    @router.callback_query(F.data == REM_CLEAR_ALL)
    async def on_reminder_clear_all(callback: CallbackQuery) -> None:
        if not callback.from_user or not callback.message:
            await callback.answer()
            return
        lang = norm_lang(callback.from_user.language_code)
        telegram_id = str(callback.from_user.id)
        pending_slots.pop(telegram_id, None)
        try:
            await db.delete_all_reading_reminders(telegram_id)
        except SupabaseError:
            logger.exception("delete_all_reading_reminders failed")
            await callback.answer(t(lang, "err_clear"), show_alert=True)
            return
        await callback.answer(t(lang, "rem_cleared_toast"))
        await callback.message.answer(t(lang, "rem_cleared_msg"))

    @router.message(pending_filter, F.text)
    async def on_reminder_flow_message(message: Message) -> None:
        if not message.from_user:
            return
        telegram_id = str(message.from_user.id)
        lang = norm_lang(message.from_user.language_code)
        state = pending_slots.get(telegram_id)
        if not state:
            return

        normalized = normalize_time_local(message.text or "")
        if not normalized:
            await message.answer(t(lang, "rem_need_hhmm"))
            return

        phase = state.get("phase")
        slot_key = state.get("slot_key")

        if phase == "menu_phone_sync":
            h, m = int(normalized[:2]), int(normalized[3:5])
            utc_sent = message_date_to_utc(message.date)
            off = infer_utc_offset_minutes(utc_sent, h, m)
            if off is None:
                await message.answer(t(lang, "rem_sync_fail"))
                return
            try:
                await user_service.ensure_user(
                    telegram_id,
                    message.from_user.language_code if message.from_user else None,
                )
                await db.update_user(telegram_id, {"utc_offset_minutes": off})
            except SupabaseError:
                logger.exception("utc_offset update failed")
                await message.answer(t(lang, "rem_save_offset_fail"))
                return

            pending_slots.pop(telegram_id, None)
            try:
                await _send_reminder_menu(message, telegram_id, lang)
            except SupabaseError:
                logger.exception("send reminder menu failed")
                await message.answer(t(lang, "err_reminders_load"))
            return

        if phase == "reminder_time" and slot_key:
            label = slot_label(lang, slot_key)
            pending_slots.pop(telegram_id, None)
            try:
                await user_service.ensure_user(
                    telegram_id,
                    message.from_user.language_code if message.from_user else None,
                )
                await db.upsert_reading_reminder(telegram_id, slot_key, normalized)
            except SupabaseError:
                logger.exception("upsert_reading_reminder failed")
                await message.answer(t(lang, "rem_save_fail"))
                return

            btn = t(lang, "btn_read_next")
            await message.answer(
                t(lang, "rem_saved", label=label, time=normalized, btn=btn),
            )
            return

        pending_slots.pop(telegram_id, None)

    return router
