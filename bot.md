# Supply & Demand Signal Bot — Build Spec

> Companion to `README_forex.md`, which remains the source of truth for architecture, non-functional requirements, and the anti-hype rules referenced throughout this document. This file specifies **one new Signal Engine setup type** — it does not change anything else about the system.

**Status (2026-08-19): Both setups implemented, live-verified, and wired into the UI.**

**Setup A (Supply & Demand + FVG):**
- `lib/engines/zones.py` — displacement/zone/FVG/EMA200 detection, folded into `multi_timeframe.compute_frame()` so every setup shares one source of truth for indicator columns.
- `lib/engines/signal_supply_demand.py` — the signal generator, same `TradingSignal` contract as the existing pullback setup, same "no signal unless every rule met" discipline.
- **Live-verified**: real BTC/USD (124 qualifying bars / 2160, 3 completed backtest trades over 90 days) and EUR/USD (72 qualifying bars / 2160).
- Section 3's six open questions resolved with explicit, documented defaults — see `lib/engines/zones.py`'s docstring, including the one real simplification (multi-FVG confidence scaling isn't implemented, since the fixed 3-candle displacement window only ever produces a single gap to check).

**Setup B (Opening Range Breakout):**
- `lib/engines/orb.py` — NY-session opening-range detection (DST-correct via `zoneinfo`), single-candle displacement breakout, same FVG/EMA200 confirmation pattern as Setup A. `lib/engines/signal_orb.py` — the signal generator.
- Adapted to TradeLab's supported timeframes (Section 3, questions 5-6): the source's 5-minute chart isn't one we fetch, so the opening range is a single 15m candle (09:30-09:45 NY maps exactly onto one 15m bucket) and entries/breakouts happen on 15m candles. Trend confirmation uses a 1H/4H hierarchy, not Setup A's 1H/4H/1D — a faster filter for a faster entry timeframe.
- **Live-verified**: BTC/USD found 39 qualifying bars / 1920 over 20 days with sane entries; EUR/USD legitimately found zero over a 60-day window — traced the entire funnel (range detection → breakout → FVG → EMA200 → trend → R:R) and confirmed every stage works, it's specifically the R:R≥1.5 filter correctly rejecting setups clustered at R:R 1.16-1.41 for that window. ORB's stop spans the whole opening range (wider than Setup A's zone-based stop), so lower R:R more often is an expected property of the setup as specified, not a bug — the filter doing exactly its job.
- Building this surfaced and fixed a real, unrelated bug that would have corrupted session-time detection: `datetime.fromtimestamp()` without an explicit `tz` silently uses the server's local timezone, not UTC, across three provider modules — see README_forex.md Section 11 for the fix.

Both setups share `lib/engines/backtest.py`'s `signal_fn` seam (`SignalFn` type) — one simulation/stats engine, no duplicated backtest logic — and are wired into Strategy Lab and Backtesting via the same Setup selector. Full 9-page regression passes.

## 0. Source & an honest framing of it

This spec is derived from `botguid.md`, a transcript of a YouTube trading-education video. Two things about that source matter before writing a line of code:

1. **It's one trader's discretionary method, described after the fact, from a single anecdotal example chart.** It is not a backtested, peer-reviewed, or independently verified strategy. Nothing in the video constitutes evidence this approach has positive expectancy. Section 2's rule applies in full: nothing here gets called "profitable" until it clears the same sample-size and backtesting bar as the existing trend-aligned pullback setup (`lib/engines/signal.py`).
2. **The video is a marketing funnel**, not neutral education — it builds to a pitch for a paid "trading robot" / signal Discord with social-proof numbers ("1,400 users," "13.5% buy a second copy"). None of that marketing framing belongs anywhere in this spec or in TradeLab's UI. We're extracting the *mechanical trading logic* only — the parts that are actually rules, not the parts that are sales copy. Any implementation must go through the exact same Section 7 anti-hype filter as everything else in this app: no "this works," no popularity-as-evidence, no guaranteed returns.

With that framing, the underlying method is a fairly standard ICT-style ("Inner Circle Trader" school) supply/demand approach, and it's genuinely describable as an explicit rule set — which is exactly what Section 1.3's "hard constraints, not style guidance" bar requires before it's allowed to emit a signal at all.

---

## 1. Two setups described in the source

### 1.1 Setup A — Supply/Demand + Fair Value Gap (day/swing)

Rules, in the order the video applies them:

1. **Identify a displacement move**: 2-3+ consecutive same-direction candles moving aggressively away from a level (the video's example: ~75 pips on the hourly chart — this is asset/timeframe relative, not an absolute pip count; define it as a move whose range exceeds N × ATR, not a fixed pip value).
2. **Mark the zone**: the *last opposite-colored candle immediately before the displacement move*. Use the candle **body** (open-close range) for the zone by default; fall back to the full candle **range** (including wicks) only if the body is small relative to ATR (the video's stated reason: "so I don't miss trading opportunities" on small candles).
3. **Require Fair Value Gap confirmation**: a 3-candle imbalance where candle 1's wick and candle 3's wick don't overlap candle 2's body — i.e. a gap nobody has traded back through. At least one FVG within or immediately after the displacement move is required; the video treats *multiple* FVGs as extra confirmation, not just one.
4. **Trend confirmation** (both required):
   - Market structure: the recent swing sequence must be higher-highs/higher-lows (for a long) or lower-highs/lower-lows (for a short) — this is the same trend concept `lib/engines/multi_timeframe.py` already computes, so reuse it rather than re-deriving it.
   - Price relative to the 200-period EMA on the same timeframe, same direction as the trade.
5. **Entry**: a limit order at the zone, triggered when price returns to it. (The video also mentions a more conservative variant — wait for a confirmation candle inside the zone before entering — note it as a config option, not a second setup type.)
6. **Stop loss**: beyond the zone (below it for a long, above for a short), optionally extended to beyond the 200 EMA if that gives more room.
7. **Take profit**: the nearest prior resistance/support level the market has already rejected from at least once — *not* a fixed R-multiple. This is the one rule in the source that's the least mechanically precise ("why risk it, I'll play it safe") — needs a concrete, codifiable definition before this can be anything but discretionary (see Section 3 below).

### 1.2 Setup B — Opening Range Breakout (scalp)

1. **Mark the range**: high/low of the first 15 minutes after NY session open (09:30–09:45 America/New_York), on a 5-minute chart.
2. **Wait for displacement outside the range**: a "break and close" candle that closes outside the range with real momentum (the video explicitly distinguishes a weak first break, which it ignores, from an aggressive one, which it acts on) — same displacement definition as Setup A (move exceeds N × ATR).
3. That displacement candle's body becomes a demand/supply zone (same marking rule as Setup A, step 2), and the same FVG check applies.
4. **Trend confirmation**: same two checks as Setup A (structure + 200 EMA), evaluated on a higher timeframe than the 5-minute entry chart (the video doesn't say which — needs a decision, see Section 3).
5. **Entry**: pullback to the edge of the opening range (not the full zone — "right at the top of the range").
6. **Stop loss**: below the range low (long) / above the range high (short).
7. **Take profit**: same nearest-prior-level rule as Setup A.

### 1.3 What's explicitly *not* in scope

- The video's "move stop to break-even, take partial profits" trade management — flagged in the source itself as "advanced... things you can learn from my other videos," i.e. not part of the described system. Leave for a future iteration if wanted, don't invent rules the source doesn't actually give.
- Any of the marketing content (Discord, "trading robot," social proof, upsell). Not a trading rule, not going in.

---

## 2. How this fits the existing architecture

No new engine needed — this is **a second setup type for the existing Signal Engine** (`lib/engines/signal.py` currently hardcodes exactly one: trend-aligned pullback). Concretely:

- **`lib/engines/zones.py` (new)**: displacement-move detection, demand/supply zone marking, Fair Value Gap detection. Pure functions over a candle DataFrame, same shape as `lib/engines/multi_timeframe.py`'s existing indicator functions — causal/rolling only, no lookahead, per that module's existing discipline.
- **`lib/engines/multi_timeframe.py`**: add a 200-period EMA column to `compute_frame()` (indicator work belongs in `lib/indicators/`, reuse `sma`-style rolling logic or add an `ema()` function there) — trend/structure detection already exists and should be reused as-is, not reimplemented.
- **`lib/engines/signal.py`**: generalize `generate_signal()` to accept a `setup_type` parameter (or split into `generate_signal_pullback()` / `generate_signal_supply_demand()`, dispatched by a registry) rather than hardcoding one rule set. This is the natural point where README_forex.md Section 4.5 ("Strategy Builder... rule-definition UI/DSL," Phase 5, not yet built) would eventually plug in — this spec doesn't require building that DSL, just doesn't want to make it harder to add later.
- **`lib/engines/backtest.py`**: already setup-type-agnostic in its trade simulation loop (entry-zone touch → stop/target/timeout) — should work for this setup with minimal change once `generate_signal` accepts a setup type. Re-verify the "stop and target in the same bar → assume stop first" conservative assumption still makes sense here (probably yes, unchanged).
- **Strategy Lab / Scanner / Backtesting pages**: add a setup-type selector once there's more than one; until then, no UI changes required beyond that selector.

Everything from README_forex.md's non-functional requirements (Section 6) applies unchanged: rule version stored alongside every signal (Section 6.1), minimum sample size before "reliable" (Section 6.2), no survivorship bias in backtests (Section 6.3), idempotent backtests (Section 6.4).

---

## 3. Open questions to resolve before implementing (don't guess these)

The source video is a spoken walkthrough, not a spec — several things it does by eye need an explicit, codifiable rule before this can run mechanically:

1. **Displacement threshold**: what multiple of ATR (or what other precise measure) counts as "aggressive"? The video's pip examples (75 pips, 62 pips) aren't asset/timeframe-general.
2. **Take-profit target**: "nearest level price has rejected from before" needs a precise definition — likely reuse the existing `resistance`/`support` trailing-extreme columns from `multi_timeframe.py`, with the same documented limitation already on file (Section 9 item 3: trailing-window proxy, not true swing-point detection) — or invest in real swing-point detection now that a second setup needs it more precisely. Worth deciding explicitly rather than inheriting the limitation silently.
3. **Zone body vs. wick threshold**: "small candle → use the wick" — small relative to what? (Proposal: relative to ATR, consistent with the displacement threshold.)
4. **FVG count**: is one FVG sufficient, or does the "multiple FVGs = stronger" comment from the video need to become a confidence-tier rule (e.g. feeding into `confidence_score` the same way `confirmation_level` does for the existing setup)?
5. **Setup B's higher-timeframe trend check**: which timeframe, exactly, confirms trend for a 5-minute-chart scalp?
6. **Setup B's session-time handling**: `America/New_York` DST transitions, and what happens on days with no clean 15-minute range (e.g. a holiday-thinned session) — needs an explicit "no qualifying setup" fallback, not a crash.

Per README_forex.md Section 1.4 ("ask before assuming a broker/exchange/data provider") and the same spirit applied here: **surface these six questions to the user before writing the detection code**, rather than picking defaults unilaterally. Getting the displacement/zone thresholds wrong quietly turns this into a different, untested strategy from the one described.

---

## 4. Non-negotiable constraints (restated from README_forex.md, apply without exception)

- No `TradingSignal` is emitted unless every rule in Section 1.1/1.2 is met — "no qualifying setup" stays a normal, expected, common outcome (Section 5.2's existing rule, unchanged).
- Every signal carries `reasons`, `confirmation_factors`, and `invalidating_conditions`, same as the existing setup — a supply/demand signal needs to explain *why*, not just emit LONG/SHORT.
- Minimum R:R and any other numeric threshold must be an explicit, stated constant (like the existing `MIN_RISK_REWARD_RATIO = 1.5`) — not tuned invisibly against this specific backtest window.
- Backtest results for this setup are "preliminary" below the same sample-size bar as the existing one (README_forex.md Section 2) — and must show sample size, limitations, and overfitting flags exactly like `lib/engines/backtest.py` already does. A new setup type does not get to skip the discipline the first one had to earn.
- Nothing about this setup implies or states that it is *the* strategy used by "1,400 traders" or any other borrowed credibility from the source video — that claim belongs to someone else's paid product, not to what we're building or testing here.
