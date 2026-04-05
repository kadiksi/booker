#!/usr/bin/env python3
"""Опционально: загрузить демо-книгу для одного telegram id (как в боте: id = d-<id>)."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from config import get_settings
from db.client import SupabaseClient
from services.book_seed import preload_sample_book
from services.book_service import personal_default_book_id

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)


async def _run() -> None:
    owner = (os.getenv("SEED_TELEGRAM_ID") or (sys.argv[1] if len(sys.argv) > 1 else "")).strip()
    if not owner:
        logger.error(
            "Укажите Telegram user id: SEED_TELEGRAM_ID=... или python run_seed.py <telegram_id>"
        )
        sys.exit(1)
    settings = get_settings()
    db = SupabaseClient(settings.supabase_url, settings.supabase_key)
    book_id = personal_default_book_id(owner)
    try:
        summary = await preload_sample_book(db, book_id, owner_telegram_id=owner)
        logger.info("Done: %s", summary)
    finally:
        await db.aclose()


if __name__ == "__main__":
    asyncio.run(_run())
