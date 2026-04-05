-- Per-user book ownership. Nullable legacy rows (old global catalog) are invisible in /books.

alter table public.books
    add column if not exists owner_telegram_id text;

create index if not exists idx_books_owner on public.books (owner_telegram_id);
