"""Ограничения Telegram Bot API на длину текста."""

from __future__ import annotations

# https://core.telegram.org/bots/api#sendmessage
TELEGRAM_MAX_MESSAGE_LENGTH = 4096


def split_for_telegram(text: str, limit: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> list[str]:
    """Режет длинный текст на части не длиннее limit, по возможности по абзацам и строкам."""
    t = text.rstrip()
    if not t:
        return []
    if len(t) <= limit:
        return [t]

    out: list[str] = []
    remaining = t
    min_chunk = max(limit // 2, 1)

    while remaining:
        if len(remaining) <= limit:
            out.append(remaining)
            break

        chunk = remaining[:limit]
        split_at = chunk.rfind("\n\n")
        if split_at < min_chunk:
            split_at = chunk.rfind("\n")
        if split_at < min_chunk:
            split_at = chunk.rfind(" ")
        if split_at <= 0:
            split_at = limit

        piece = remaining[:split_at].rstrip()
        if piece:
            out.append(piece)
        remaining = remaining[split_at:].lstrip()
        if not remaining:
            break

    return out
