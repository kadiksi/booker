-- If user_books was created with a streak column, remove it (optional one-off).

alter table public.user_books drop column if exists streak;
