-- Заменить IANA timezone на фиксированный сдвиг от UTC (минуты), выставляемый по «времени с телефона» при настройке напоминаний.

alter table public.users drop column if exists timezone;

alter table public.users add column if not exists utc_offset_minutes int not null default 0;

comment on column public.users.utc_offset_minutes is
    'Смещение «местных» часов от UTC в минутах (восток +); задаётся при настройке напоминания по текущему времени на телефоне.';
