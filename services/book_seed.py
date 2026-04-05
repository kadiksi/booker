"""Load the bundled sample book into Supabase (idempotent for chunks)."""

from __future__ import annotations

import logging
import re
from typing import Any

from db.client import SupabaseClient, SupabaseError
from services.word_chunks import to_reading_chunks

logger = logging.getLogger(__name__)

# Short original prose; split into paragraphs for chunking (>= 20 chunks).
_SAMPLE_MARKDOWN = """
The lighthouse keeper woke before dawn.

Each morning the same gray light slid through the shutters.

He made tea and listened to the kettle argue with itself.

Outside, the sea rearranged stones the way others rearrange words.

On the cliff path, gulls practiced their sharp opinions.

He checked the lamp the way some people check a pulse.

The lens was a circle of disciplined fire waiting for night.

Midday brought tourists who waved from boats like friendly punctuation.

He waved back, smaller, a comma against the horizon.

In the logbook he wrote wind speed like a line of quiet poetry.

Afternoon light leaned on the railing until the metal grew warm.

He read one chapter of a book he had started years ago.

The chapter refused to end; it had learned patience from the waves.

At dusk the horizon drew a thin silver thread through the sky.

He climbed the spiral stairs, counting steps without meaning to.

The lamp woke, shy at first, then certain.

Somewhere a ship changed its mind about fear.

He thought about streaks—not of fire, but of days kept honest.

A streak, he decided, is a promise you repeat until it becomes a path.

If you miss a day, the path does not vanish; it waits, silent.

But a promise grown cold must be kindled again from one flame.

When the first star appeared, it looked like a distant yes.

He opened the window a crack and listened for the tide’s verdict.

Night pressed against the glass, softened by the beam above.

Before sleep he set one cup for morning, an ordinary altar.

He whispered thanks to no one in particular, which was enough.

The dark hours passed, faithful and indifferent.

When dawn returned, the cycle hesitated at the threshold—then began again.

Tomorrow he would polish the brass until it laughed softly in reply.

The sea kept its vast appointment with the shore, indifferent and kind.
"""


def _paragraphs() -> list[str]:
    raw = [p.strip() for p in re.split(r"\n\s*\n", _SAMPLE_MARKDOWN.strip()) if p.strip()]
    if len(raw) < 20:
        raise RuntimeError("Sample book must contain at least 20 paragraphs")
    return raw


async def preload_sample_book(
    db: SupabaseClient,
    book_id: str,
    title: str | None = None,
    owner_telegram_id: str | None = None,
) -> dict[str, Any]:
    """
    Загрузка примера в БД (для ручного seed). Укажите owner_telegram_id — иначе книга не попадёт в /users.
    """
    if not title:
        title = "The Lighthouse Keeper (sample)"

    paragraphs = _paragraphs()
    merged = to_reading_chunks(paragraphs)
    try:
        await db.upsert_book(book_id, title, owner_telegram_id)
        await db.delete_chunks_for_book(book_id)
        rows = [{"book_id": book_id, "position": i + 1, "content": text} for i, text in enumerate(merged)]
        await db.insert_chunks_bulk(rows)
    except SupabaseError:
        logger.exception("Failed to preload sample book")
        raise

    logger.info("Preloaded book %s with %s chunks", book_id, len(merged))
    return {"book_id": book_id, "title": title, "chunks": len(merged)}
