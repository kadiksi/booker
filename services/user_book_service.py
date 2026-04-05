"""Per-user, per-book progress rows (user_books)."""

from __future__ import annotations

import logging
from typing import Any

from db.client import SupabaseClient, SupabaseError

logger = logging.getLogger(__name__)


class UserBookService:
    def __init__(self, db: SupabaseClient) -> None:
        self._db = db

    async def ensure_row(self, telegram_id: str, book_id: str | None) -> dict[str, Any] | None:
        if not book_id:
            return None
        row = await self._db.fetch_user_book(telegram_id, book_id)
        if row:
            return row
        try:
            return await self._db.insert_user_book(telegram_id, book_id, 0, None)
        except SupabaseError:
            logger.exception("insert_user_book race; refetching")
            row = await self._db.fetch_user_book(telegram_id, book_id)
            if row:
                return row
            raise

    async def switch_current_book(self, telegram_id: str, book_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        await self._db.update_user(telegram_id, {"current_book": book_id})
        ub = await self.ensure_row(telegram_id, book_id)
        if not ub:
            raise SupabaseError("Could not open book progress")
        user = await self._db.fetch_user_by_telegram_id(telegram_id)
        if not user:
            raise SupabaseError("User missing after book switch")
        return user, ub
