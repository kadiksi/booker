"""User lifecycle: create on /start, fetch by telegram id."""

from __future__ import annotations

import logging
from typing import Any

from db.client import SupabaseClient, SupabaseError
from services.i18n import norm_lang
from services.user_book_service import UserBookService

logger = logging.getLogger(__name__)


class UserService:
    def __init__(
        self,
        db: SupabaseClient,
        user_book_service: UserBookService,
        legacy_global_sample_book_id: str,
    ) -> None:
        self._db = db
        self._user_books = user_book_service
        self._legacy_global_sample_book_id = legacy_global_sample_book_id

    async def _migrate_legacy_global_sample(self, telegram_id: str) -> None:
        """Старый общий sample-parable больше не используется — сбрасываем текущую книгу."""
        user = await self._db.fetch_user_by_telegram_id(telegram_id)
        if not user or user.get("current_book") != self._legacy_global_sample_book_id:
            return
        legacy = self._legacy_global_sample_book_id
        try:
            await self._db.delete_user_book_row(telegram_id, legacy)
        except SupabaseError:
            logger.exception("Legacy sample user_book delete failed (continuing)")
        await self._db.update_user(telegram_id, {"current_book": None})

    async def ensure_user(
        self,
        telegram_id: str,
        language_code: str | None = None,
    ) -> dict[str, Any]:
        await self._migrate_legacy_global_sample(telegram_id)

        existing = await self._db.fetch_user_by_telegram_id(telegram_id)
        lang_ui = norm_lang(language_code) if language_code else None

        if existing:
            cur = existing.get("current_book")
            if cur:
                b = await self._db.fetch_book(cur)
                if not b or b.get("owner_telegram_id") != telegram_id:
                    existing = await self._db.update_user(telegram_id, {"current_book": None})
                    cur = None
            await self._user_books.ensure_row(telegram_id, cur)
            if lang_ui is not None:
                u = await self._db.fetch_user_by_telegram_id(telegram_id)
                if u and str(u.get("telegram_language_code") or "") != lang_ui:
                    await self._db.update_user(telegram_id, {"telegram_language_code": lang_ui})
            fresh = await self._db.fetch_user_by_telegram_id(telegram_id)
            return fresh or existing

        insert_lang = lang_ui if lang_ui is not None else "en"
        try:
            await self._db.insert_user(
                telegram_id=telegram_id,
                current_book=None,
                utc_offset_minutes=0,
                telegram_language_code=insert_lang,
            )
        except SupabaseError:
            logger.exception("Failed to insert user; retrying fetch")
            existing = await self._db.fetch_user_by_telegram_id(telegram_id)
            if existing:
                await self._migrate_legacy_global_sample(telegram_id)
                await self._user_books.ensure_row(
                    telegram_id,
                    existing.get("current_book"),
                )
                return existing
            raise

        await self._user_books.ensure_row(telegram_id, None)
        user = await self._db.fetch_user_by_telegram_id(telegram_id)
        if not user:
            raise SupabaseError("User row missing after create")
        return user

    async def get_user(self, telegram_id: str) -> dict[str, Any] | None:
        return await self._db.fetch_user_by_telegram_id(telegram_id)
