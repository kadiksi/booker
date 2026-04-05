"""Telegram bot entrypoint: long-polling, structured logging, graceful shutdown."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError
from config import get_settings
from db.client import SupabaseClient
from handlers import build_router
from services import BookParserService, BookService, ReadingService, UserBookService, UserService
from services.i18n import register_localized_commands
from services.reminder_service import tick_scheduled_reminders

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    db = SupabaseClient(settings.supabase_url, settings.supabase_key)
    book_service = BookService(db)
    user_book_service = UserBookService(db)
    user_service = UserService(
        db,
        user_book_service,
        book_service,
        settings.sample_book_id,
    )
    reading_service = ReadingService(db)
    book_parser = BookParserService()

    reminder_pending_slots: dict[str, dict] = {}

    dp.include_router(
        build_router(
            db,
            user_service,
            user_book_service,
            reading_service,
            book_service,
            book_parser,
            settings.max_upload_bytes,
            reminder_pending_slots,
        )
    )

    async def reminder_loop() -> None:
        while True:
            await asyncio.sleep(30)
            try:
                await tick_scheduled_reminders(bot, db)
            except Exception:
                logger.exception("reminder tick failed")

    reminder_task = asyncio.create_task(reminder_loop())

    try:
        await register_localized_commands(bot)
        logger.info("Bot starting (long polling)")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except TelegramNetworkError:
        logger.exception("Telegram network error")
        raise
    finally:
        reminder_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reminder_task
        await db.aclose()
        await bot.session.close()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
