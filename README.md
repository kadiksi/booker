# Telegram book reading bot (MVP+)

Python 3.11 + [aiogram](https://docs.aiogram.dev/) + Supabase (PostgREST). Книга по фрагментам, FB2/EPUB, прогресс; под абзацем кнопка **✅ Дальше**, смена книги через меню бота.

## Project layout

- `bot.py` — entrypoint
- `config.py` — env settings (`MAX_UPLOAD_MB`, etc.)
- `db/client.py` — async Supabase REST (`httpx`)
- `services/book_parser_service.py` — FB2 / EPUB parsing (run in `asyncio.to_thread`)
- `services/book_service.py` — create/list books
- `services/user_book_service.py` — `user_books` progress rows
- `services/user_service.py` — `users` row; текущая книга после загрузки файла
- `services/word_chunks.py` — один шаг / одно сообщение на абзац; длинный абзац режется под лимит Telegram
- `services/reading_service.py` — next chunk + `last_read_date`
- `handlers/setup.py` — commands, read/change-book callbacks, book picker
- `handlers/reminders.py` — /reminders, слоты + синхронизация времени с телефона
- `handlers/keyboards.py` — общая inline-клавиатура **✅ Дальше**
- `handlers/documents.py` — document upload handler
- `services/reminder_service.py` — локальное время, фоновые напоминания
- `services/utc_offset_sync.py` — сдвиг UTC от «времени с телефона»
- `schema.sql` — full schema (fresh installs)
- `migrations/001_user_books.sql` — upgrade from older single-table progress
- `migrations/003_books_owner.sql` — колонка `books.owner_telegram_id` (список книг у каждого пользователя)
- `migrations/004_reading_reminders.sql` — таблица `reading_reminders` (+ исторически колонка `timezone`; см. 005)
- `migrations/005_utc_offset_only.sql` — убрать IANA, добавить `users.utc_offset_minutes` (сдвиг в минутах от UTC)
- `migrations/006_user_language.sql` — `users.telegram_language_code` для локализации (en, ru, kk)
- `services/i18n.py` — строки интерфейса и меню команд по языку Telegram
## Prerequisites

- Python 3.11+
- Supabase project
- Telegram bot token

## Supabase setup

### New project

1. **SQL Editor** → paste and run `schema.sql`.

### Already using the first MVP schema (`users.current_position`, …)

1. Run `migrations/001_user_books.sql` once. It creates `user_books`, copies progress from `users`, and drops the legacy columns.
2. Redeploy the bot **after** the migration so inserts match the slim `users` table.

### Личные каталоги книг

Run `migrations/003_books_owner.sql` once. Книги с пустым `owner_telegram_id` не показываются в `/books` (старые глобальные записи).

### Напоминания о чтении

Run `migrations/004_reading_reminders.sql` once, затем **`005`**, затем **`006`** (или актуальный `schema.sql` для новых проектов).

3. Under **Project Settings → API**, copy **Project URL** and **service_role** key.

## Local configuration

```bash
cd book_reader
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env`:

- `BOT_TOKEN`, `SUPABASE_URL`, `SUPABASE_KEY`
- `SAMPLE_BOOK_ID` — id **старой** общей демо-книги (`sample-parable`): при первом заходе после обновления бот сбросит `current_book` для этих пользователей (встроенной демо-книги нет).
- `MAX_UPLOAD_MB` (optional, default `10`)

Run:

```bash
python bot.py
```

## Features (commands)

- `/start` — регистрация пользователя; книгу добавьте, отправив файл
- Send **.fb2** or **.epub** — parse, store chunks, set as current book (max size from `MAX_UPLOAD_MB`)
- **.mobi** — rejected with a clear message (not supported yet)
- `/books` — **ваши** книги (`owner_telegram_id`), выбор текущей
- `/read` — следующий фрагмент + **✅ Дальше**; смена книги — **/books** в меню (☰)
- `/stats` — last read date (UTC) and progress for the **current** book
- `/reminders` — до четырёх слотов. Сначала **время с телефона (ЧЧ:ММ)**, затем меню; для слота — только **время напоминания**. Снова `/reminders` снова просит время для синхронизации. В нужную минуту — сообщение с **✅ Дальше** (не чаще раза в сутки на слот). Переезд / перевод часов — повторите `/reminders`.

## Data model

- `users` — `telegram_id`, `current_book`, **`utc_offset_minutes`**, **`telegram_language_code`** (код языка из Telegram: en, ru, kk; обновляется при запросах)
- `reading_reminders` — слот (`morning_commute`, `lunch`, `evening_commute`, `before_sleep`), время `HH:MM` в тех же «телефонных» часах, `last_notified_date` по **локальной** дате пользователя (с учётом сдвига)
- `user_books` — per-user **per-book** `current_position`, `last_read_date` (unique on `telegram_id`, `book_id`)
- `books` / `chunks` — текст; у книги есть **`owner_telegram_id`** (чужие книги в списке не попадают). Демо по умолчанию: `d-<telegram_id>`.

`current_position` = число **прочитанных чанков**; каждый чанк — **один абзац** (как распарсился), одно сообщение в чате. Абзац длиннее **4096** символов хранится несколькими чанками подряд. Короткие `<p>` не выкидываются; EPUB без `<p>` — fallback на весь текст HTML; куски без текста пропускаются, парсинг идёт дальше.

Следующий фрагмент в чате — chunk с индексом `current_position + 1`.

## Deploy on Railway

Worker service, start `python bot.py`, env vars as in `.env`, pin Python 3.11 (`NIXPACKS_PYTHON_VERSION=3.11` if needed). Run `migrations/001_user_books.sql` on Supabase before deploying new code if you started from the old schema.

## Troubleshooting

- **401/403 Supabase:** URL/key; use **service_role** on the server.
- **Missing `user_books`:** run migration or full `schema.sql`.
- **Empty upload:** paragraphs shorter than 20 characters after cleaning are dropped; need at least one valid paragraph.
- **EPUB odd layout:** parser collects `<p>` only; very exotic layouts may need manual export to FB2.

## License

Use and modify freely for your project.
