"""Reading progress and chunk retrieval — uses user_books."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from db.client import SupabaseClient

logger = logging.getLogger(__name__)


def _today() -> date:
    return datetime.now(timezone.utc).date()


class ReadingService:
    """current_position = number of completed chunks (0..N). Next paragraph index is completed+1."""

    def __init__(self, db: SupabaseClient) -> None:
        self._db = db

    async def get_next_chunk_context(self, book_id: str | None, user_book: dict[str, Any] | None) -> dict[str, Any]:
        if not book_id or not user_book:
            return {"error": "no_book"}

        completed = int(user_book.get("current_position") or 0)
        next_position = completed + 1
        chunk = await self._db.fetch_chunk(book_id, next_position)
        if not chunk:
            total = await self._db.count_chunks(book_id)
            return {
                "done": True,
                "total_chunks": total,
                "book_id": book_id,
            }

        return {
            "done": False,
            "chunk": chunk,
            "next_position": next_position,
            "completed_before": completed,
            "book_id": book_id,
        }

    async def record_read(self, telegram_id: str, book_id: str, user_book: dict[str, Any]) -> dict[str, Any]:
        today = _today()
        completed = int(user_book.get("current_position") or 0)

        next_position = completed + 1
        chunk = await self._db.fetch_chunk(book_id, next_position)
        if not chunk:
            return {
                "book_finished": True,
                "current_position": completed,
            }

        updated = await self._db.update_user_book(
            telegram_id,
            book_id,
            {
                "current_position": next_position,
                "last_read_date": today.isoformat(),
            },
        )
        logger.info("Recorded read %s book=%s position=%s", telegram_id, book_id, next_position)
        return {"user_book": updated}
