"""Telegram bot entrypoint: long-polling, structured logging, graceful shutdown."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import BotCommand

from config import get_settings
from db.client import SupabaseClient
from handlers import build_router
from services import BookParserService, BookService, ReadingService, UserBookService, UserService

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
    user_book_service = UserBookService(db)
    user_service = UserService(db, settings.sample_book_id, user_book_service)
    reading_service = ReadingService(db)
    book_service = BookService(db)
    book_parser = BookParserService()

    dp.include_router(
        build_router(
            user_service,
            user_book_service,
            reading_service,
            book_service,
            book_parser,
            settings.max_upload_bytes,
        )
    )

    try:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Welcome & help"),
                BotCommand(command="read", description="Continue reading"),
                BotCommand(command="books", description="Change book"),
                BotCommand(command="stats", description="Progress"),
            ]
        )
        logger.info("Bot starting (long polling)")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except TelegramNetworkError:
        logger.exception("Telegram network error")
        raise
    finally:
        await db.aclose()
        await bot.session.close()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
