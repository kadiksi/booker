#!/usr/bin/env python3
"""One-off: preload the sample book into Supabase. Run after applying schema.sql."""

from __future__ import annotations

import asyncio
import logging
import sys

from config import get_settings
from db.client import SupabaseClient
from services.book_seed import preload_sample_book

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)


async def _run() -> None:
    settings = get_settings()
    db = SupabaseClient(settings.supabase_url, settings.supabase_key)
    try:
        summary = await preload_sample_book(db, settings.sample_book_id)
        logger.info("Done: %s", summary)
    finally:
        await db.aclose()


if __name__ == "__main__":
    asyncio.run(_run())
