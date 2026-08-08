-- One versioned snapshot is easier to publish atomically than several related
-- tables. The public can read lottery data, while only the service role writes.
create table if not exists public.mobile_snapshots (
    id text primary key check (id = 'current'),
    payload jsonb not null,
    refreshed_at timestamptz not null default now()
);

alter table public.mobile_snapshots enable row level security;

drop policy if exists "Public can read current mobile snapshot" on public.mobile_snapshots;
create policy "Public can read current mobile snapshot"
on public.mobile_snapshots
for select
to anon, authenticated
using (id = 'current');
