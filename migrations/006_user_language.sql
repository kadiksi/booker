-- Язык интерфейса Telegram для локализации напоминаний и будущего UI.

alter table public.users add column if not exists telegram_language_code text not null default 'en';
