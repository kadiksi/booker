# Telegram book reading bot (MVP+)

Python 3.11 + [aiogram](https://docs.aiogram.dev/) + Supabase (PostgREST). Sends book paragraphs as chunks, supports FB2/EPUB uploads, per-book progress; **Read** under the paragraph, **Change book** via the bot command menu.

## Project layout

- `bot.py` — entrypoint
- `config.py` — env settings (`MAX_UPLOAD_MB`, etc.)
- `db/client.py` — async Supabase REST (`httpx`)
- `services/book_parser_service.py` — FB2 / EPUB parsing (run in `asyncio.to_thread`)
- `services/book_service.py` — create/list books
- `services/user_book_service.py` — `user_books` progress rows
- `services/user_service.py` — `users` row + default book
- `services/word_chunks.py` — чанки ~300–550 слов при длинном тексте; иначе один шаг на абзац как в файле
- `services/reading_service.py` — next chunk + `last_read_date`
- `services/book_seed.py` — sample book preload
- `handlers/setup.py` — commands, read/change-book callbacks, book picker
- `handlers/documents.py` — document upload handler
- `schema.sql` — full schema (fresh installs)
- `migrations/001_user_books.sql` — upgrade from older single-table progress
- `migrations/002_drop_streak.sql` — drop legacy `streak` on `user_books` if present
- `migrations/003_books_owner.sql` — колонка `books.owner_telegram_id` (список книг у каждого пользователя)
- `run_seed.py` — опционально загрузить демо для конкретного `telegram_id`

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

### Already have `user_books` with a `streak` column

Run `migrations/002_drop_streak.sql` once.

### Личные каталоги книг

Run `migrations/003_books_owner.sql` once. Книги с пустым `owner_telegram_id` не показываются в `/books` (старые глобальные записи).

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
- `SAMPLE_BOOK_ID` — id **старой** общей демо-книги (`sample-parable`) только для переноса прогресса при миграции; демо теперь создаётся автоматически как `d-<telegram_id>`.
- `MAX_UPLOAD_MB` (optional, default `10`)

Демо при первом `/start` создаётся само. Ручной seed для своего аккаунта (после деплоя):

```bash
SEED_TELEGRAM_ID=123456789 python run_seed.py
# или
python run_seed.py 123456789
```

Run:

```bash
python bot.py
```

## Features (commands)

- `/start` — register user, default sample book, ensure `user_books` row
- Send **.fb2** or **.epub** — parse, store chunks, set as current book (max size from `MAX_UPLOAD_MB`)
- **.mobi** — rejected with a clear message (not supported yet)
- `/books` — **ваши** книги (`owner_telegram_id`), выбор текущей
- `/read` — next paragraph + inline **✅ Read**; **Change book** is **/books** in the bot menu (☰)
- `/stats` — last read date (UTC) and progress for the **current** book

## Data model

- `users` — `telegram_id`, `current_book` (which book is active)
- `user_books` — per-user **per-book** `current_position`, `last_read_date` (unique on `telegram_id`, `book_id`)
- `books` / `chunks` — текст; у книги есть **`owner_telegram_id`** (чужие книги в списке не попадают). Демо по умолчанию: `d-<telegram_id>`.

`current_position` = число **прочитанных чанков**. Если в книге всего **меньше 300 слов**, чанк = **один исходный абзац** (как распарсился). Если текста больше — склейка в куски **~300–550** слов; при проблемах со склейкой снова режем **по абзацам**. Короткие `<p>` не выкидываются; EPUB без `<p>` — fallback на весь текст HTML; куски без текста пропускаются, парсинг идёт дальше.

Следующий фрагмент в чате — chunk с индексом `current_position + 1`.

## Deploy on Railway

Worker service, start `python bot.py`, env vars as in `.env`, pin Python 3.11 (`NIXPACKS_PYTHON_VERSION=3.11` if needed). Run `migrations/001_user_books.sql` on Supabase before deploying new code if you started from the old schema.

## Troubleshooting

- **401/403 Supabase:** URL/key; use **service_role** on the server.
- **Missing `user_books`:** run migration or full `schema.sql`.
- **Column `streak` errors:** run `migrations/002_drop_streak.sql` and ensure the app is updated.
- **Empty upload:** paragraphs shorter than 20 characters after cleaning are dropped; need at least one valid paragraph.
- **EPUB odd layout:** parser collects `<p>` only; very exotic layouts may need manual export to FB2.

## License

Use and modify freely for your project.
