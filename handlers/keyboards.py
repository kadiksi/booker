"""Shared inline keyboards (single source for callback payloads)."""

from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.i18n import norm_lang, t

NAV_READ = "nav:read"


def reading_keyboard(language_code: str | None = None) -> object:
    lang = norm_lang(language_code)
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "btn_read_next"), callback_data=NAV_READ)
    return kb.as_markup()
