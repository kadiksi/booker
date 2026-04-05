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
- `services/word_chunks.py` — склейка абзацев в чанки ~300–550 слов
- `services/reading_service.py` — next chunk + `last_read_date`
- `services/book_seed.py` — sample book preload
- `handlers/setup.py` — commands, read/change-book callbacks, book picker
- `handlers/documents.py` — document upload handler
- `schema.sql` — full schema (fresh installs)
- `migrations/001_user_books.sql` — upgrade from older single-table progress
- `migrations/002_drop_streak.sql` — drop legacy `streak` on `user_books` if present
- `run_seed.py` — load sample book

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
- `SAMPLE_BOOK_ID` (optional)
- `MAX_UPLOAD_MB` (optional, default `10`)

Seed the sample book once:

```bash
python run_seed.py
```

Run:

```bash
python bot.py
```

## Features (commands)

- `/start` — register user, default sample book, ensure `user_books` row
- Send **.fb2** or **.epub** — parse, store chunks, set as current book (max size from `MAX_UPLOAD_MB`)
- **.mobi** — rejected with a clear message (not supported yet)
- `/books` — inline list of books → pick current book and resume progress
- `/read` — next paragraph + inline **✅ Read**; **Change book** is **/books** in the bot menu (☰)
- `/stats` — last read date (UTC) and progress for the **current** book

## Data model

- `users` — `telegram_id`, `current_book` (which book is active)
- `user_books` — per-user **per-book** `current_position`, `last_read_date` (unique on `telegram_id`, `book_id`)
- `books` / `chunks` — catalog text (`chunks.position` is 1-based)

`current_position` = число **прочитанных чанков**; каждый чанк — примерно **300–550** слов (исходные абзацы склеиваются). Очень короткая книга может дать один чанк меньше 300 слов; последний чанк длинной книги иногда короче 300, если иначе нельзя уложиться в максимум.

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
