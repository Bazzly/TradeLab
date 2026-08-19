-- Paper Trading Bot trade log (README_forex.md Section 11, README_forex.md
-- Section 8's Phase 8 "Paper Trading" milestone). Deliberately NOT
-- per-user/RLS-scoped, unlike journal_entries and user_settings — this is a
-- single shared, public demonstration log of what a rules-based system
-- would have done, not private user data. Same precedent as the `candles`
-- table in 0001_init.sql, which also carries no RLS for the same reason.

create table if not exists bot_trades (
  id uuid primary key default gen_random_uuid(),
  asset text not null,
  setup_type text not null,
  direction text not null check (direction in ('LONG', 'SHORT')),
  entry_zone_low numeric not null,
  entry_zone_high numeric not null,
  entry_price numeric,
  stop_loss numeric not null,
  target numeric not null,
  risk_reward_ratio numeric not null,
  confidence_score numeric not null,
  reasons text[] not null default '{}',
  confirmation_factors text[] not null default '{}',
  status text not null default 'PENDING'
    check (status in ('PENDING', 'OPEN', 'CLOSED', 'EXPIRED')),
  signal_timestamp timestamptz not null,
  entry_filled_at timestamptz,
  closed_at timestamptz,
  exit_price numeric,
  exit_reason text check (exit_reason in ('STOP', 'TARGET')),
  r_multiple numeric,
  created_at timestamptz not null default now()
);
create index if not exists bot_trades_status_idx on bot_trades (status);
create index if not exists bot_trades_asset_setup_idx on bot_trades (asset, setup_type);

grant select, insert, update on bot_trades to tradelab_app;
