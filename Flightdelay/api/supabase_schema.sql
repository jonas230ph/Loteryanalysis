create table if not exists public.flightaware_delay_totals (
  id bigserial primary key,
  run_id text not null,
  date date not null,
  day_offset integer not null,
  page_label text not null,
  total_delays_within_into_or_out_of_united_states integer not null,
  total_cancellations_within_into_or_out_of_united_states integer not null,
  source_url text not null,
  scraped_at timestamptz not null
);

create index if not exists idx_flightaware_delay_totals_run_id
  on public.flightaware_delay_totals (run_id);

create index if not exists idx_flightaware_delay_totals_scraped_at
  on public.flightaware_delay_totals (scraped_at desc);
