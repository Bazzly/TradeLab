-- Core schema for TradeLab MVP (Neon Postgres).
-- Every user-scoped table enforces Row-Level Security keyed on the
-- app.current_user_id session setting (README_forex.md Section 3.2) — the
-- app sets this via lib/db/connection.py per connection. RLS is the tenancy
-- boundary, not application-layer filtering alone.
--
-- FORCE ROW LEVEL SECURITY is set on every such table because Postgres
-- exempts a table's OWNER from its own RLS policies by default. This alone
-- is NOT sufficient on Neon, though: the default `<project>_owner` role also
-- has the BYPASSRLS attribute, which skips RLS unconditionally — FORCE or
-- not. The app must connect as a separate, least-privileged role without
-- BYPASSRLS; see migrations/0002_app_role.sql.

create extension if not exists pgcrypto;

create table if not exists candles (
  asset text not null,
  timeframe text not null,
  time timestamptz not null,
  open numeric not null,
  high numeric not null,
  low numeric not null,
  close numeric not null,
  volume numeric not null,
  primary key (asset, timeframe, time)
);
create index if not exists candles_asset_timeframe_time_idx
  on candles (asset, timeframe, time desc);

create table if not exists strategies (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  name text not null,
  setup_type text not null,
  rules jsonb not null,
  created_at timestamptz not null default now()
);
alter table strategies enable row level security;
alter table strategies force row level security;
create policy "strategies_owner_all" on strategies
  for all
  using (user_id = current_setting('app.current_user_id', true))
  with check (user_id = current_setting('app.current_user_id', true));

create table if not exists journal_entries (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  date date not null,
  asset text not null,
  direction text not null check (direction in ('LONG', 'SHORT')),
  entry numeric not null,
  stop_loss numeric not null,
  take_profit numeric not null,
  position_size numeric not null,
  risk_amount numeric not null,
  strategy_id uuid references strategies (id) on delete set null,
  timeframe text not null,
  chart_screenshot_url text,
  reason_for_entry text not null,
  reason_for_exit text,
  result text check (result in ('WIN', 'LOSS', 'BREAKEVEN', 'OPEN')),
  r_multiple numeric,
  mistakes text[] not null default '{}',
  emotional_state text,
  lessons_learned text,
  created_at timestamptz not null default now()
);
alter table journal_entries enable row level security;
alter table journal_entries force row level security;
create policy "journal_entries_owner_all" on journal_entries
  for all
  using (user_id = current_setting('app.current_user_id', true))
  with check (user_id = current_setting('app.current_user_id', true));

-- Cached from a polled Stripe API call (Section 3.4) — Streamlit Community
-- Cloud has no route to receive webhooks. Written only by the billing
-- service, never directly by user-facing code paths.
create table if not exists subscriptions (
  user_id text primary key,
  stripe_customer_id text not null,
  stripe_subscription_id text,
  status text not null default 'free'
    check (status in ('free', 'active', 'past_due', 'canceled')),
  price_id text,
  current_period_end timestamptz,
  updated_at timestamptz not null default now()
);
alter table subscriptions enable row level security;
alter table subscriptions force row level security;
create policy "subscriptions_owner_read" on subscriptions
  for select
  using (user_id = current_setting('app.current_user_id', true));
