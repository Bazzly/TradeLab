# TradeLab — AI-Powered Forex & Crypto Trading Education and Analysis Platform

> **Read this file first.** This README is the build specification for an agentic AI (Claude Code, or any coding agent) to use as the source of truth when scaffolding, developing, and extending this project. It is not a pitch deck and not financial advice — it's an engineering spec for a personal trading research and education tool.

---

## 0. What This Project Is (and Isn't)

**Is:**
- A personal learning, research, backtesting, and journaling platform for forex/crypto trading.
- A rules-based, evidence-driven system: every signal, strategy, and dashboard number must be traceable to a defined rule or calculation.
- A tool that makes uncertainty, risk, and limitations visible rather than hidden.

**Is not:**
- A signal-selling service, a "get rich quick" bot, or an auto-trader that guarantees profits.
- A system that presents backtested results on small samples as proof of future performance.
- A place where hype, guesswork, or unverified "strategies" get treated as fact.

**Non-negotiable design law:** `DATA → ANALYSIS → TESTING → SIMULATION → REVIEW → IMPROVEMENT`. No feature ships that skips a step in this chain.

---

## 1. Instructions for the Agentic AI

If you are an AI agent building this project:

1. **Do not build everything at once.** Follow the phased roadmap in Section 8. Each phase must be functional and tested before starting the next.
2. **Start with the MVP in Section 9**, not the full feature list in Section 2 onward. The full spec exists so you understand where the architecture needs to extend to — not as a Sprint 1 checklist.
3. **Treat Section 7 (Anti-Hype & Anti-Bias Rules) as hard constraints**, not style guidance. Any generated copy, signal, or UI element that violates them is a bug.
4. **Ask before assuming a broker/exchange/data provider.** Data provider choice affects architecture (rate limits, websocket support, historical depth). Confirm before hard-coding one.
5. **No real-money execution in early phases.** Paper trading / simulation only until the user explicitly asks for live-broker order execution, and even then, execution should be opt-in, confirmable, and heavily gated (see Section 6.9).
6. **Every statistic must state its sample size.** A win rate or Sharpe ratio without a trade count next to it is not allowed in any UI or report.
7. **Keep the architecture modular.** New assets, indicators, strategies, and data providers should be pluggable without rewriting core engines.

---

## 2. Core Philosophy (governs every feature)

- Explain **why**, never just **what**. A signal must say why it exists, not just LONG/SHORT.
- Distinguish confidence levels explicitly: Strong / Moderate / Weak / Conflicting / No-trade.
- Never call a strategy "profitable" on a small sample. Define a minimum trade count (suggest ≥100 trades, or note statistical significance) before displaying performance claims as anything more than "preliminary."
- Show drawdowns and losing streaks as prominently as wins.
- No feature should let the user (or the system) skip risk management to chase an entry.

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (Web)                        │
│  Dashboard · Charting · Journal UI · Strategy Lab · Learning │
└───────────────────────────┬───────────────────────────────────┘
                             │ REST + WebSocket
┌───────────────────────────▼───────────────────────────────────┐
│                        BACKEND API LAYER                       │
│  Auth · User Settings · Journal API · Strategy API · Signals   │
└───────┬───────────┬───────────┬───────────┬───────────┬────────┘
        │           │           │           │           │
   ┌────▼───┐  ┌─────▼────┐ ┌───▼────┐ ┌────▼─────┐ ┌───▼──────┐
   │ Market │  │ Technical│ │Backtest│ │  Signal  │ │  Trade   │
   │  Data  │  │ Analysis │ │ Engine │ │  Engine  │ │  Review  │
   │Service │  │  Engine  │ │        │ │          │ │   (AI)   │
   └────┬───┘  └─────┬────┘ └───┬────┘ └────┬─────┘ └───┬──────┘
        │            │          │           │           │
   ┌────▼────────────▼──────────▼───────────▼───────────▼─────┐
   │                    DATA LAYER (Postgres +                  │
   │           TimescaleDB/InfluxDB for OHLCV time-series)      │
   └──────────────────────────────────────────────────────────┘
        │
   ┌────▼──────────────────────────────────────────────────────┐
   │  External: Forex/Crypto Data APIs · Economic Calendar API  │
   │  · Broker/Exchange APIs (paper trading first) · News Feed  │
   └──────────────────────────────────────────────────────────┘
```

### 3.1 Tech Stack (decided — Python/Streamlit, $0 hosting)

Priorities driving these choices: **Python end-to-end** (per explicit preference), stay on genuinely-free hosting tiers, support multi-user auth/tenancy without Supabase, and make subscription gating (free vs. paid features) straightforward to add later.

| Layer | Decision | Why |
|---|---|---|
| App framework | **Streamlit** (Python), multipage app (`Home.py` + `pages/`) | Single Python codebase for UI + logic; matches the quant/pandas-native ecosystem the backtesting engine needs anyway |
| Hosting | **Streamlit Community Cloud** (share.streamlit.io), free tier — live at [tradelab.streamlit.app](https://tradelab.streamlit.app/) | Free hosting tied directly to a GitHub repo; zero infra to manage. Constraint: app sleeps on inactivity, ~1 CPU/1GB RAM, ephemeral filesystem (no local file storage between deploys/restarts) |
| Database | **Neon** (serverless Postgres), free tier | Genuinely free (not a trial), real Postgres incl. Row-Level Security — needed since Streamlit's filesystem isn't persistent and Supabase is explicitly excluded |
| Auth | **Streamlit native auth** (`st.login()` / `st.user`, OIDC) backed by a free OIDC provider (e.g. Google or Auth0 free tier) | Built into Streamlit 1.42+, no custom password handling; identity (`st.user.email`) is the tenancy key into Neon |
| Tenancy enforcement | Postgres **Row-Level Security** on Neon, keyed on a session-scoped `app.current_user_id` setting the app sets per request, with the app connecting as a dedicated **`tradelab_app` role (no BYPASSRLS)** — see Section 11's 2026-08-19 entry | DB-enforced isolation, not just app-layer filtering. The app must NOT connect as Neon's default owner role: that role has BYPASSRLS, which silently disables RLS for it entirely, verified the hard way against a live database |
| Charts | **Plotly** (`st.plotly_chart`) for candlesticks + equity curves | First-class Streamlit support, handles OHLCV candlesticks and stats charts alike |
| Indicators/Backtesting | Python (pandas, numpy; **vectorbt** once backtesting depth requires it) | No longer deferred — this was always the natural fit once the app itself is Python |
| "Live" updates | `st.fragment(run_every=...)` periodic re-run on the dashboard fragment | Streamlit's execution model (rerun-on-interaction) isn't websocket-native; polling on an interval is the idiomatic substitute for MVP |
| Payments/Subscriptions | **Stripe** (Checkout + Customer Portal), status read via **polling the Stripe API** (cached, short TTL) rather than webhooks | Streamlit Community Cloud has no custom HTTP route for a webhook receiver; polling avoids standing up a second hosted service. Revisit with a small serverless webhook receiver only if polling latency becomes a real problem |
| Notifications | Email (Resend free tier) to start; Streamlit has no push/websocket channel of its own | Alerts for signals, journal reminders, news events |
| Economic Calendar | **Static, zero-API list** (`lib/economic_calendar/static.py`) — FOMC, ECB, US jobs report | FMP and Finnhub both confirmed paid-only for this specific endpoint (verified live against real keys — `402`/`403` respectively), despite both requiring a key on their free tier too. Trading Economics' old no-signup "guest" access is also dead (confirmed 2026-08-19). Rather than keep chasing commercial APIs, sourced the highest-impact recurring events directly from official calendars (Fed, ECB) — free forever, can't be paid-gated out from under us. Trade-off: not a full country-by-country feed, and deliberately excludes CPI (no fixed release-day rule, and BLS blocks automated verification of exact dates) |
| Trade Review AI (LLM) | **Google Gemini** (`gemini-2.5-flash`, free-tier API key) | Chosen specifically because it has a genuinely free, ongoing tier — unlike Claude/OpenAI, which only give one-time trial credits then bill per token |

### 3.2 Data Architecture Notes

- **Market data**: cache OHLCV candles per (asset, timeframe) in Neon Postgres, indexed on (asset, timeframe, time); never recompute historical candles from scratch on every rerun.
- **Indicators**: compute on ingest and store, or compute on-demand with `st.cache_data`-backed memoization keyed by (asset, timeframe, indicator, params) — Streamlit's own caching covers what Redis would have done at MVP scale.
- **Multi-timeframe engine**: reads from the same normalized candle store; never duplicate fetch logic per timeframe.
- **Provider abstraction**: define an internal `MarketDataProvider` protocol (Python `Protocol`/ABC) so forex/crypto data sources can be swapped or added without touching downstream engines. MVP providers (Section 3.3) implement this interface.
- **Tenancy**: every table holding user data (journal, strategies, settings) enforces Postgres Row-Level Security keyed on the authenticated user's id; the app sets the session-scoped `app.current_user_id` setting (`set_config(..., is_local=false)`, see `lib/db/connection.py`) once per connection — no cross-user data access via app-layer checks alone. The app connects as the restricted `tradelab_app` role, never Neon's owner role (Section 3.1, Section 11).
- **Ephemeral filesystem caveat**: never write anything that needs to survive a redeploy (uploaded screenshots, exports) to local disk on Streamlit Community Cloud — use Neon (structured data) or object storage (e.g. Cloudflare R2 free tier) for files if/when the journal needs chart-screenshot uploads.

### 3.3 Market Data Providers (decided)

| Asset class | Provider | Why |
|---|---|---|
| Forex (EUR/USD, GBP/USD, etc.) | ~~OANDA v20 REST API~~ → **Twelve Data** (free-tier API key) | OANDA is a regulated broker requiring KYC/residency checks and rejected the user's signup outright by country ("OANDA cannot accept new clients from your country of residence") — confirmed live, not a hypothetical. Twelve Data is a pure market-data API, no brokerage account or KYC involved, so that blocker doesn't apply. `lib/market_data/oanda.py` is kept for anyone OANDA does accept, or its future paper-trading-broker role (Twelve Data is data-only, not a broker) |
| Crypto (BTC/USD, etc.) | ~~Binance public REST API~~ → **Coinbase Exchange public REST API** (`api.exchange.coinbase.com`) | Free, no API key required. Binance.com returns HTTP 451 (geo-blocked) from Streamlit Community Cloud's US-hosted infra, discovered when the deployed app failed with that exact error — Coinbase's public candle endpoint isn't blocked there. Its granularity buckets (60/300/900/3600/21600/86400s) map cleanly onto our timeframes too. |

Both are free indefinitely at MVP scale (no card required, no trial expiry). If usage later exceeds Twelve Data's free-tier limits, Coinbase's geo-availability changes, or a live-execution broker is needed, revisit per Section 11.

### 3.4 Payment/Subscription Gating

- Stripe Checkout + Customer Portal handle signup, plan changes, and cancellation — never build custom card-collection UI.
- Subscription status cached from a polled Stripe API call into a `subscriptions` table (Neon), keyed by user id, with a short TTL (e.g. re-check on login and every few hours) rather than real-time webhooks (Section 3.1).
- Feature gating is enforced in the Python code path that renders/serves the feature, never client-side only — Streamlit has no "client" separate from the server anyway, but the same discipline applies: check entitlement before computing/returning the paid result, not just before rendering a button.
- Free tier scope and paid-tier feature list are a product decision, not an engineering one — confirm with the user before hard-coding which features sit behind the paywall (see Section 11).

---

## 4. Core Engines (Modules)

Each engine below should be its own service/module with a clear interface, independently testable.

1. **Market Data Service** — ingest, normalize, cache OHLCV + volume across pairs/assets and timeframes (1m–1W).
2. **Technical Analysis Engine** — indicators (MA, RSI, MACD, ATR), support/resistance detection, trend/structure classification, volatility measurement.
3. **Multi-Timeframe Analysis Engine** — aggregates TA Engine outputs across timeframes per asset; outputs a structured confluence report (see Section 5).
4. **Signal Engine** — rules-based, consumes Multi-Timeframe output; emits structured signal objects only when predefined criteria are met (Section 5.2).
5. **Backtesting Engine** — runs strategy rule sets against historical data; computes performance statistics (Section 5.3); supports walk-forward and out-of-sample splits.
6. **Risk Management Engine** — position sizing, stop/target calculation, exposure and correlation checks, daily/weekly loss limits.
7. **Trading Journal Service** — CRUD for trades, screenshot/chart attachment, tagging, mistake/lesson tracking.
8. **Trade Review AI** — post-trade analysis using journal + original signal/strategy rules to assess process quality (separate from P&L outcome).
9. **Market Scanner** — runs Signal Engine + ranking logic across a watchlist; outputs the four-tier leaderboard (Section 5.5).
10. **Economic Calendar Service** — ingests scheduled macro events; flags high-impact windows for the Risk Engine and Dashboard.
11. **Learning/Mentor Engine** — serves the structured curriculum, tracks progress, generates quizzes/exercises, gates advanced content.
12. **Billing & Access Control Service** — polls Stripe for subscription state (Section 3.4), caches it in Neon, exposes an entitlement check other engines/pages call to gate paid features.

---

## 5. Key Data Contracts

Define these as shared types/schemas early — everything else depends on them.

### 5.1 Multi-Timeframe Analysis Output
```
{
  asset, timestamp,
  higherTimeframeTrend, intermediateTrend, lowerTimeframeStructure,
  keySupportResistance: [...],
  momentum, volatility,
  possibleEntryZones: [...], invalidationLevels: [...], targets: [...],
  riskRewardRatio,
  confirmationLevel: "STRONG" | "MODERATE" | "WEAK" | "CONFLICTING" | "NO_TRADE",
  conflictingSignals: [...]
}
```

### 5.2 Trading Signal
```
{
  id, asset, direction: "LONG" | "SHORT", timeframe, setupType,
  entryZone, stopLoss, takeProfitLevels: [...], riskRewardRatio,
  confirmationFactors: [...], invalidatingConditions: [...],
  confidenceScore, reasons: [...], marketConditions, timestamp
}
```
Rule: **no signal object is created unless predefined criteria are met.** "No qualifying setup" is a valid, expected, and common output.

### 5.3 Strategy Performance Report
```
{
  strategyId, sampleSize (tradeCount), dateRange,
  winRate, lossRate, profitFactor, expectancy,
  avgWin, avgLoss, maxDrawdown, sharpeRatio,
  consecutiveWins, consecutiveLosses,
  monthlyPerformance: [...], annualizedPerformance,
  outOfSample: boolean, walkForwardTested: boolean,
  overfittingFlags: [...], limitations: [free text, required field]
}
```
Rule: `limitations` is a **required, non-empty field** on every report. The system should refuse to render a performance report without it.

### 5.4 Journal Entry
```
{
  id, date, asset, direction, entry, stopLoss, takeProfit, positionSize,
  riskAmount, strategyId, timeframe, chartScreenshotUrl,
  reasonForEntry, reasonForExit, result, rMultiple,
  mistakes: [...], emotionalState, lessonsLearned
}
```

### 5.5 Scanner Leaderboard
Four fixed tiers only: `HIGH_QUALITY_SETUPS`, `WATCHLIST`, `WEAK_SETUPS`, `NO_TRADE`. The scanner must be allowed to return an empty `HIGH_QUALITY_SETUPS` list — never force-fill it.

---

## 6. Non-Functional Requirements

1. **Auditability** — every signal and performance number must be traceable back to the rule/calculation that produced it (store the rule version alongside results).
2. **Statistical honesty** — enforce minimum sample size thresholds in code, not just UI copy, before labeling anything "profitable" or "reliable."
3. **No survivorship bias** — backtests must include losing periods and drawdowns by default; there is no "hide losses" toggle.
4. **Idempotent backtests** — same strategy + same data + same params always produces the same report (seed any randomized Monte Carlo runs and store the seed).
5. **Security** — standard auth best practices; never store broker API keys in plaintext; secrets in environment/secret manager, not in the repo.
6. **Rate-limit resilience** — market data and news API calls must be cached and rate-limit-aware; the system should degrade gracefully (stale-but-labeled data) rather than crash.
7. **Timezone/session correctness** — all timestamps stored in UTC; trading-session logic (Sydney/Tokyo/London/New York) computed at the display layer.
8. **Explainability over automation** — favor "here's what the data shows and why" UI over black-box scores.
9. **Execution gating (future phase)** — if/when live order execution is added, require explicit per-trade confirmation, a hard daily-loss circuit breaker, and no default "auto-execute on signal" mode.
10. **Payment security** — all card/payment data handled exclusively by Stripe Checkout/Elements; the app never receives or stores raw payment details. Subscription/entitlement checks happen server-side only.
11. **Tenancy isolation** — Postgres Row-Level Security (Section 3.2) is the enforcement boundary for multi-user data, not just application-layer filtering.

---

## 7. Anti-Hype and Anti-Bias Rules (hard constraints)

The system must **never**:
- Guarantee profits or state a strategy "cannot fail."
- Present speculation, backtested results, or a single scanner hit as certainty.
- Encourage revenge trading, oversized position sizing, or excessive leverage.
- Recommend a trade because it's popular rather than because it meets defined criteria.
- Treat one successful backtest as proof of future profitability.
- Hide losing periods, drawdowns, or cherry-pick favorable date ranges.

Every strategy report, signal, and dashboard summary must show assumptions, sample size, and limitations alongside the results.

---

## 8. Development Roadmap

| Phase | Focus | Key Deliverables |
|---|---|---|
| 1 | Trading Education | Structured curriculum content model, progress tracking, beginner→advanced content for all listed topics |
| 2 | Market Data | Provider integration, normalized OHLCV storage, historical backfill, live feed ingestion |
| 3 | Market Dashboard | Multi-asset dashboard UI, price/trend/volatility display, multi-timeframe selector |
| 4 | Technical Analysis | Indicator library (MA, RSI, MACD, ATR), support/resistance + structure detection |
| 5 | Strategy Builder | Rule-definition UI/DSL for entries/exits/stops/sizing, strategy storage |
| 6 | Backtesting | Historical + walk-forward + out-of-sample testing, performance stats engine |
| 7 | Signal Engine | Rules-based signal generation from Multi-Timeframe Engine, confidence scoring |
| 8 | Paper Trading | Simulated order execution, simulated P&L tracking, comparison vs. trading rules |
| 9 | Trading Journal | Trade CRUD, screenshots, tagging, mistake/lesson tracking, history analysis |
| 10 | AI Trade Analysis | Trade Review AI, process-vs-outcome separation, weakness pattern detection |
| 11 | Advanced Analytics | Market Scanner, Economic Calendar integration, correlation/exposure tools, Monte Carlo |
| 12 | Production Deployment | Hardened auth, monitoring/logging, admin dashboard, deployment pipeline |

For each phase, before starting: confirm objectives, required APIs/data, DB schema changes, and test plan with the user if anything is ambiguous — don't silently assume a data provider or broker.

---

## 9. Recommended MVP (build this first)

Before touching Phases 3–12 in full, ship a thin vertical slice:

0. **Project scaffold**: Streamlit multipage app, Neon project (Postgres + RLS enabled), `st.login()` auth wired to a free OIDC provider, secrets via `.streamlit/secrets.toml` (local) / Streamlit Cloud secrets manager (hosted) — no Stripe integration required yet, but data models should anticipate a `subscriptions` table.
1. **One data source per asset class** — Twelve Data (forex: EUR/USD, GBP/USD) + Coinbase Exchange (crypto: BTC/USD) — on 3 timeframes (15m, 1H, 4H, 1D).
2. **Basic dashboard**: price, % change, trend direction, 2–3 core indicators (MA, RSI, ATR) — with plain-language explanations of what each reading means.
3. **Multi-Timeframe Analysis Engine v1**: trend/structure per timeframe + a simple confirmation-level classifier.
4. **Rules-based Signal Engine v1**: one well-defined setup type (e.g., "trend-aligned pullback to support/resistance") with full reasoning output — no black-box scoring yet.
5. **Basic Backtesting Engine (Python/pandas)**: run that one setup type against historical data, output win rate/profit factor/max drawdown/expectancy with sample size clearly shown.
6. **Trading Journal v1**: manual trade entry with the core fields (Section 5.4), scoped to the authenticated user via RLS, no AI review yet.
7. **Education module v1**: the first 4–5 beginner topics (market structure, candlesticks, support/resistance, risk management basics) as structured lessons.

Payment gating (Stripe) is architected for from day one (Section 3.4) but wired up once there's an actual paid feature to gate — don't build billing UI before there's something worth paying for.

Everything else in this README describes where the architecture must be able to grow — not what to build on day one.

---

## 10. Suggested Repository Structure

```
Home.py              # Streamlit entrypoint (landing/dashboard)
/pages
  1_Dashboard.py
  2_Strategy_Lab.py
  3_Backtesting.py
  4_Journal.py
  5_Learning.py
/lib
  /market_data        # MarketDataProvider protocol + Twelve Data + OANDA + Coinbase adapters, registry for routing
  /indicators          # Technical analysis indicator library (pandas)
  /engines              # Multi-timeframe, signal, backtest, risk engines
  /billing              # Stripe client + polled entitlement checks
  /db                    # Neon connection, RLS session setup, typed queries
  /schemas              # Shared dataclasses/pydantic models (signal, strategy, journal, subscription contracts)
/migrations           # DB migrations (Postgres, RLS policies) for Neon
/.streamlit
  config.toml
  secrets.toml.example
/docs
  architecture.md
  data-contracts.md
  roadmap.md
requirements.txt
README.md            # this file
```

---

## 11. Decisions Log & Remaining Open Questions

**Resolved (2026-08-18):**
- Backend language: Next.js/TypeScript end-to-end for MVP, Python quant service deferred until needed.
- Hosting: Vercel (free) + Supabase (free).
- User scope: **Multi-user**, enforced via Postgres RLS (mechanism changed 2026-08-19, see below).
- Market data: **OANDA practice API** (forex, also doubles as Phase 8 paper-trading broker) + Binance public API (crypto) — crypto provider later swapped to Coinbase, see 2026-08-19 entry below.
- Payments: **Stripe**, architected for from day one, wired up once a paid feature exists to gate (Section 3.4, Section 9) — unchanged, delivery mechanism changed below.

**Superseded (2026-08-19) — full pivot away from Supabase/Next.js to Python/Streamlit, per explicit request:**
- App framework + hosting: ~~Next.js/TypeScript on Vercel~~ → **Streamlit (Python) on Streamlit Community Cloud** (Section 3.1). The already-built Next.js scaffold was moved to a sibling `forex-nextjs-backup` directory rather than deleted, in case it's wanted later. **Live at https://tradelab.streamlit.app/** (deployed 2026-08-19).
- Database + auth: ~~Supabase~~ → **Neon (Postgres, free tier)** for data, **Streamlit native `st.login()`/OIDC** for auth. Multi-user tenancy is still Postgres RLS, just self-managed on Neon instead of Supabase-managed.
- Indicators/backtesting: not deferred anymore — Python (pandas/numpy, vectorbt later) is now the MVP language, not a future upgrade.
- Payment gating delivery: Stripe **webhooks** → Stripe **polling**, because Streamlit Community Cloud has no custom HTTP route to receive a webhook (Section 3.4).

**Resolved (2026-08-19, discovered in production):**
- Crypto data provider: ~~Binance public API~~ → **Coinbase Exchange public API** (Section 3.3). The deployed app failed with `451 Client Error` fetching Binance candles — Binance.com geo-blocks the US-hosted infrastructure Streamlit Community Cloud runs on. Coinbase's public candle endpoint isn't blocked there and wasn't a difficult swap since both are unauthenticated REST. Worth remembering if any *other* free API integration (OANDA, future providers) starts failing only in production and not locally — geo-blocking from the hosting region is a real, recurring risk with free public APIs and won't show up in local dev.

**Progress (2026-08-19) — MVP (Section 9) complete, plus the Market Scanner pulled forward from Phase 11:**
- All 7 MVP items shipped: Dashboard, Strategy Lab (Multi-Timeframe + Signal engines), Backtesting, Journal, Learning.
- Market Scanner (Section 4.9, 5.5) built ahead of its Phase 11 slot since it needed no new infra — it's just the existing Signal Engine run across a watchlist. Watchlist widened from BTC/USD alone to 8 Coinbase USD pairs (BTC, ETH, SOL, XRP, ADA, DOGE, LTC, LINK) across Dashboard/Strategy Lab/Backtesting/Scanner, since testing the scanner meaningfully needs more than one asset.
- Still blocked on user-supplied credentials: OANDA (forex data), OIDC provider (blocks real `st.login()` — Journal currently falls back to a manually typed dev user id).
- Everything built so far is crypto-only in practice, despite the architecture being asset-class-agnostic (`MarketDataProvider` protocol) — forex is code-complete (`lib/market_data/oanda.py`) but untested end-to-end for lack of an API key.

**Resolved (2026-08-19) — Neon connected, and a real RLS security bug found + fixed before any real user data touched it:**
- `DATABASE_URL` supplied, `migrations/0001_init.sql` applied, Journal verified end-to-end against the live database (real form submission through the actual Streamlit page → row landed in Neon → cleaned up test data).
- **Critical finding while verifying tenancy isolation**: with Neon's default `<project>_owner` role, RLS was a complete no-op — a "user B" session could read *and modify* "user A"'s journal entries, even with `FORCE ROW LEVEL SECURITY` set on every table. Root cause: Neon's owner role carries the `BYPASSRLS` role attribute, which Postgres documents as overriding RLS unconditionally — for the owner, FORCE ROW LEVEL SECURITY does nothing at all. This was **not** caught by policy review or by the migration applying cleanly; it only surfaced by actually testing cross-user isolation against the live database, which is why that test is worth keeping as a standing check on every future auth/tenancy change here.
- **Fix**: `migrations/0002_app_role.sql` creates a separate `tradelab_app` role without `BYPASSRLS`, granted only the table privileges it needs. `DATABASE_URL` (used by the running app) now points at this restricted role; the original owner connection string is kept separately as `NEON_ADMIN_DATABASE_URL`, used only to run migrations, never at app runtime. Re-verified with the same cross-user test: isolation now holds (read and write both correctly blocked).
- **Generalizes beyond Neon**: any managed Postgres whose default/admin role has superuser-like privileges will have the same problem — RLS policies must always be tested against the role the app actually authenticates as, not just checked for existing via `pg_policies`.

**Progress (2026-08-19) — Risk Management Engine (Section 4.6) built, closing the last unimplemented Core Engine:**
- `lib/engines/risk.py`: position sizing, open-risk exposure (from real Journal entries), daily loss limit checks, and a return-correlation matrix across the watchlist with warnings when a candidate trade is highly correlated with an existing open position — verified against real Coinbase data (BTC/ETH correlation came back at 0.83, in the range you'd expect).
- New `user_settings` table (`migrations/0003_user_settings.sql`) for persisted account equity / risk-per-trade / daily-loss-limit, same RLS pattern (ENABLE + FORCE + restricted role) as the rest — isolation re-verified with the same cross-user test used for the Journal fix.
- New Risk page. Caught and fixed one real bug while testing it live: an `st.rerun()` placed immediately after `st.success("Saved.")` fired before the success message could ever render — Streamlit already reruns automatically after a form submit, so the extra explicit rerun was both redundant and silently swallowing the user-facing confirmation. Removed.
- This closes out every Core Engine in Section 4 except Trade Review AI (needs an LLM API key) and Economic Calendar Service (needs a data provider) — both genuinely blocked on new credentials, unlike everything built so far.

**Resolved (2026-08-19) — Trade Review AI live-verified; Economic Calendar dropped commercial APIs entirely after both failed:**
- Trade Review AI: **Google Gemini**, `lib/engines/trade_review.py`, wired into the Journal page's "AI Trade Review" section. Verified live against a real key and a real closed trade — caught and fixed a real bug in the process: the initially-picked model id (`gemini-2.5-flash`) is deprecated for new users; the API's own error message named the replacement (`gemini-3.6-flash`), now in use. Output quality checked, not just "it returned 200" — it correctly graded a winning trade's process as flawed (stop moved early out of anxiety) rather than praising the win, which is the whole point of the process-not-outcome framing in the prompt.
- Economic Calendar: **~~Financial Modeling Prep~~ → ~~Finnhub~~ → static, zero-API list**. Both commercial providers were tried and both failed live-testing with a real key: FMP returns `402 Restricted Endpoint`, Finnhub returns `403 "You don't have access to this resource"` — same root mistake both times (a key requirement isn't the same as free-tier inclusion). Rather than keep guessing at more commercial APIs, pivoted to `lib/economic_calendar/static.py`: FOMC and ECB rate-decision dates sourced directly from federalreserve.gov and ecb.europa.eu (fetched 2026-08-19), plus US Non-Farm Payrolls computed via its well-established first-Friday-of-month rule. CPI is deliberately excluded — BLS blocks automated fetches of its release schedule (403), and publishing a specific CPI date without a verified source would be exactly the false precision Section 7 forbids. `fmp.py`/`finnhub.py` are kept only for anyone with a paid plan on either.
- Lesson for future provider claims in this doc: "requires an API key" and "included in the free tier of that key" are different facts, and only live-testing against a real key confirms the second one. Every "free-tier confirmed" claim above the 2026-08-19 entries that hasn't specifically been re-verified with a real key should be treated with the same skepticism until it has.

**Resolved (2026-08-19) — real login wired up and verified end-to-end by the user in an actual browser (not something I can automate — st.login() is a real redirect to Google's own consent screen):**
- OIDC provider: **Google**, via a Google Cloud OAuth client (External consent screen, test-user mode). `lib/auth.py` added as the shared identity helper for Journal/Risk, replacing duplicated inline logic in both pages. Fixed a real bug in the process: the original "is auth configured" check only tested whether the `[auth]` secrets *section* existed, which is true even with an empty `[auth.google]` block (exactly what `secrets.toml.example` ships with) — it now checks that `client_id`/`client_secret` are actually non-empty, or the dev-user-id fallback would have silently broken the moment `[auth]` existed at all, configured or not.
- Caught and fixed a real missing-dependency bug live: `st.login()` requires Authlib, which isn't pulled in by plain `streamlit` — `requirements.txt` now installs `streamlit[auth]`. First login attempt crashed with `StreamlitMissingAuthlibError`; fixed and the retry succeeded.
- This closes the "anyone can type any user id" gap flagged earlier — Journal/Risk now use the real, verified Google email as the RLS tenancy key once configured (falls back to the dev-user-id text box only when Google OAuth isn't set up, e.g. a fresh clone of this repo).
- **Still needs doing**: the same `[auth]`/`[auth.google]` values (with the deployed `redirect_uri`, not localhost) must be pasted into Streamlit Cloud's Settings → Secrets for login to work on the live app — verified locally only so far.

**Progress (2026-08-19) — forex wired up (code-complete, not yet live-verified — no OANDA key supplied yet):**
- Watchlist expanded to the five majors — EUR/USD, USD/JPY, GBP/USD, USD/CHF, AUD/USD — the standard beginner starting point (tightest spreads, most liquid). New `lib/market_data/registry.py` routes each asset to the right provider (OANDA for forex, Coinbase for crypto) so every page (Dashboard, Strategy Lab, Backtesting, Scanner, Risk's correlation check) works across both asset classes without page-level branching.
- Proactively fixed a bug *before* it could bite in production, by pattern-matching against the Binance pagination bug found earlier (Section 11, 2026-08-19 "MVP complete" entry): OANDA's candles endpoint caps at 5000 per request, and 15m granularity over 90 days is 8640 candles — would have silently truncated. `lib/market_data/oanda.py` now pages the request the same way `binance.py` does. Also now filters out OANDA's still-forming "incomplete" candle, matching the no-lookahead discipline the rest of the pipeline already follows.
- Also fixed a real UX bug caught while testing this change: since forex now sorts first in the combined asset list, every page's selectbox defaulted to a forex pair — meaning the default view became an error state (`OANDA_API_KEY is not set`) for anyone without OANDA configured, crypto included. `registry.default_asset()` now picks whichever asset class is actually usable, so the default view never breaks regardless of what's configured.
- **Not yet live-tested**: no OANDA credentials supplied yet, so the actual candle-fetching code, the 5000-candle pagination, and the "incomplete candle" filter are all unverified against real data — treat with the same skepticism as any other "should work" claim in this doc until it's been tested the way Coinbase/Neon/Gemini were.

**Superseded (2026-08-19) — OANDA rejected the user's signup outright; forex provider changed to Twelve Data:**
- The blocker above wasn't "hasn't gotten a key yet" — OANDA actively refused to open an account: *"OANDA cannot accept new clients from your country of residence."* OANDA is a regulated broker, so this is a real KYC/residency gate, not something a different signup flow works around.
- Provider changed to **Twelve Data** (Section 3.3) — a pure market-data API with no brokerage account or KYC, so country-of-residence doesn't block signup the same way. `lib/market_data/twelvedata.py` added, `registry.get_provider()`/`default_asset()` repointed at it. The pagination and no-lookahead discipline from the OANDA work carried over (Twelve Data also caps at ~5000 values per request).
- `lib/market_data/oanda.py` is kept, unused by default, for anyone OANDA does accept.
- **Twelve Data itself is also not yet live-verified** against a real, self-registered free key — only their shared "demo" key was tested (it did return real EUR/USD candles, a positive sign, but demo-key behavior isn't proof of real account free-tier terms — same caution as the FMP/Finnhub lesson above).

**Resolved (2026-08-19) — consolidated caching across pages to reduce free-tier API usage:**
- Every page (Dashboard, Strategy Lab, Backtesting, Scanner, Risk) was defining its own `@st.cache_data`-wrapped loader. Since Streamlit keys the cache by function identity, that meant zero cache sharing across pages — visiting Dashboard then Strategy Lab for the same asset triggered two independent API calls for identical data. New `lib/data.py` (`load_candles`, `load_joined_frame`) is now the single shared, cached entry point every page routes through, so the cache is shared across the whole session. Verified directly (not just "should work"): calling the same (asset, timeframe, days) twice hits the cache on the second call; a different timeframe correctly triggers a fresh fetch.
- Caught a real bug the regression suite exists to catch: while consolidating imports, `import streamlit as st` was accidentally dropped from Strategy Lab, breaking the page outright (`NameError: name 'st' is not defined`). Fixed immediately — this is exactly why every change in this doc gets a full 9-page headless regression pass before being called done, not just a visual check of the diff.
- Clarified for the record: none of the free-tier services wired up here (Neon, Twelve Data, Coinbase, Gemini, Finnhub/FMP) have a card on file — exceeding a free-tier limit means requests start failing (429s), not a surprise bill. The caching consolidation reduces the chance of hitting those limits and the app breaking under load, which is the real risk, not billing.

**Resolved (2026-08-19) — Twelve Data live-verified; found and fixed a real secrets-loading ordering bug in the process:**
- Real EUR/USD 1H candles confirmed via a self-registered free key (single test call, deliberately not repeated, given this conversation's usage-conscious context) — 120 candles for a 5-day window, matches expected count exactly.
- **Critical finding while verifying it through the actual Dashboard page** (not just a raw script): Streamlit only mirrors `secrets.toml` into `os.environ` lazily, the first time *anything* in the running process touches `st.secrets`. Every provider module (`oanda.py`, `twelvedata.py`, `trade_review.py`, `db/connection.py`, `fmp.py`, `finnhub.py`) read secrets via plain `os.environ.get(...)`, which is fine only if some other code has already touched `st.secrets` earlier in that process. Confirmed directly: a fresh process running Dashboard first (page 1 — the most likely real entry point) saw `TWELVEDATA_API_KEY` as unset even though it was genuinely configured, until a *different* page (Journal, via `lib.auth`) touched `st.secrets` first. This would have intermittently broken forex (and potentially DB/AI) in production depending on which page a session happened to load first — exactly the kind of bug that "it worked when I tested it" hides, since my earlier Journal/Risk-based tests always touched `st.secrets` before the pages that needed it.
- **Fix**: new `lib/secrets.py` (`get_secret()`) reads `st.secrets` directly — no ordering dependency — falling back to `os.environ` only for non-Streamlit contexts (scripts, migrations). Every module above switched to it. Re-tested the exact failing scenario (fresh process, Dashboard first, EUR/USD selected) — passes clean now.
- Also fixed a precision bug the live data made visible: prices were formatted at 2 decimals everywhere, fine for crypto (~$65,000) but wrong for forex majors (EUR/USD ~1.1607) — ATR literally rounded to `0.00`. Dashboard and Strategy Lab now use 5 decimals for forex, 2 for crypto.

**Progress (2026-08-19) — second Signal Engine setup type added: Supply & Demand + Fair Value Gap (`bot.md`):**
- Derived from a user-supplied trading-video transcript (`botguid.md`). Extracted only the mechanical trading rules; deliberately excluded the source's marketing content (a paid "trading robot"/Discord pitch with social-proof numbers) — that's someone else's product, not evidence of edge, and repeating it anywhere would violate Section 7.
- `lib/engines/zones.py` (displacement/zone/FVG/EMA200, folded into `multi_timeframe.compute_frame()`), `lib/engines/signal_supply_demand.py` (the signal generator, same `TradingSignal` contract as the existing setup), and a `signal_fn` seam added to `lib/engines/backtest.py` so both setups share one simulation/stats engine rather than duplicating it.
- `bot.md` Section 3 posed six open questions (displacement threshold, take-profit definition, small-candle handling, multi-FVG confidence scaling, ORB's higher timeframe, thin-session handling) — resolved with explicit ATR-relative defaults documented in `zones.py`'s docstring rather than picked silently; multi-FVG confidence scaling specifically was *not* implemented (documented as a real simplification, not hidden) since the fixed 3-candle displacement window only ever produces one gap to check.
- **Live-verified**, not just unit-tested: real BTC/USD (124 qualifying bars of 2160, 3 completed backtest trades over 90 days) and real EUR/USD (72 qualifying bars of 2160) both produce sane entry zones, stops, targets, and R:R. Wired into Strategy Lab and Backtesting via a Setup selector; full 9-page regression passes.
- Setup B (Opening Range Breakout scalp) implemented immediately after — see the dedicated entry below.

**Resolved (2026-08-19) — real timestamp bug found while preparing for session-time logic (Setup B needs an exact 09:30 NY open), fixed across every provider:**
- `datetime.fromtimestamp(epoch)` without a `tz` argument converts to the *server's local timezone*, not UTC — confirmed directly (a full hour of skew on a non-UTC test machine), despite `Candle.time`'s contract requiring UTC (Section 6.7). Coinbase and Binance both had this. It happened to look correct in production only because Streamlit Community Cloud's containers default to UTC — coincidence, not correctness, and exactly the kind of bug that stays invisible until either the deployment environment changes or a feature (like session-time detection) actually depends on the timestamp being right.
- Fix: `lib/market_data/provider.py` gained `epoch_to_utc_naive()`, an explicit UTC conversion every provider now routes through instead of calling `datetime.fromtimestamp()` directly.
- Also found and fixed a second, related bug in the same sweep: OANDA's request builder did `cursor.isoformat() + "Z"`, which is only valid for a *naive* datetime — every real caller (`lib/data.py`) passes timezone-*aware* UTC datetimes, which already end in `+00:00`, so this silently built a malformed double-marked timestamp (`...+00:00Z`) that OANDA's API would have rejected. Never caught earlier because OANDA has never been tested against a real key (Section 11's OANDA-rejected-by-country entry) — dormant code with a real bug in it. Fixed with an explicit aware/naive-safe conversion.
- Twelve Data's request now explicitly passes `timezone: UTC` rather than relying on its unverified default (documented as "Exchange" time for some endpoints) — removes an assumption instead of leaving it implicit.
- Re-verified live after the fix: Coinbase and Twelve Data's most recent candle both land within a minute of actual current UTC time, confirmed directly against `datetime.now(UTC)`, not just "no exception raised."

**Progress (2026-08-19) — third Signal Engine setup type: Opening Range Breakout (`bot.md` Setup B), completing `bot.md`:**
- `lib/engines/orb.py` (NY-session range detection via stdlib `zoneinfo`, single-candle displacement breakout) + `lib/engines/signal_orb.py`, sharing Setup A's FVG/EMA200 confirmation pattern and the same backtest `signal_fn` seam. New `lib/data.py` loader (`load_orb_frame`) for its 15m base timeframe.
- Adapted the source's 5-minute-chart opening range onto our supported 15m granularity (bot.md Section 3, questions 5-6) — 09:30-09:45 NY maps exactly onto one 15m candle, so no approximation was needed there. Trend confirmation uses 1H/4H (not Setup A's 1H/4H/1D) — a faster filter matched to the faster entry timeframe.
- DST correctness verified directly, not assumed: the range-candle detection landed on 13:30 UTC (= 09:30 EDT) for an August test window — confirms `zoneinfo`-based conversion, not a naive fixed-offset one that would break every March/November.
- **Live-verified, including a real debugging pass, not just a clean first run**: BTC/USD found 39 qualifying signals over 20 days with sane entry/stop/target/R:R. EUR/USD initially returned zero signals across two different windows (20 days, then 60 days) — traced the full funnel by hand (range detection → breakout → FVG → EMA200 → trend direction → target → R:R) rather than assuming a bug, and found every stage was working: 106 of 140 FVG-confirmed breakouts passed trend+EMA, but every one of them landed at R:R 1.16-1.41, just under the 1.5 minimum. ORB's stop spans the *entire* opening range — inherently wider than Setup A's tight zone-based stop — so lower R:R is a real, expected property of this setup, not a symptom of a broken implementation. Worth remembering next time a setup returns zero signals: trace the funnel stage-by-stage before assuming it's broken.
- **Found and fixed a real bug in the process, unrelated to ORB itself but only surfaced by needing exact session-time correctness**: `datetime.fromtimestamp(epoch)` without an explicit `tz` argument silently uses the *server's local timezone*, not UTC — present in Coinbase and Binance's provider code, confirmed with a full hour of skew on a non-UTC machine. It only ever looked correct because Streamlit Community Cloud's containers default to UTC — coincidence, not correctness — and would have quietly misaligned every ORB session-window calculation on any environment where that coincidence didn't hold. Fixed with an explicit `epoch_to_utc_naive()` helper (`lib/market_data/provider.py`) every provider now routes through; also fixed a dormant, never-live-tested bug in OANDA's request builder that would have sent a malformed double-UTC-marked timestamp (`...+00:00Z`) once given the timezone-aware datetimes every real caller actually passes.
- `bot.md` is now fully implemented — both Setup A and Setup B built, live-verified, and wired into Strategy Lab/Backtesting via the same Setup selector.

**Resolved (2026-08-19) — deployed app broke immediately after the previous push, real Python-version incompatibility, fixed and confirmed empirically:**
- The live app threw `ImportError` on Strategy Lab: `from lib.data import load_joined_frame, load_orb_frame`. Root cause: three files (`lib/data.py`, `lib/market_data/provider.py`, `lib/market_data/oanda.py`) used `from datetime import UTC` — that alias for `timezone.utc` was only added in **Python 3.11**, and this repo never pinned a Python version, so Streamlit Community Cloud was free to deploy on whatever its own default is (evidently older than 3.11).
- **Confirmed the exact mechanism, not just a plausible theory**: ran `from datetime import UTC` against this machine's own Python 3.9 install and got the identical error class (`ImportError: cannot import name 'UTC' from 'datetime'`) that the deployed app reported. Fixed by switching all three files to `timezone.utc`, which has worked since Python 3.2 — confirmed the fix imports cleanly on that same Python 3.9 install.
- **Also fixed proactively, before it could cause a second broken deploy**: `lib/engines/orb.py` evaluates `ZoneInfo("America/New_York")` at *module import time*, and minimal cloud Python containers frequently lack the OS-level IANA timezone database `zoneinfo` depends on — a well-documented, common gotcha for exactly this deployment shape. Added `tzdata` (the pure-Python fallback database) to `requirements.txt` pre-emptively, rather than waiting for a second round of "the app broke, why."
- **Root fix, not just a patch**: added `runtime.txt` (`python-3.11`) to pin Streamlit Cloud to a known Python version going forward — this whole bug class (code that works locally, breaks on a remote Python version nobody pinned) shouldn't be able to recur silently.
- Lesson for future code in this app: `datetime.UTC`, and more generally any very-recent-Python-only stdlib feature, is not safe to use without checking the pinned deployment version first — local `python3` being modern doesn't mean the deploy target is.

**Progress (2026-08-19) — Learning module (Section 4.11) substantially expanded, live examples added throughout:**
- 4 new lessons: Fair Value Gaps & Supply/Demand Zones, Trend Filters (Moving Averages & the 200 EMA), Opening Range Breakout, and a capstone ("How a Signal Actually Gets Built") that walks the full candles-to-`TradingSignal` pipeline. 8 lessons total, up from 4.
- Every lesson now has a **live example**: real current data pulled from the actual running engines (via the same cached `lib/data.py` loaders every other page uses), not static text — e.g. the Support & Resistance lesson shows *this asset's actual* trailing support/resistance right now, the capstone lesson lets you pick a setup and asset and literally runs `generate_signal`/`generate_supply_demand_signal`/`generate_orb_signal` live, showing "no qualifying setup" or a real signal exactly as Strategy Lab would.
- A few lessons (Candlesticks, Risk Management, Fair Value Gaps) gained short interactive quick-check quizzes (radio/number input + "Check answer" reveal) — verified end-to-end via `AppTest`, not just that the widgets render.
- Found and fixed an unrelated local-only issue while testing this: `.streamlit/secrets.toml`'s `[auth]` block had two active (uncommented) `redirect_uri` lines — invalid TOML, breaking every page that touches `st.secrets` (Journal, Risk) with a parse error. Not a code bug; a leftover from manually toggling between local/deployed values while debugging the redirect_uri_mismatch OAuth issue. Restored the local value as active, deployed value as the commented-out reference, matching the file's own documented convention.

**Note (2026-08-19) — a deploy of the above looked broken on Streamlit Cloud (`AttributeError` on `Lesson.live_example`) despite the pushed code being verified correct** (checked directly against `origin/main` — the field was there, on every lesson). Root cause was a stale Streamlit Cloud build, not a code issue — fixed by a manual reboot from the app's "Manage app" panel. Worth remembering: if a deploy ever looks like it silently didn't pick up a push, verify the code on GitHub first (rules out a code bug), then try a manual reboot before assuming something's wrong with the code.

**Progress (2026-08-19) — animated illustrative examples added to the top of every lesson:**
- New `lib/content/illustrations.py`: hand-built synthetic OHLC scenarios (Plotly frame-based animation, Play/Restart controls) — one per lesson, each crafted to unambiguously show that lesson's concept (a clean higher-high/higher-low sequence, a textbook demand-zone-plus-FVG formation, an opening-range breakout, etc.). Deliberately **not** real market data — real price action won't reliably show a clean example of a given concept in whatever the current window happens to look like, so illustrations are synthetic and explicitly labeled as such, kept clearly distinct from the real-data "Try it live" section already on each lesson.
- Risk Management's illustration is a different chart type by necessity — an animated equity-curve comparison (1% vs. 8% risk per trade against the identical losing streak) rather than a candlestick chart, since the lesson's point (position sizing determines survival, not the price action itself) isn't a price-pattern concept.
- All 8 verified via `AppTest` (frame counts, trace counts, no exceptions) and a real dev-server HTTP smoke test.

**Progress (2026-08-19) — Paper Trading Bot built (README_forex.md Section 8 Phase 8), plus a direct pushback-and-resolution on "predict the next trading signal":**
- The user's original ask was for the bot to "predict the next trading signal." Pushed back directly rather than quietly building something that oversells what these engines can honestly do: there's no evidence retail-accessible technical-analysis methods (including all three setups here) actually forecast future price movement, and a confident-looking "prediction" feature without that evidence would be exactly the kind of overclaiming Section 7 exists to prevent. Landed on the strongest honest version: **empirical, backtest-derived confidence** — a setup's real historical win-rate for that specific asset, sample size always shown — replacing "confidence" as a forecast with "confidence" as a report card.
- `lib/engines/confidence.py`: runs one cached backtest per (asset, setup) and returns its real win rate/expectancy/sample size. Deliberately decoupled from `TradingSignal.confidence_score` (the existing static rule-tier heuristic, unchanged, still used inside `backtest.py`'s own simulation) — this module must never be called from inside a backtest's per-bar `signal_fn`, since it runs its own backtest internally and would turn an O(n) simulation into O(n²) if nested.
- `lib/engines/bot.py` + `lib/db/bot_trades.py` + `migrations/0004_bot_trades.sql`: a paper trading bot that, on each page visit, checks all 3 setups across the full watchlist, opens a logged PENDING trade when a signal fires, and walks forward through candles since logging to detect entry-zone touches and stop/target hits — reusing the exact same touch-then-resolve logic `backtest.py`'s `_simulate_trades` already has, just walking forward from "when logged" to "now" instead of across history. `bot_trades` deliberately has no RLS/user scoping (same precedent as the `candles` table) — it's a single shared, public demonstration log, not private data.
- New Bot page: trade log (open/pending/closed, full reasoning shown per trade), a **Readiness Board** (rules-based "how close is this to qualifying" per asset/setup — zone/FVG/EMA/trend state, explicitly not a direction prediction), and the empirical win-rate table.
- **Two real bugs found and fixed via live testing against the actual Neon database**, not just logic review: (1) comparing a `timestamptz` column (returned by psycopg as timezone-*aware*) against `joined["time"]` (naive-but-UTC, the app's established convention) raised `Invalid comparison between dtype=datetime64[us] and datetime` in pandas — same naive-vs-aware bug class as the earlier OANDA timestamp fix, different call site. Fixed with a `_naive_utc()` helper. (2) Verified re-running the bot's refresh doesn't create duplicate trades for an asset/setup already in flight — confirmed directly, not assumed.
- Verified end-to-end against the full real watchlist (13 assets × 3 setups = 39 combinations): real signals opened across both forex (correct 5-decimal precision) and crypto (2-decimal), no exceptions, no duplicates on a second refresh.
- `refresh_bot` is `st.cache_data`-wrapped (300s TTL, matching the underlying candle data's own cache lifetime) despite having DB side effects — deliberate: within that window, the side effects are idempotent no-ops anyway (nothing changed), and caching avoids ~39 redundant DB round-trips on every page reload.

**Progress (2026-08-19) — Share section added to the Bot page (social text + branded PDF):**
- `lib/content/share.py`: a shareable text blurb (for pasting into a post) and a branded PDF report (`fpdf2` — pure-Python, no system font/library dependencies, deliberately avoiding another Streamlit-Cloud-environment landmine like the earlier `zoneinfo`/tzdata one). Both pull the bot's real current track record and open/closed trades — nothing here is a mockup.
- Anti-hype discipline treated as *more* important here, not less: this content is designed to leave the app and be read with zero context by strangers on social media. The disclaimer ("not financial advice, not a signal-selling service") and the sample-size/preliminary flag render **before** any stats in both the text and the PDF, not as a footnote — there's no code path that can produce a "clean" version without them.
- **Caught a real bug immediately on first run**: `fpdf2`'s built-in Helvetica font only supports Latin-1, and disclaimer text using an em-dash (`—`) raised `FPDFUnicodeEncodingException`. Rather than bundle a Unicode TTF font (more deployment risk, the exact category of problem already hit twice this session), swapped every non-ASCII character in PDF-bound strings for plain ASCII — the social-text version keeps its emoji/em-dashes freely, since that path never goes through `fpdf`.
- PDF verified structurally valid (`%PDF`/`%%EOF` markers) and visually inspected (not just "no exception") — TradeLab header, disclaimer, track record, and a real trades table all render correctly against live data.
- Share links (X/Twitter, LinkedIn, WhatsApp, Telegram) are plain `st.link_button`s to each platform's public share-intent URL, built with `urllib.parse.quote` — no custom JS, no clipboard API, nothing that behaves differently across browsers.

**Resolved (2026-08-19) — real 429 from Twelve Data on the deployed Bot page, fixed with proactive client-side rate limiting:**
- Reported live: `429 Too Many Requests` fetching AUD/USD 15m data. Root cause, not surprising in hindsight: checking 5 forex assets × 2 timeframes (1H + 15m) × 3 setups on a cold cache can burst past Twelve Data's free-tier 8-requests/minute limit well before any of it gets cached. The bot's existing per-asset/setup try/except (Section 6.6's "degrade gracefully" already built in) meant this didn't crash the page — that one combo was just skipped for the refresh — but it would keep recurring on every cold-cache refresh.
- Fix in `lib/market_data/twelvedata.py`: a module-level sliding-window rate limiter (`_throttle()`) that proactively paces our *own* outgoing requests to stay under 8/minute, plus a retry-with-backoff for any 429 that still gets through (e.g. another session sharing the same key). A slow page beats a failed one.
- Verified the throttle's timing logic directly with mocked `time.monotonic`/`time.sleep` (no real 60-second waits burned on testing) — confirmed it fires exactly once at the 9th request within a rolling minute and correctly stops throttling once the window naturally clears. Also verified normal single-request usage has no added delay.

**Still open — surface these before the relevant phase locks in:**
- Exact free-tier vs. paid-tier feature split (which signals/backtests/analytics sit behind Stripe gating) — a product decision, needed before Section 3.4 is implemented, not before MVP.
- Broker/exchange for eventual **live** (real-money) order execution, if that's ever wanted — OANDA remains a candidate for markets/residencies it does accept, but this is explicitly gated per Section 1.5/6.9 and not needed for MVP.
- Budget ceiling if/when free tiers are outgrown (Streamlit Cloud/Neon paid tiers, Twelve Data/Coinbase rate-limit upgrades).

An agent picking this up should treat the "Resolved" and "Superseded" lists as binding unless the user changes them again, and should still surface the "Still open" items as clarifying questions before locking in the relevant phase's architecture.

**Investigated and dropped (2026-08-19) — Open Graph "social preview card" support, found technically infeasible on this hosting setup:**
- The user asked what would give the app "more social lead" and picked three options, one being social preview cards. Investigated before building anything, per this project's own established pattern of verifying against real behavior rather than assuming: `curl`'d the raw HTML Streamlit Community Cloud serves for a real page (`/Bot`) and confirmed it's a single generic static shell (`<title>Streamlit</title>`, no per-page content at all) for every route — all actual content, including anything injected via `st.markdown`, only exists after client-side JavaScript runs.
- Social crawlers (Twitterbot, facebookexternalhit, WhatsApp, LinkedInBot) don't execute JavaScript — they only ever see that generic shell, so no Open Graph tag added through Streamlit's Python API can ever reach them. This isn't a bug to fix; it's a real property of Streamlit Community Cloud's serving model, and there's no supported way to customize that raw HTML per-route.
- The only real fix would be a separate, non-Streamlit static HTML page (hosted free elsewhere — GitHub Pages, Cloudflare Pages) with proper OG tags, that the actual shared link would point to. Surfaced this to the user as new infrastructure rather than a tweak, rather than quietly building something (e.g. `st.markdown`-injected meta tags) that would look done in the app but silently fail the moment anyone actually shared a link. User chose to skip it and proceed with the other two selected features instead.

**Progress (2026-08-19) — "more social lead" pass, part 2: Share sections added to Strategy Lab, Backtesting, and Scanner; shareable branded PNG image cards added everywhere Share already existed:**
- `lib/content/share.py` grew from Bot-only into a shared module: per-page text builders (`build_signal_share_text`, `build_backtest_share_text`, `build_scanner_share_text`), two Pillow-based branded PNG card builders (`build_stat_card_image` for a single signal/scan snapshot, `build_equity_curve_image` for a backtest's cumulative-R curve), and a `render_share_section()` UI helper so the text/PDF/image/social-link block is defined once instead of copy-pasted per page (it was about to be pasted a fourth time).
- Chose **Pillow only, no matplotlib/kaleido**, for the image cards — matches this project's established caution around adding dependencies with system-level or rendering-engine baggage onto Streamlit Community Cloud (the exact class of risk behind the `zoneinfo`/`tzdata` and `fpdf2` font issues already hit twice this session). `ImageFont.load_default(size=...)` uses Pillow's own bundled font, not a system font path, so there's no "works locally, missing font on the cloud container" risk. Pillow itself needed no new install — already a transitive dependency of both `fpdf2` and `streamlit` — but pinned it directly in `requirements.txt` since code now imports it directly, not just transitively.
- **Caught a real bug on first render, same class as the `fpdf2`/Helvetica issue from the earlier Bot-page Share work**: Pillow's bundled default font doesn't cover em/en-dashes or smart quotes either — they rendered as a visible tofu box (visually confirmed by rendering a real card and reading the PNG back, not assumed from code review). Fixed the same way as the PDF case: sanitize at the render boundary (`_safe_text()` in `share.py`) rather than trust every caller string to avoid the glyph — replaced "∞" with "Inf" for the same reason.
- Added an `equity_curve: list[float]` field to `StrategyPerformanceReport` (`lib/schemas/__init__.py`) and populated it in `run_backtest` (cumulative R after each trade, in resolution order) — didn't exist before this pass; needed for the equity-curve card and also now rendered as a normal `st.line_chart` on the Backtesting page itself, a small direct improvement independent of sharing.
- Verified every new/changed page end-to-end with `AppTest` against **real live data** (not mocks): Strategy Lab actually found a qualifying LONG EUR/USD signal on the very first run, exercising the new Share section's real code path, not just its absence; Backtesting and Scanner ran clean with real market data and no exceptions; the image-card functions were also rendered standalone and visually read back (including edge cases: zero trades, one trade, an all-losing curve, an empty stats list, `profit_factor = inf`) to confirm the chart math and font-safety fix actually hold, not just that no exception was raised.
- Bot page's existing Share section was refactored (not changed in substance) to use the new shared `render_share_section()` helper and gained a fourth format: a branded PNG track-record card, alongside its existing text and PDF.
