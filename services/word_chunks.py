"""Один шаг чтения = один абзац = одно сообщение в Telegram; длинные абзацы режутся по лимиту длины."""

from __future__ import annotations

from services.telegram_text import split_for_telegram


def normalize_paragraph_text(text: str) -> str:
    """Убирает пустые строки по краям и хвостовые пробелы строк; красная строка и внутренние \\n сохраняются."""
    lines = [ln.rstrip() for ln in str(text).splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return "\n".join(lines)


def _normalize_paragraph_list(paragraphs: list[str]) -> list[str]:
    out: list[str] = []
    for p in paragraphs:
        t = normalize_paragraph_text(p)
        if t:
            out.append(t)
    return out


def to_reading_chunks(paragraphs: list[str]) -> list[str]:
    """
    По одному чанку на абзац; если абзац длиннее лимита Telegram — несколько чанков подряд
    (каждый всё равно одно сообщение и один шаг «Дальше»).
    """
    normalized = _normalize_paragraph_list(paragraphs)
    if not normalized:
        return []

    out: list[str] = []
    for p in normalized:
        parts = split_for_telegram(p)
        out.extend(parts)
    return out
