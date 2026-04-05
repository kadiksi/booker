"""User lifecycle: create on /start, fetch by telegram id."""

from __future__ import annotations

import logging
from typing import Any

from db.client import SupabaseClient, SupabaseError
from services.user_book_service import UserBookService

logger = logging.getLogger(__name__)


class UserService:
    def __init__(
        self,
        db: SupabaseClient,
        default_book_id: str,
        user_book_service: UserBookService,
    ) -> None:
        self._db = db
        self._default_book_id = default_book_id
        self._user_books = user_book_service

    async def ensure_user(self, telegram_id: str) -> dict[str, Any]:
        existing = await self._db.fetch_user_by_telegram_id(telegram_id)
        book_id = self._default_book_id

        if existing:
            if not existing.get("current_book"):
                existing = await self._db.update_user(
                    telegram_id,
                    {"current_book": book_id},
                )
            bid = existing.get("current_book")
            await self._user_books.ensure_row(telegram_id, bid)
            fresh = await self._db.fetch_user_by_telegram_id(telegram_id)
            return fresh or existing

        try:
            await self._db.insert_user(telegram_id=telegram_id, current_book=book_id)
        except SupabaseError:
            logger.exception("Failed to insert user; retrying fetch")
            existing = await self._db.fetch_user_by_telegram_id(telegram_id)
            if existing:
                await self._user_books.ensure_row(
                    telegram_id,
                    existing.get("current_book") or book_id,
                )
                return existing
            raise

        await self._user_books.ensure_row(telegram_id, book_id)
        user = await self._db.fetch_user_by_telegram_id(telegram_id)
        if not user:
            raise SupabaseError("User row missing after create")
        return user

    async def get_user(self, telegram_id: str) -> dict[str, Any] | None:
        return await self._db.fetch_user_by_telegram_id(telegram_id)
