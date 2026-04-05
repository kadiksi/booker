"""Локализация UI по коду языка Telegram (`User.language_code`). Поддержка: en (по умолчанию), ru, kk."""

from __future__ import annotations

from aiogram import Bot
from aiogram.types import BotCommand

_SUPPORTED = frozenset({"en", "ru", "kk"})

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "cmd_start_desc": "Welcome and help",
        "cmd_read_desc": "Continue reading",
        "cmd_books_desc": "Change book",
        "cmd_stats_desc": "Reading progress",
        "cmd_reminders_desc": "Reading reminders",
        "btn_read_next": "✅ Next",
        "start_help": (
            "Welcome. You can start reading.\n\n"
            "• Send .fb2 or .epub to add a book (MOBI not supported yet)\n"
            "• Change book: bot menu (☰) or / → Change book (/books)\n"
            "• /read — current chunk and the “Next” button\n"
            "• /stats — progress for the current book\n"
            "• /reminders — reminders: phone time first, then setup menu\n"
            "Only the “Next” button appears under the text."
        ),
        "err_profile_save": "Could not save your profile. Try again later.",
        "no_book": "No book selected. Use /books or send a file.",
        "book_finished": "You finished this book ({total} chunks). Pick another with /books or upload a new file.",
        "err_catalog": "Could not load the catalog. Try again later.",
        "no_books_library": "No books in your library yet. Send a .fb2 or .epub file.",
        "choose_book": "Choose a book:",
        "err_verify_account": "Could not verify your account.",
        "err_reading_state": "Could not load reading state. Try again later.",
        "err_stats": "Could not load stats. Try again later.",
        "stats_header_last": "Last read (UTC date): {last}\nBook: {bid}\n{progress}",
        "stats_progress_done": "Progress: finished ({completed} chunks).",
        "stats_progress_next": "Progress: {completed} chunks read — next is #{nxt}.",
        "book_not_found": "Book not found.",
        "book_not_yours": "This book is not in your library.",
        "err_switch_book": "Could not switch book.",
        "book_selected": "Book selected",
        "current_book_shown": "Current book: {title}. Resuming where you left off.",
        "no_active_book": "No active book.",
        "err_save_progress": "Could not save progress.",
        "book_done": "You finished this book. Use /books or upload a new file.",
        "doc_need_filename": "Send a file with a name and extension (.fb2 or .epub).",
        "doc_bad_type": "Unsupported format. Send .fb2 or .epub (MOBI not supported yet).",
        "doc_too_large": "File is too large (max {max_mb} MB). Try a smaller file.",
        "doc_downloading": "Downloading and parsing…",
        "doc_too_large_after": "File is too large after download (max {max_mb} MB).",
        "doc_save_err": "Could not save the book. Try again later.",
        "doc_empty_parse": "Could not extract text from the file (empty or unsupported layout).",
        "doc_saved": "Saved “{title}” ({chunks} chunks). It’s your current book — use /read.",
        "reminders_intro": "Reminders (clock synced when you open /reminders):",
        "reminders_hint": (
            "Pick a slot, then send **HH:MM** for that reminder.\n"
            "To reopen the menu with a fresh phone sync: **/reminders** again."
        ),
        "rem_menu_ask_phone": (
            "Send **your current phone time** (**HH:MM**, 24h) in one message — "
            "we’ll sync the clock for reminders.\n"
            "Then you’ll see the setup menu with slots.\n"
            "Best in the same minute as on your screen.\n"
            "Cancel: **/reminders** again."
        ),
        "err_reminders_load": "Could not load reminders. Try again later.",
        "rem_clear_btn": "🗑 Clear all reminders",
        "unknown_slot": "Unknown slot.",
        "err_clear": "Could not clear.",
        "rem_cleared_toast": "All reminders cleared",
        "rem_cleared_msg": "All reminders removed. Set again: /reminders",
        "rem_need_hhmm": "Use HH:MM, e.g. 09:05. Try again.",
        "rem_sync_fail": (
            "Could not match time to the message timestamp. "
            "Check HH:MM and send again right after /reminders."
        ),
        "rem_save_offset_fail": "Could not save. Try again later.",
        "rem_slot_time_prompt": "Send **HH:MM** when to remind for “{label}”.",
        "rem_save_fail": "Could not save reminder.",
        "rem_saved": "Saved: “{label}” at {time}. I’ll message you then with the {btn} button.",
        "rem_tick": "📖 It’s {hm} — “{label}”. Open /read and continue.\n",
        "rem_tick_note": "Time from your last phone sync when you opened /reminders.",
        "slot_morning_commute": "Commute to work",
        "slot_lunch": "Lunch",
        "slot_evening_commute": "Commute home",
        "slot_before_sleep": "Before sleep",
    },
    "ru": {
        "cmd_start_desc": "Приветствие и справка",
        "cmd_read_desc": "Читать дальше",
        "cmd_books_desc": "Сменить книгу",
        "cmd_stats_desc": "Прогресс чтения",
        "cmd_reminders_desc": "Напоминания о чтении",
        "btn_read_next": "✅ Дальше",
        "start_help": (
            "Добро пожаловать. Можно читать.\n\n"
            "• Пришлите .fb2 или .epub, чтобы добавить книгу (MOBI пока нет)\n"
            "• Сменить книгу: меню бота (☰) или / → «Сменить книгу» (/books)\n"
            "• /read — текущий фрагмент и кнопка «✅ Дальше»\n"
            "• /stats — прогресс по текущей книге\n"
            "• /reminders — напоминания: сначала время с телефона, затем меню настройки\n"
            "Под текстом только кнопка «✅ Дальше»."
        ),
        "err_profile_save": "Не удалось сохранить профиль. Попробуйте позже.",
        "no_book": "Книга не выбрана. Используйте /books или пришлите файл.",
        "book_finished": "Книга закончилась ({total} фрагментов). Выберите другую через /books или загрузите новый файл.",
        "err_catalog": "Не удалось загрузить каталог. Попробуйте позже.",
        "no_books_library": "В библиотеке пока нет книг. Пришлите файл .fb2 или .epub.",
        "choose_book": "Выберите книгу:",
        "err_verify_account": "Не удалось проверить аккаунт.",
        "err_reading_state": "Не удалось загрузить чтение. Попробуйте позже.",
        "err_stats": "Не удалось загрузить статистику. Попробуйте позже.",
        "stats_header_last": "Последнее чтение (дата, UTC): {last}\nКнига: {bid}\n{progress}",
        "stats_progress_done": "Прогресс: книга прочитана ({completed} фрагментов).",
        "stats_progress_next": "Прогресс: прочитано {completed} фрагментов — далее №{nxt}.",
        "book_not_found": "Книга не найдена.",
        "book_not_yours": "Этой книги нет в вашей библиотеке.",
        "err_switch_book": "Не удалось сменить книгу.",
        "book_selected": "Книга выбрана",
        "current_book_shown": "Текущая книга: {title}. Показываю, где остановились.",
        "no_active_book": "Нет активной книги.",
        "err_save_progress": "Не удалось сохранить прогресс.",
        "book_done": "Книга закончилась. Выберите другую через /books или загрузите новый файл.",
        "doc_need_filename": "Пришлите файл с именем и расширением (.fb2 или .epub).",
        "doc_bad_type": "Неподдерживаемый формат. Нужен .fb2 или .epub (MOBI пока не поддерживается).",
        "doc_too_large": "Файл слишком большой (макс. {max_mb} МБ). Попробуйте меньший файл.",
        "doc_downloading": "Скачиваю и разбираю файл…",
        "doc_too_large_after": "После загрузки файл слишком большой (макс. {max_mb} МБ).",
        "doc_save_err": "Не удалось сохранить книгу. Попробуйте позже.",
        "doc_empty_parse": "Не удалось извлечь текст из файла (пусто или неподдерживаемая вёрстка).",
        "doc_saved": "Сохранено «{title}» ({chunks} фрагментов). Это текущая книга — продолжите через /read.",
        "reminders_intro": "Напоминания (часы синхронизируются при открытии /reminders):",
        "reminders_hint": (
            "Выберите слот, затем отправьте **ЧЧ:ММ** для этого напоминания.\n"
            "Чтобы снова синхронизировать время с телефона: **/reminders** ещё раз."
        ),
        "rem_menu_ask_phone": (
            "Отправьте **текущее время с телефона** (**ЧЧ:ММ**, 24 ч.) одним сообщением — "
            "подстроим часы для напоминаний.\n"
            "Затем появится меню со слотами.\n"
            "Лучше в ту же минуту, что на экране.\n"
            "Отмена: снова **/reminders**."
        ),
        "err_reminders_load": "Не удалось загрузить напоминания. Попробуйте позже.",
        "rem_clear_btn": "🗑 Убрать все напоминания",
        "unknown_slot": "Неизвестный слот.",
        "err_clear": "Не удалось очистить.",
        "rem_cleared_toast": "Все напоминания убраны",
        "rem_cleared_msg": "Все напоминания удалены. Настроить снова: /reminders",
        "rem_need_hhmm": "Нужно время в формате ЧЧ:ММ, например 09:05. Попробуйте ещё раз.",
        "rem_sync_fail": (
            "Не удалось сопоставить время с моментом сообщения. "
            "Проверьте ЧЧ:ММ и отправьте снова сразу после /reminders."
        ),
        "rem_save_offset_fail": "Не удалось сохранить. Попробуйте позже.",
        "rem_slot_time_prompt": "Отправьте **ЧЧ:ММ**, когда напоминать «{label}».",
        "rem_save_fail": "Не удалось сохранить напоминание.",
        "rem_saved": "Сохранено: «{label}» в {time}. В это время пришлю сообщение с кнопкой {btn}.",
        "rem_tick": "📖 Сейчас {hm} — «{label}». Откройте /read и продолжите книгу.\n",
        "rem_tick_note": "Время по последней синхронизации с телефоном при открытии /reminders.",
        "slot_morning_commute": "Путь на работу",
        "slot_lunch": "Обед",
        "slot_evening_commute": "Путь с работы",
        "slot_before_sleep": "Перед сном",
    },
    "kk": {
        "cmd_start_desc": "Қош келдіңіз және анықтама",
        "cmd_read_desc": "Оқуды жалғастыру",
        "cmd_books_desc": "Кітапты ауыстыру",
        "cmd_stats_desc": "Оқу прогресі",
        "cmd_reminders_desc": "Оқу туралы еске салулар",
        "btn_read_next": "✅ Әрі қарай",
        "start_help": (
            "Қош келдіңіз. Оқуды бастауға болады.\n\n"
            "• Кітап қосу үшін .fb2 немесе .epub жіберіңіз (MOBI әлі жоқ)\n"
            "• Кітапты ауыстыру: бот мәзірі (☰) немесе / → «Кітапты ауыстыру» (/books)\n"
            "• /read — ағымдағы бөлім және «✅ Әрі қарай» батырмасы\n"
            "• /stats — ағымдағы кітап бойынша прогресс\n"
            "• /reminders — алдымен телефон уақыты, содан кейін баптау мәзірі\n"
            "Мәтін астында тек «✅ Әрі қарай» батырмасы көрінеді."
        ),
        "err_profile_save": "Профильді сақтау мүмкін болмады. Кейінірек қайталаңыз.",
        "no_book": "Кітап таңдалмаған. /books пайдаланыңыз немесе файл жіберіңіз.",
        "book_finished": (
            "Кітап аяқталды ({total} бөліктер). Басқа кітапты /books арқылы таңдаңыз "
            "немесе жаңа файл жүктеңіз."
        ),
        "err_catalog": "Каталогты жүктеу мүмкін болмады. Кейінірек қайталаңыз.",
        "no_books_library": "Кітапханада әзірге кітап жоқ. .fb2 немесе .epub файлын жіберіңіз.",
        "choose_book": "Кітапты таңдаңыз:",
        "err_verify_account": "Тіркелгіні тексеру мүмкін болмады.",
        "err_reading_state": "Оқу күйін жүктеу мүмкін болмады. Кейінірек қайталаңыз.",
        "err_stats": "Статистиканы жүктеу мүмкін болмады. Кейінірек қайталаңыз.",
        "stats_header_last": "Соңғы оқу (күн, UTC): {last}\nКітап: {bid}\n{progress}",
        "stats_progress_done": "Прогресс: кітап оқылып бітті ({completed} бөліктер).",
        "stats_progress_next": "Прогресс: {completed} бөлік оқылды — келесі №{nxt}.",
        "book_not_found": "Кітап табылмады.",
        "book_not_yours": "Бұл кітап сіздің кітапханаңызда жоқ.",
        "err_switch_book": "Кітапты ауыстыру мүмкін болмады.",
        "book_selected": "Кітап таңдалды",
        "current_book_shown": "Ағымдағы кітап: {title}. Тоқтаған жерден көрсетемін.",
        "no_active_book": "Белсенді кітап жоқ.",
        "err_save_progress": "Прогресті сақтау мүмкін болмады.",
        "book_done": (
            "Кітап аяқталды. Басқа кітапты /books арқылы таңдаңыз немесе жаңа файл жүктеңіз."
        ),
        "doc_need_filename": "Аты мен кеңейтілмі бар файл жіберіңіз (.fb2 немесе .epub).",
        "doc_bad_type": (
            "Формат қолданылмайды. .fb2 немесе .epub керек (MOBI әлі қолданылмайды)."
        ),
        "doc_too_large": "Файл тым үлкен (макс. {max_mb} МБ). Кішірек файлды қолданыңыз.",
        "doc_downloading": "Жүктеп алып, талдау…",
        "doc_too_large_after": "Жүктеп алғаннан кейін файл тым үлкен (макс. {max_mb} МБ).",
        "doc_save_err": "Кітапты сақтау мүмкін болмады. Кейінірек қайталаңыз.",
        "doc_empty_parse": (
            "Файлдан мәтін алу мүмкін болмады (бос немесе қолданылмайтын бетбелгі)."
        ),
        "doc_saved": (
            "«{title}» сақталды ({chunks} бөліктер). Бұл ағымдағы кітап — /read арқылы жалғастырыңыз."
        ),
        "reminders_intro": "Еске салулар (/reminders ашқанда сағат синхрондалады):",
        "reminders_hint": (
            "Слотты таңдаңыз, содан кейін осы еске салу үшін **СС:ММ** жіберіңіз.\n"
            "Телефон уақытын қайта синхрондау үшін: **/reminders** қайта."
        ),
        "rem_menu_ask_phone": (
            "Бір хабарламада **телефондағы ағымдағы уақытты** (**СС:ММ**, 24 сағ.) жіберіңіз — "
            "еске салулар үшін сағатты сәйкестендіреміз.\n"
            "Содан кейін слоттармен баптау мәзірі шығады.\n"
            "Экрандағы минутпен бірдей жіберген дұрыс.\n"
            "Болдырмау: **/reminders** қайта."
        ),
        "err_reminders_load": "Еске салуларды жүктеу мүмкін болмады. Кейінірек қайталаңыз.",
        "rem_clear_btn": "🗑 Барлық еске салуларды өшіру",
        "unknown_slot": "Белгісіз слот.",
        "err_clear": "Тазалау мүмкін болмады.",
        "rem_cleared_toast": "Барлық еске салулар өшірілді",
        "rem_cleared_msg": "Барлық еске салулар жойылды. Қайта баптау: /reminders",
        "rem_need_hhmm": "СС:ММ пішімін қолданыңыз, мысалы 09:05. Қайталаңыз.",
        "rem_sync_fail": (
            "Уақытты хабарлама уақытымен сәйкестендіру мүмкін болмады. "
            "СС:ММ дұрыстығын тексеріп, /reminders кейін дереу қайта жіберіңіз."
        ),
        "rem_save_offset_fail": "Сақтау мүмкін болмады. Кейінірек қайталаңыз.",
        "rem_slot_time_prompt": "«{label}» үшін **СС:ММ** қашан еске салу керектігін жіберіңіз.",
        "rem_save_fail": "Еске салуді сақтау мүмкін болмады.",
        "rem_saved": "Сақталды: «{label}» — {time}. Сол уақытта {btn} батырмасымен хабарлама жіберемін.",
        "rem_tick": "📖 Қазір {hm} — «{label}». /read ашып, оқуды жалғастырыңыз.\n",
        "rem_tick_note": "Уақыт /reminders соңғы ашқандағы телефон синхронына сәйкес.",
        "slot_morning_commute": "Жұмысқа бара жатқанда",
        "slot_lunch": "Түскі ас",
        "slot_evening_commute": "Жұмыстан қайту",
        "slot_before_sleep": "Ұйқы алдында",
    },
}


def norm_lang(language_code: str | None) -> str:
    if not language_code or not str(language_code).strip():
        return "en"
    base = str(language_code).strip().lower().replace("_", "-").split("-")[0]
    return base if base in _SUPPORTED else "en"


def t(lang: str, key: str, **kwargs: str | int) -> str:
    lang = lang if lang in _SUPPORTED else "en"
    pack = STRINGS.get(lang, STRINGS["en"])
    template = pack.get(key) or STRINGS["en"].get(key) or key
    if kwargs:
        return template.format(**kwargs)
    return template


def slot_label(lang: str, slot_key: str) -> str:
    return t(lang, f"slot_{slot_key}")


def build_bot_commands(lang: str) -> list[BotCommand]:
    lang = lang if lang in _SUPPORTED else "en"
    return [
        BotCommand(command="start", description=t(lang, "cmd_start_desc")),
        BotCommand(command="read", description=t(lang, "cmd_read_desc")),
        BotCommand(command="books", description=t(lang, "cmd_books_desc")),
        BotCommand(command="stats", description=t(lang, "cmd_stats_desc")),
        BotCommand(command="reminders", description=t(lang, "cmd_reminders_desc")),
    ]


async def register_localized_commands(bot: Bot) -> None:
    """Язык по умолчанию — en; ru/kk — отдельные списки (Telegram API)."""
    await bot.set_my_commands(build_bot_commands("en"))
    await bot.set_my_commands(build_bot_commands("ru"), language_code="ru")
    await bot.set_my_commands(build_bot_commands("kk"), language_code="kk")
