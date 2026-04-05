-- Migration: per-book progress (user_books) and slim users table.
-- Run once in Supabase SQL Editor if you deployed the earlier schema with
-- users.current_position / streak / last_read_date.

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

insert into public.user_books (telegram_id, book_id, current_position, last_read_date)
select u.telegram_id, u.current_book, u.current_position, u.last_read_date
from public.users u
where u.current_book is not null
on conflict (telegram_id, book_id) do nothing;

alter table public.users drop column if exists current_position;
alter table public.users drop column if exists streak;
alter table public.users drop column if exists last_read_date;
