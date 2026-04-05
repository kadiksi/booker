"""Create and list books in Supabase."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from db.client import SupabaseClient, SupabaseError
from services.word_chunks import to_reading_chunks

logger = logging.getLogger(__name__)


async def create_book_with_chunks(
    db: SupabaseClient,
    title: str,
    paragraphs: list[str],
    book_id: str | None = None,
    owner_telegram_id: str | None = None,
) -> dict[str, Any]:
    if not paragraphs:
        raise SupabaseError("No paragraphs to store")

    merged = to_reading_chunks(paragraphs)
    if not merged:
        raise SupabaseError("No paragraphs to store")

    if not book_id:
        book_id = f"u-{uuid.uuid4().hex[:12]}"

    safe_title = title.strip() or "Untitled"
    await db.upsert_book(book_id, safe_title, owner_telegram_id)
    await db.delete_chunks_for_book(book_id)
    rows = [{"book_id": book_id, "position": i + 1, "content": text} for i, text in enumerate(merged)]
    await db.insert_chunks_bulk(rows)
    logger.info("Created book %s for owner=%s (%s chunks)", book_id, owner_telegram_id, len(rows))
    return {"id": book_id, "title": safe_title, "chunks": len(rows)}


class BookService:
    def __init__(self, db: SupabaseClient) -> None:
        self._db = db

    async def get_book(self, book_id: str) -> dict[str, Any] | None:
        return await self._db.fetch_book(book_id)

    async def list_books_for_user(self, telegram_id: str) -> list[dict[str, Any]]:
        return await self._db.list_books_for_owner(telegram_id)

    async def create_from_paragraphs(
        self,
        title: str,
        paragraphs: list[str],
        owner_telegram_id: str,
        preferred_id: str | None = None,
    ) -> dict[str, Any]:
        return await create_book_with_chunks(
            self._db,
            title,
            paragraphs,
            preferred_id,
            owner_telegram_id,
        )
