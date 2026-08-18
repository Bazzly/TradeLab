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
| Hosting | **Streamlit Community Cloud** (share.streamlit.io), free tier | Free hosting tied directly to a GitHub repo; zero infra to manage. Constraint: app sleeps on inactivity, ~1 CPU/1GB RAM, ephemeral filesystem (no local file storage between deploys/restarts) |
| Database | **Neon** (serverless Postgres), free tier | Genuinely free (not a trial), real Postgres incl. Row-Level Security — needed since Streamlit's filesystem isn't persistent and Supabase is explicitly excluded |
| Auth | **Streamlit native auth** (`st.login()` / `st.user`, OIDC) backed by a free OIDC provider (e.g. Google or Auth0 free tier) | Built into Streamlit 1.42+, no custom password handling; identity (`st.user.email`) is the tenancy key into Neon |
| Tenancy enforcement | Postgres **Row-Level Security** on Neon, keyed on a session-scoped `app.current_user_id` setting the app sets per request | DB-enforced isolation, not just app-layer filtering (same principle as the original Supabase-RLS design, just self-managed) |
| Charts | **Plotly** (`st.plotly_chart`) for candlesticks + equity curves | First-class Streamlit support, handles OHLCV candlesticks and stats charts alike |
| Indicators/Backtesting | Python (pandas, numpy; **vectorbt** once backtesting depth requires it) | No longer deferred — this was always the natural fit once the app itself is Python |
| "Live" updates | `st.fragment(run_every=...)` periodic re-run on the dashboard fragment | Streamlit's execution model (rerun-on-interaction) isn't websocket-native; polling on an interval is the idiomatic substitute for MVP |
| Payments/Subscriptions | **Stripe** (Checkout + Customer Portal), status read via **polling the Stripe API** (cached, short TTL) rather than webhooks | Streamlit Community Cloud has no custom HTTP route for a webhook receiver; polling avoids standing up a second hosted service. Revisit with a small serverless webhook receiver only if polling latency becomes a real problem |
| Notifications | Email (Resend free tier) to start; Streamlit has no push/websocket channel of its own | Alerts for signals, journal reminders, news events |

### 3.2 Data Architecture Notes

- **Market data**: cache OHLCV candles per (asset, timeframe) in Neon Postgres, indexed on (asset, timeframe, time); never recompute historical candles from scratch on every rerun.
- **Indicators**: compute on ingest and store, or compute on-demand with `st.cache_data`-backed memoization keyed by (asset, timeframe, indicator, params) — Streamlit's own caching covers what Redis would have done at MVP scale.
- **Multi-timeframe engine**: reads from the same normalized candle store; never duplicate fetch logic per timeframe.
- **Provider abstraction**: define an internal `MarketDataProvider` protocol (Python `Protocol`/ABC) so forex/crypto data sources can be swapped or added without touching downstream engines. MVP providers (Section 3.3) implement this interface.
- **Tenancy**: every table holding user data (journal, strategies, settings) enforces Postgres Row-Level Security keyed on the authenticated user's id; the app sets `SET LOCAL app.current_user_id` per request/connection — no cross-user data access via app-layer checks alone.
- **Ephemeral filesystem caveat**: never write anything that needs to survive a redeploy (uploaded screenshots, exports) to local disk on Streamlit Community Cloud — use Neon (structured data) or object storage (e.g. Cloudflare R2 free tier) for files if/when the journal needs chart-screenshot uploads.

### 3.3 Market Data Providers (decided)

| Asset class | Provider | Why |
|---|---|---|
| Forex (EUR/USD, GBP/USD, etc.) | **OANDA v20 REST API**, free practice/demo account | Free forex pricing + historical candles, and the same demo account doubles as the Phase 8 paper-trading broker — one integration covers both needs |
| Crypto (BTC/USD, etc.) | **Binance public REST API** | Free, no API key required for market data, high rate limits |

Both are free indefinitely at MVP scale (no card required, no trial expiry). If usage later exceeds OANDA's demo/practice limits or a live-execution broker is needed, revisit per Section 11.

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
1. **One data source per asset class** — OANDA (forex: EUR/USD, GBP/USD) + Binance (crypto: BTC/USD) — on 3 timeframes (15m, 1H, 4H, 1D).
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
  /market_data        # MarketDataProvider protocol + OANDA + Binance adapters
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
- Market data: **OANDA practice API** (forex, also doubles as Phase 8 paper-trading broker) + **Binance public API** (crypto) — unchanged.
- Payments: **Stripe**, architected for from day one, wired up once a paid feature exists to gate (Section 3.4, Section 9) — unchanged, delivery mechanism changed below.

**Superseded (2026-08-19) — full pivot away from Supabase/Next.js to Python/Streamlit, per explicit request:**
- App framework + hosting: ~~Next.js/TypeScript on Vercel~~ → **Streamlit (Python) on Streamlit Community Cloud** (Section 3.1). The already-built Next.js scaffold was moved to a sibling `forex-nextjs-backup` directory rather than deleted, in case it's wanted later.
- Database + auth: ~~Supabase~~ → **Neon (Postgres, free tier)** for data, **Streamlit native `st.login()`/OIDC** for auth. Multi-user tenancy is still Postgres RLS, just self-managed on Neon instead of Supabase-managed.
- Indicators/backtesting: not deferred anymore — Python (pandas/numpy, vectorbt later) is now the MVP language, not a future upgrade.
- Payment gating delivery: Stripe **webhooks** → Stripe **polling**, because Streamlit Community Cloud has no custom HTTP route to receive a webhook (Section 3.4).

**Still open — surface these before the relevant phase locks in:**
- Exact free-tier vs. paid-tier feature split (which signals/backtests/analytics sit behind Stripe gating) — a product decision, needed before Section 3.4 is implemented, not before MVP.
- Which OIDC provider backs `st.login()` (Google vs. Auth0 vs. other) — needed before Section 9 item 0 (auth wiring), not before scaffolding.
- Broker/exchange for eventual **live** (real-money) order execution, if that's ever wanted — OANDA's live account is a natural candidate given the demo integration, but this is explicitly gated per Section 1.5/6.9 and not needed for MVP.
- Budget ceiling if/when free tiers are outgrown (Streamlit Cloud/Neon paid tiers, OANDA/Binance rate-limit upgrades).

An agent picking this up should treat the "Resolved" and "Superseded" lists as binding unless the user changes them again, and should still surface the "Still open" items as clarifying questions before locking in the relevant phase's architecture.
