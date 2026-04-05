"""Вычисление смещения от UTC (минуты) по моменту сообщения и показаниям часов на телефоне."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def message_date_to_utc(message_date: datetime) -> datetime:
    if message_date.tzinfo is None:
        return message_date.replace(tzinfo=timezone.utc)
    return message_date.astimezone(timezone.utc)


def infer_utc_offset_minutes(sent_utc: datetime, hour: int, minute: int) -> int | None:
    """Подобрать off так, что (sent_utc + off) даёт тот же ЧЧ:ММ, что на телефоне (фиксированный оффсет)."""
    sent_utc = sent_utc.astimezone(timezone.utc)
    matches: list[int] = []
    for off in range(-14 * 60, 15 * 60):
        adj = sent_utc + timedelta(minutes=off)
        if adj.hour == hour and adj.minute == minute:
            matches.append(off)
    if not matches:
        return None
    return min(matches, key=abs)
