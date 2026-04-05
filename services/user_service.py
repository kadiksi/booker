"""User lifecycle: create on /start, fetch by telegram id."""

from __future__ import annotations

import logging
from typing import Any

from db.client import SupabaseClient, SupabaseError
from services.book_service import BookService, personal_default_book_id
from services.user_book_service import UserBookService

logger = logging.getLogger(__name__)


class UserService:
    def __init__(
        self,
        db: SupabaseClient,
        user_book_service: UserBookService,
        book_service: BookService,
        legacy_global_sample_book_id: str,
    ) -> None:
        self._db = db
        self._user_books = user_book_service
        self._book_service = book_service
        self._legacy_global_sample_book_id = legacy_global_sample_book_id

    async def _migrate_legacy_global_sample(self, telegram_id: str, new_book_id: str) -> None:
        user = await self._db.fetch_user_by_telegram_id(telegram_id)
        if not user or user.get("current_book") != self._legacy_global_sample_book_id:
            return
        legacy = self._legacy_global_sample_book_id
        old_ub = await self._db.fetch_user_book(telegram_id, legacy)
        await self._db.update_user(telegram_id, {"current_book": new_book_id})
        if old_ub:
            await self._db.delete_user_book_row(telegram_id, legacy)
            await self._db.insert_user_book(
                telegram_id,
                new_book_id,
                int(old_ub.get("current_position") or 0),
                str(old_ub["last_read_date"])[:10] if old_ub.get("last_read_date") else None,
            )

    async def ensure_user(self, telegram_id: str) -> dict[str, Any]:
        bid = personal_default_book_id(telegram_id)
        await self._book_service.ensure_default_book_for_user(telegram_id, bid)
        await self._migrate_legacy_global_sample(telegram_id, bid)

        existing = await self._db.fetch_user_by_telegram_id(telegram_id)

        if existing:
            if not existing.get("current_book"):
                existing = await self._db.update_user(telegram_id, {"current_book": bid})
            cur = existing.get("current_book")
            if cur:
                b = await self._db.fetch_book(cur)
                if not b or b.get("owner_telegram_id") != telegram_id:
                    existing = await self._db.update_user(telegram_id, {"current_book": bid})
                    cur = bid
            await self._user_books.ensure_row(telegram_id, cur)
            fresh = await self._db.fetch_user_by_telegram_id(telegram_id)
            return fresh or existing

        try:
            await self._db.insert_user(telegram_id=telegram_id, current_book=bid)
        except SupabaseError:
            logger.exception("Failed to insert user; retrying fetch")
            existing = await self._db.fetch_user_by_telegram_id(telegram_id)
            if existing:
                await self._migrate_legacy_global_sample(telegram_id, bid)
                await self._user_books.ensure_row(
                    telegram_id,
                    existing.get("current_book") or bid,
                )
                return existing
            raise

        await self._user_books.ensure_row(telegram_id, bid)
        user = await self._db.fetch_user_by_telegram_id(telegram_id)
        if not user:
            raise SupabaseError("User row missing after create")
        return user

    async def get_user(self, telegram_id: str) -> dict[str, Any] | None:
        return await self._db.fetch_user_by_telegram_id(telegram_id)
