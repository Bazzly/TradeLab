-- Least-privileged role for the app to connect as (README_forex.md Section
-- 3.1, 11). Run this with the Neon owner connection string — it creates a
-- role the OWNER connection string should never be used for at runtime.
--
-- Why this exists: Neon's default `<project>_owner` role has BYPASSRLS,
-- which makes every RLS policy in 0001_init.sql a no-op for that role,
-- REGARDLESS of FORCE ROW LEVEL SECURITY (BYPASSRLS overrides FORCE too —
-- this was verified against a live database: with the owner role, two
-- different `app.current_user_id` sessions could read AND write each
-- other's journal_entries rows). A role without BYPASSRLS is the only way
-- to make RLS actually enforce anything on Neon's free tier.
--
-- Set the password out-of-band (psql `\password tradelab_app`, or an
-- `ALTER ROLE ... PASSWORD` run manually) — never commit a real password
-- into a migration file. This script creates the role with a placeholder
-- that must be changed before use.

do $$
begin
   if not exists (select from pg_roles where rolname = 'tradelab_app') then
      create role tradelab_app with login password 'CHANGE_ME_BEFORE_USE' nobypassrls;
   end if;
end
$$;

grant usage on schema public to tradelab_app;
grant select, insert, update, delete on journal_entries, strategies, subscriptions to tradelab_app;
grant select, insert on candles to tradelab_app;

-- After running this migration:
-- 1. ALTER ROLE tradelab_app WITH PASSWORD '<a real generated secret>';
-- 2. Build DATABASE_URL for secrets.toml / Streamlit Cloud secrets using
--    tradelab_app + that password (same host/port/dbname as the owner DSN,
--    different user/password) — this is what the running app should use.
-- 3. Keep the original owner connection string only for running migrations
--    (e.g. as a separate, not-committed NEON_ADMIN_DATABASE_URL) — the app
--    itself should never hold owner/BYPASSRLS credentials.
