"""Commands and reading navigation callbacks."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.client import SupabaseError
from handlers.documents import build_document_router
from services.book_service import BookService
from services.book_parser_service import BookParserService
from services.reading_service import ReadingService
from services.user_book_service import UserBookService
from services.user_service import UserService

logger = logging.getLogger(__name__)

NAV_READ = "nav:read"
NAV_BOOKS = "nav:books"
PICK_PREFIX = "pick:"


def reading_keyboard() -> object:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Read", callback_data=NAV_READ)
    return kb.as_markup()


def build_router(
    user_service: UserService,
    user_book_service: UserBookService,
    reading_service: ReadingService,
    book_service: BookService,
    book_parser: BookParserService,
    max_upload_bytes: int,
) -> Router:
    router = Router()

    async def _load(
        telegram_id: str,
    ) -> tuple[dict, str | None, dict | None]:
        user = await user_service.ensure_user(telegram_id)
        book_id = user.get("current_book")
        ub = await user_book_service.ensure_row(telegram_id, book_id)
        return user, book_id, ub

    async def push_reading_view(message: Message, telegram_id: str) -> None:
        _, book_id, ub = await _load(telegram_id)
        ctx = await reading_service.get_next_chunk_context(book_id, ub)
        if ctx.get("error") == "no_book":
            await message.answer("No book selected. Use /books or upload a file.")
            return
        if ctx.get("done"):
            total = ctx.get("total_chunks", 0)
            await message.answer(
                f"You’ve finished this book ({total} paragraphs). "
                "Use /books or upload another file."
            )
            return
        text = str(ctx["chunk"].get("content", "")).strip()
        await message.answer(text, reply_markup=reading_keyboard())

    async def send_book_picker(message: Message) -> None:
        try:
            books = await book_service.list_books()
        except SupabaseError:
            logger.exception("list_books failed")
            await message.answer("Could not load the catalog. Try again later.")
            return
        if not books:
            await message.answer("No books yet. Upload an .fb2 or .epub file.")
            return
        kb = InlineKeyboardBuilder()
        for b in books:
            bid = str(b["id"])
            label = (b.get("title") or bid)[:58]
            kb.button(text=label, callback_data=f"{PICK_PREFIX}{bid}")
        kb.adjust(1)
        await message.answer("Choose a book:", reply_markup=kb.as_markup())

    @router.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        if not message.from_user:
            return
        telegram_id = str(message.from_user.id)
        try:
            await user_service.ensure_user(telegram_id)
        except SupabaseError:
            logger.exception("ensure_user failed")
            await message.answer("Could not save your profile. Try again later.")
            return

        await message.answer(
            "Welcome. You’re set up for reading.\n\n"
            "• Send an .fb2 or .epub to add a book (MOBI not supported yet)\n"
            "• Change book: open the bot menu (☰) or type / and tap “Change book” (/books)\n"
            "• /read — current paragraph + ✅ Read\n"
            "• /stats — progress for this book\n"
            "Under each paragraph only the ✅ Read button."
        )

    @router.message(Command("books"))
    async def cmd_books(message: Message) -> None:
        if not message.from_user:
            return
        try:
            await user_service.ensure_user(str(message.from_user.id))
        except SupabaseError:
            await message.answer("Could not verify your account.")
            return
        await send_book_picker(message)

    @router.message(Command("read"))
    async def cmd_read(message: Message) -> None:
        if not message.from_user:
            return
        try:
            await push_reading_view(message, str(message.from_user.id))
        except SupabaseError:
            logger.exception("cmd_read failed")
            await message.answer("Could not load your reading state. Try again later.")

    @router.message(Command("stats"))
    async def cmd_stats(message: Message) -> None:
        if not message.from_user:
            return
        telegram_id = str(message.from_user.id)
        try:
            _, book_id, ub = await _load(telegram_id)
            ctx = await reading_service.get_next_chunk_context(book_id, ub)
        except SupabaseError:
            logger.exception("cmd_stats failed")
            await message.answer("Could not load stats. Try again later.")
            return

        completed = int(ub.get("current_position") or 0) if ub else 0
        last = ub.get("last_read_date") if ub else None
        bid = book_id or "—"

        if ctx.get("done"):
            progress_note = f"Progress: finished ({completed} paragraphs)."
        else:
            nxt = completed + 1
            progress_note = f"Progress: {completed} paragraphs done — next is #{nxt}."

        await message.answer(
            f"Last read (UTC): {last or '—'}\n"
            f"Book: {bid}\n"
            f"{progress_note}"
        )

    @router.callback_query(F.data == NAV_BOOKS)
    async def on_nav_books(callback: CallbackQuery) -> None:
        if not callback.from_user or not callback.message:
            await callback.answer()
            return
        await callback.answer()
        try:
            await user_service.ensure_user(str(callback.from_user.id))
        except SupabaseError:
            await callback.message.answer("Could not verify your account.")
            return
        await send_book_picker(callback.message)

    @router.callback_query(F.data.startswith(PICK_PREFIX))
    async def on_book_picked(callback: CallbackQuery) -> None:
        if not callback.from_user or not callback.message or not callback.data:
            await callback.answer()
            return
        book_id = callback.data[len(PICK_PREFIX) :]
        telegram_id = str(callback.from_user.id)
        try:
            book = await book_service.get_book(book_id)
            if not book:
                await callback.answer("Book not found.", show_alert=True)
                return
            await user_book_service.switch_current_book(telegram_id, book_id)
        except SupabaseError:
            logger.exception("switch book failed")
            await callback.answer("Could not switch book.", show_alert=True)
            return

        await callback.answer("Book selected")
        title = book.get("title") or book_id
        await callback.message.answer(f"Current book: {title}. Showing where you left off.")
        await push_reading_view(callback.message, telegram_id)

    @router.callback_query(F.data == NAV_READ)
    async def on_read_click(callback: CallbackQuery) -> None:
        if not callback.from_user or not callback.message:
            await callback.answer()
            return
        telegram_id = str(callback.from_user.id)

        try:
            _, book_id, ub = await _load(telegram_id)
            if not book_id or not ub:
                await callback.answer("No active book.", show_alert=True)
                return
            result = await reading_service.record_read(telegram_id, book_id, ub)
        except SupabaseError:
            logger.exception("record_read failed")
            await callback.answer("Could not save progress.", show_alert=True)
            return

        await callback.answer()

        if result.get("book_finished"):
            await callback.message.answer(
                "You’ve reached the end of this book. /books to pick another, or upload a new file."
            )
            return

        await push_reading_view(callback.message, telegram_id)

    doc_router = build_document_router(
        user_service,
        user_book_service,
        book_service,
        book_parser,
        max_upload_bytes,
    )
    router.include_router(doc_router)

    return router
