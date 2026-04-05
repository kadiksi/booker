-- Fresh install: run in Supabase SQL Editor.
-- Existing project: run migrations/001_user_books.sql after this if you already had the old users shape.

create table if not exists public.books (
    id text primary key,
    title text not null,
    owner_telegram_id text
);

create index if not exists idx_books_owner on public.books (owner_telegram_id);

create table if not exists public.chunks (
    id serial primary key,
    book_id text not null references public.books (id) on delete cascade,
    position int not null,
    content text not null,
    unique (book_id, position)
);

create index if not exists idx_chunks_book_position on public.chunks (book_id, position);

create table if not exists public.users (
    id uuid primary key default gen_random_uuid(),
    telegram_id text not null unique,
    current_book text,
    utc_offset_minutes int not null default 0,
    telegram_language_code text not null default 'en'
);

create index if not exists idx_users_telegram_id on public.users (telegram_id);

create table if not exists public.user_books (
    id uuid primary key default gen_random_uuid(),
    telegram_id text not null,
    book_id text not null references public.books (id) on delete cascade,
    current_position int not null default 0,
    last_read_date date,
    unique (telegram_id, book_id)
);

create index if not exists idx_user_books_telegram on public.user_books (telegram_id);
create index if not exists idx_user_books_book on public.user_books (book_id);

create table if not exists public.reading_reminders (
    id uuid primary key default gen_random_uuid(),
    telegram_id text not null references public.users (telegram_id) on delete cascade,
    slot_key text not null,
    time_local text not null,
    enabled boolean not null default true,
    last_notified_date date,
    unique (telegram_id, slot_key),
    constraint reading_reminders_slot_key_check check (
        slot_key in ('morning_commute', 'lunch', 'evening_commute', 'before_sleep')
    )
);

create index if not exists idx_reading_reminders_telegram on public.reading_reminders (telegram_id);
create index if not exists idx_reading_reminders_enabled on public.reading_reminders (enabled);
