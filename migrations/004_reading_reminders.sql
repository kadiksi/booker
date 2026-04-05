-- Per-user reading nudges: local time slots + IANA timezone on users.

alter table public.users add column if not exists timezone text not null default 'UTC';

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
