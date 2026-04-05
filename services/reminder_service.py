"""Local-time reading nudges: normalize HH:MM, fire once per local day per slot."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from db.client import SupabaseClient
from services.i18n import norm_lang, slot_label, t

logger = logging.getLogger(__name__)

SLOT_KEYS_ORDERED = ("morning_commute", "lunch", "evening_commute", "before_sleep")

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def normalize_time_local(raw: str) -> str | None:
    text = raw.strip()
    m = _TIME_RE.match(text)
    if not m:
        return None
    h, mn = int(m.group(1)), int(m.group(2))
    return f"{h:02d}:{mn:02d}"


def list_slot_keys_ordered() -> list[str]:
    return list(SLOT_KEYS_ORDERED)


def _user_local_hm_today(now_utc: datetime, offset_minutes: int) -> tuple[str, str]:
    adj = now_utc + timedelta(minutes=offset_minutes)
    return f"{adj.hour:02d}:{adj.minute:02d}", adj.date().isoformat()


async def tick_scheduled_reminders(bot: Bot, db: SupabaseClient) -> None:
    from handlers.keyboards import reading_keyboard

    rows = await db.list_enabled_reminders_for_scheduler()
    if not rows:
        return

    uids = list({str(r["telegram_id"]) for r in rows})
    uctx = await db.fetch_users_reminder_context(uids)
    now_utc = datetime.now(timezone.utc)

    for row in rows:
        tid = str(row["telegram_id"])
        ctx = uctx.get(tid) or {}
        off = int(ctx.get("utc_offset_minutes") or 0)
        lang = norm_lang(str(ctx.get("telegram_language_code") or "en"))

        hm, today = _user_local_hm_today(now_utc, off)
        if hm != str(row.get("time_local") or ""):
            continue

        lnd = row.get("last_notified_date")
        if lnd is not None and str(lnd)[:10] == today:
            continue

        slot_key = str(row.get("slot_key") or "")
        label = slot_label(lang, slot_key) if slot_key in SLOT_KEYS_ORDERED else slot_key
        text = t(lang, "rem_tick", hm=hm, label=label) + t(lang, "rem_tick_note")

        try:
            chat_id = int(tid)
            await bot.send_message(chat_id, text, reply_markup=reading_keyboard(lang))
            await db.patch_reading_reminder_last_notified(str(row["id"]), today)
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.warning("Reminder send failed for %s: %s", tid, e)
        except Exception:
            logger.exception("Reminder send unexpected error for %s", tid)
