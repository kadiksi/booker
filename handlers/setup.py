"""Commands and reading navigation callbacks."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.client import SupabaseClient, SupabaseError
from handlers.documents import build_document_router
from handlers.keyboards import NAV_READ, reading_keyboard
from handlers.reminders import build_reminder_router
from services.book_parser_service import BookParserService
from services.book_service import BookService
from services.i18n import norm_lang, t
from services.reading_service import ReadingService
from services.user_book_service import UserBookService
from services.user_service import UserService

logger = logging.getLogger(__name__)

NAV_BOOKS = "nav:books"
PICK_PREFIX = "pick:"


def build_router(
    db: SupabaseClient,
    user_service: UserService,
    user_book_service: UserBookService,
    reading_service: ReadingService,
    book_service: BookService,
    book_parser: BookParserService,
    max_upload_bytes: int,
    reminder_pending_slots: dict[str, dict],
) -> Router:
    router = Router()

    async def _load(
        telegram_id: str,
        language_code: str | None = None,
    ) -> tuple[dict, str | None, dict | None]:
        user = await user_service.ensure_user(telegram_id, language_code)
        book_id = user.get("current_book")
        ub = await user_book_service.ensure_row(telegram_id, book_id)
        return user, book_id, ub

    async def push_reading_view(
        message: Message,
        telegram_id: str,
        *,
        language_code: str | None = None,
    ) -> None:
        lang = norm_lang(language_code)
        _, book_id, ub = await _load(telegram_id, language_code)
        ctx = await reading_service.get_next_chunk_context(book_id, ub)
        if ctx.get("error") == "no_book":
            await message.answer(t(lang, "no_book"))
            return
        if ctx.get("done"):
            total = ctx.get("total_chunks", 0)
            await message.answer(t(lang, "book_finished", total=total))
            return
        text = str(ctx["chunk"].get("content", "")).rstrip()
        await message.answer(text or "…", reply_markup=reading_keyboard(language_code))

    async def send_book_picker(
        message: Message,
        telegram_id: str,
        *,
        language_code: str | None = None,
    ) -> None:
        lang = norm_lang(language_code)
        try:
            books = await book_service.list_books_for_user(telegram_id)
        except SupabaseError:
            logger.exception("list_books_for_user failed")
            await message.answer(t(lang, "err_catalog"))
            return
        if not books:
            await message.answer(t(lang, "no_books_library"))
            return
        kb = InlineKeyboardBuilder()
        for b in books:
            bid = str(b["id"])
            label = (b.get("title") or bid)[:58]
            kb.button(text=label, callback_data=f"{PICK_PREFIX}{bid}")
        kb.adjust(1)
        await message.answer(t(lang, "choose_book"), reply_markup=kb.as_markup())

    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        if not message.from_user:
            return
        telegram_id = str(message.from_user.id)
        lang = norm_lang(message.from_user.language_code)
        try:
            await user_service.ensure_user(telegram_id, message.from_user.language_code)
        except SupabaseError:
            logger.exception("ensure_user failed")
            await message.answer(t(lang, "err_profile_save"))
            return

        await message.answer(t(lang, "start_help"))

    @router.message(Command("books"))
    async def cmd_books(message: Message) -> None:
        if not message.from_user:
            return
        lang = norm_lang(message.from_user.language_code)
        try:
            await user_service.ensure_user(
                str(message.from_user.id),
                message.from_user.language_code,
            )
        except SupabaseError:
            await message.answer(t(lang, "err_verify_account"))
            return
        await send_book_picker(
            message,
            str(message.from_user.id),
            language_code=message.from_user.language_code,
        )

    @router.message(Command("read"))
    async def cmd_read(message: Message) -> None:
        if not message.from_user:
            return
        lang = norm_lang(message.from_user.language_code)
        try:
            await push_reading_view(
                message,
                str(message.from_user.id),
                language_code=message.from_user.language_code,
            )
        except SupabaseError:
            logger.exception("cmd_read failed")
            await message.answer(t(lang, "err_reading_state"))

    @router.message(Command("stats"))
    async def cmd_stats(message: Message) -> None:
        if not message.from_user:
            return
        telegram_id = str(message.from_user.id)
        lang = norm_lang(message.from_user.language_code)
        try:
            _, book_id, ub = await _load(telegram_id, message.from_user.language_code)
            ctx = await reading_service.get_next_chunk_context(book_id, ub)
        except SupabaseError:
            logger.exception("cmd_stats failed")
            await message.answer(t(lang, "err_stats"))
            return

        completed = int(ub.get("current_position") or 0) if ub else 0
        last = ub.get("last_read_date") if ub else None
        book_label = "—"
        if book_id:
            book_row = await book_service.get_book(book_id)
            book_label = (book_row.get("title") if book_row else None) or book_id

        if ctx.get("done"):
            progress = t(lang, "stats_progress_done", completed=completed)
        else:
            nxt = completed + 1
            progress = t(lang, "stats_progress_next", completed=completed, nxt=nxt)

        await message.answer(
            t(
                lang,
                "stats_header_last",
                last=last or "—",
                bid=book_label,
                progress=progress,
            )
        )

    @router.callback_query(F.data == NAV_BOOKS)
    async def on_nav_books(callback: CallbackQuery) -> None:
        if not callback.from_user or not callback.message:
            await callback.answer()
            return
        lang = norm_lang(callback.from_user.language_code)
        await callback.answer()
        try:
            await user_service.ensure_user(
                str(callback.from_user.id),
                callback.from_user.language_code,
            )
        except SupabaseError:
            await callback.message.answer(t(lang, "err_verify_account"))
            return
        await send_book_picker(
            callback.message,
            str(callback.from_user.id),
            language_code=callback.from_user.language_code,
        )

    @router.callback_query(F.data.startswith(PICK_PREFIX))
    async def on_book_picked(callback: CallbackQuery) -> None:
        if not callback.from_user or not callback.message or not callback.data:
            await callback.answer()
            return
        lang = norm_lang(callback.from_user.language_code)
        book_id = callback.data[len(PICK_PREFIX) :]
        telegram_id = str(callback.from_user.id)
        try:
            book = await book_service.get_book(book_id)
            if not book:
                await callback.answer(t(lang, "book_not_found"), show_alert=True)
                return
            if book.get("owner_telegram_id") != telegram_id:
                await callback.answer(t(lang, "book_not_yours"), show_alert=True)
                return
            await user_book_service.switch_current_book(telegram_id, book_id)
        except SupabaseError:
            logger.exception("switch book failed")
            await callback.answer(t(lang, "err_switch_book"), show_alert=True)
            return

        await callback.answer(t(lang, "book_selected"))
        title = book.get("title") or book_id
        await callback.message.answer(t(lang, "current_book_shown", title=title))
        await push_reading_view(
            callback.message,
            telegram_id,
            language_code=callback.from_user.language_code,
        )

    @router.callback_query(F.data == NAV_READ)
    async def on_read_click(callback: CallbackQuery) -> None:
        if not callback.from_user or not callback.message:
            await callback.answer()
            return
        telegram_id = str(callback.from_user.id)
        lang = norm_lang(callback.from_user.language_code)

        try:
            _, book_id, ub = await _load(telegram_id, callback.from_user.language_code)
            if not book_id or not ub:
                await callback.answer(t(lang, "no_active_book"), show_alert=True)
                return
            result = await reading_service.record_read(telegram_id, book_id, ub)
        except SupabaseError:
            logger.exception("record_read failed")
            await callback.answer(t(lang, "err_save_progress"), show_alert=True)
            return

        await callback.answer()

        if result.get("book_finished"):
            await callback.message.answer(t(lang, "book_done"))
            return

        await push_reading_view(
            callback.message,
            telegram_id,
            language_code=callback.from_user.language_code,
        )

    router.include_router(
        build_reminder_router(db, user_service, reminder_pending_slots),
    )

    doc_router = build_document_router(
        user_service,
        user_book_service,
        book_service,
        book_parser,
        max_upload_bytes,
    )
    router.include_router(doc_router)

    return router
