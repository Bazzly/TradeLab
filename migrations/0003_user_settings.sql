-- User-configurable risk parameters (README_forex.md Section 4.6) — account
-- equity, risk per trade, daily loss limit. Same RLS pattern as 0001: ENABLE
-- + FORCE (see 0002_app_role.sql for why FORCE alone isn't enough on Neon)
-- and only the tradelab_app role gets write access.

create table if not exists user_settings (
  user_id text primary key,
  account_equity numeric not null default 10000,
  risk_pct_per_trade numeric not null default 1.0,
  daily_loss_limit_pct numeric not null default 3.0,
  updated_at timestamptz not null default now()
);
alter table user_settings enable row level security;
alter table user_settings force row level security;
create policy "user_settings_owner_all" on user_settings
  for all
  using (user_id = current_setting('app.current_user_id', true))
  with check (user_id = current_setting('app.current_user_id', true));

grant select, insert, update on user_settings to tradelab_app;
