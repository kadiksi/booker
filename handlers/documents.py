"""Handle book file uploads (FB2, EPUB; MOBI rejected in parser)."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

from aiogram import F, Router
from aiogram.types import Message

from db.client import SupabaseError
from services.book_parser_service import BookParseError, BookParserService, UnsupportedFormatError
from services.book_service import BookService
from services.user_book_service import UserBookService
from services.user_service import UserService

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = frozenset({".fb2", ".epub", ".mobi"})


def build_document_router(
    user_service: UserService,
    user_book_service: UserBookService,
    book_service: BookService,
    book_parser: BookParserService,
    max_upload_bytes: int,
) -> Router:
    router = Router()

    @router.message(F.document)
    async def on_document(message: Message) -> None:
        if not message.from_user or not message.document:
            return
        doc = message.document
        telegram_id = str(message.from_user.id)

        if not doc.file_name:
            await message.answer("Please send a file with a name and extension (.fb2 or .epub).")
            return

        suffix = Path(doc.file_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            await message.answer(
                "Unsupported file type. Send an .fb2 or .epub (MOBI is not supported yet)."
            )
            return

        if doc.file_size is not None and doc.file_size > max_upload_bytes:
            await message.answer(
                f"File is too large (max {max_upload_bytes // (1024 * 1024)} MB). "
                "Try a smaller ebook."
            )
            return

        status = await message.answer("Downloading and parsing…")
        tmp_path: str | None = None
        summary: dict | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp_path = tmp.name
            await message.bot.download(doc, destination=tmp_path)

            if os.path.getsize(tmp_path) > max_upload_bytes:
                await status.edit_text(
                    f"File is too large after download (max {max_upload_bytes // (1024 * 1024)} MB)."
                )
                return

            title, paragraphs = await asyncio.to_thread(
                book_parser.parse_file,
                tmp_path,
                suffix.lstrip("."),
            )
            if not paragraphs:
                await status.edit_text(
                    "No usable paragraphs found (need at least one paragraph of 20+ characters)."
                )
                return

            default_title = Path(doc.file_name).stem
            summary = await book_service.create_from_paragraphs(
                title or default_title,
                paragraphs,
            )
            await user_service.ensure_user(telegram_id)
            await user_book_service.switch_current_book(telegram_id, summary["id"])
        except UnsupportedFormatError as e:
            await status.edit_text(str(e))
            return
        except BookParseError as e:
            logger.info("Parse error: %s", e)
            await status.edit_text(str(e))
            return
        except SupabaseError:
            logger.exception("Upload DB error")
            await status.edit_text("Could not save the book. Try again later.")
            return
        finally:
            if tmp_path and os.path.isfile(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    logger.warning("Temp file cleanup failed: %s", tmp_path)

        if summary:
            await status.edit_text(
                f"Saved “{summary['title']}” ({summary['chunks']} paragraphs). "
                "It’s now your current book — use /read to continue."
            )

    return router
