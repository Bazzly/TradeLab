"""Learning/Mentor Engine content (README_forex.md Section 4.11, 9 item 7).

v1 scope: static beginner lessons, no persistence yet. Progress tracking
(README_forex.md Section 4.11) is deferred until Neon is wired up — the
Journal page's session-only pattern will extend here once it is.

Each lesson can declare a `live_example` key. This module stays a pure
content module (no streamlit/pandas dependency) — the Learning page
(pages/5_Learning.py) is what dispatches on that key to render a live
example pulled from the actual running engines, so a lesson's "why it
matters" claim is demonstrated against real current data, not just asserted.
"""

from dataclasses import dataclass


@dataclass
class Lesson:
    id: str
    title: str
    summary: str
    body: str  # markdown
    live_example: str | None = None  # key the Learning page dispatches on


LESSONS: list[Lesson] = [
    Lesson(
        id="market-structure",
        title="1. Market Structure",
        summary="How to read the sequence of highs and lows that defines a trend.",
        body="""
Market structure is the raw skeleton underneath every chart: the sequence of
swing highs and swing lows price leaves behind as it moves.

- **Uptrend structure**: a series of *higher highs* (HH) and *higher lows*
  (HL). Each pullback finds support above the previous low.
- **Downtrend structure**: a series of *lower highs* (LH) and *lower lows*
  (LL). Each rally fails below the previous high.
- **Range / sideways structure**: highs and lows stay roughly level — no
  consistent higher-high/higher-low or lower-high/lower-low pattern.

**Why it matters here**: TradeLab's Multi-Timeframe Analysis Engine
(README_forex.md Section 5.1) classifies trend on exactly this logic —
price relative to its moving averages is a proxy for "is structure still
making higher lows or not." When you look at the Strategy Lab page and see
`higher_timeframe_trend`, this is what it's approximating.

**A structure break is not automatically a reversal.** A single lower high
after a long uptrend could be the start of a new downtrend, or just a
deeper pullback within the same uptrend. Structure tells you the current
state, not the future — that's why TradeLab always shows confirmation level
(STRONG/MODERATE/WEAK/CONFLICTING) instead of a single "trend" label.
""",
        live_example="market_structure",
    ),
    Lesson(
        id="candlesticks",
        title="2. Candlesticks",
        summary="What a single candle actually encodes, and what it doesn't.",
        body="""
A candlestick summarizes four numbers for a fixed time window: **open,
high, low, close** (OHLC).

- The **body** spans open to close. A filled/red body means close < open
  (price fell over that candle); a hollow/green body means close > open.
- The **wicks** (or shadows) show the high and low reached during the
  candle, even if price didn't close there.

**What one candle tells you**: how contested that time window was. A long
wick with a small body means price was pushed one direction and then
rejected back — a tug of war within the candle. A large body with tiny
wicks means one side was in control the whole window.

**What one candle does NOT tell you**: why. Candles are pure price
geometry — they carry no information about the reason behind the move.
This is part of why TradeLab never generates a signal off a single
candle pattern in isolation; the Signal Engine (Section 5.2) requires
multi-timeframe trend agreement plus a defined risk:reward, not "a
hammer candle appeared."

**Timeframe changes what a candle means.** A single "big" 15-minute
candle might be unremarkable noise on the 1-day chart. Always read a
candle's significance relative to the timeframe you're trading.
""",
        live_example="candlesticks",
    ),
    Lesson(
        id="support-resistance",
        title="3. Support & Resistance",
        summary="Why price tends to react at certain levels, and the honest limits of drawing them.",
        body="""
**Support** is a price level where buying pressure has historically been
strong enough to stop or reverse a decline. **Resistance** is the mirror
image — a level where selling pressure has capped rallies.

These levels exist because price is memory: traders who missed a move at a
prior high/low often act again when price returns there (taking profit,
adding to a position, cutting a loss). That collective behavior can turn a
past price level into a self-reinforcing one — but it's a tendency, not a
law.

**How TradeLab finds levels (MVP, documented limitation)**: the current
engine uses a trailing rolling high/low over the last 20 candles — the
highest high and lowest low in that recent window. This is a simplification
of true swing-point detection (which would look for local peaks/troughs,
not just a trailing extreme) and is explicitly called out as a limitation
on the Backtesting page's report.

**A level is a zone, not a line.** Treating support/resistance as an exact
price misses how markets actually react — price often reverses a little
before or after the "exact" level. That's why TradeLab's entry zones are a
range (`entry_zone: [low, high]`, Section 5.2), not a single number.

**Levels fail.** When price decisively closes through a level (not just
wicks through it), that level often flips role — old resistance can become
new support, and vice versa. A strategy that assumes every level holds
forever will eventually get run over; this is exactly why every
TradingSignal carries `invalidatingConditions` (Section 5.2) — the
predefined point at which the setup is simply wrong.
""",
        live_example="support_resistance",
    ),
    Lesson(
        id="risk-management",
        title="4. Risk Management Basics",
        summary="The non-negotiable rules that come before any entry.",
        body="""
Risk management is the only part of trading you fully control. You don't
control whether a setup works — you control how much you lose when it
doesn't.

**Position sizing**: decide risk *before* you decide the trade. A common
starting rule: risk no more than 1-2% of account equity on any single
trade. Position size is then derived from your stop distance, not the
other way around — you don't pick a position size and hope the stop fits.

**Risk:Reward (R:R)**: the ratio between what you stand to lose (entry to
stop) and what you stand to gain (entry to target). TradeLab's Signal
Engine (Section 5.2, Section 9 item 4) enforces a minimum R:R of 1.5 before
it will even emit a signal — a rule, not a suggestion, and one you can see
directly on the Strategy Lab page.

**Win rate and R:R are a package deal.** A strategy can be profitable with
a win rate under 50% if the average winner is large enough relative to the
average loser (this is `expectancy` on the Backtesting page — the single
number that actually tells you whether a system has edge, not win rate
alone).

**Sample size before conclusions.** One winning trade, or even ten, tells
you almost nothing about whether a strategy has real edge versus random
variance. TradeLab will not label a Backtesting report's win rate or
profit factor as reliable below a documented trade-count threshold
(README_forex.md Section 2) — the UI shows the number, but flags it as
preliminary until there's enough data.

**Losing is part of the plan, not a failure of it.** A strategy with a
55% win rate still loses 45% of the time, by design. The question isn't
"did this trade lose" — it's "did I follow the rule that defines this
strategy." That distinction is the whole point of a trading journal
(coming in the Journal page): grading your *process*, separate from any
single trade's outcome.
""",
        live_example="risk_management",
    ),
    Lesson(
        id="fvg-supply-demand",
        title="5. Fair Value Gaps & Supply/Demand Zones",
        summary="How TradeLab's Supply & Demand setup (bot.md Setup A) actually detects a zone.",
        body="""
This lesson explains the first of TradeLab's two "smart money" setups —
picked apart from a trading-education video transcript into an explicit,
codifiable rule set (see `bot.md` if you want the full derivation).

**Displacement**: a fast, aggressive multi-candle move away from a level.
Institutional-size orders tend to move price in bursts, not smoothly — a
displacement move is the chart's fingerprint of that. TradeLab defines it
precisely (not just "looks big"): the 3-candle range must be at least
**3× the 14-period ATR**, with at least 2 of the 3 candles moving the same
direction. ATR-relative, not a fixed pip count, so the same rule applies
whether you're looking at BTC/USD or EUR/USD.

**The zone**: the *opposite-colored* candle immediately before the
displacement. If a big bullish push just happened, the last bearish candle
before it marks the zone — because that's the last price institutions were
willing to buy at before pushing higher. TradeLab marks the zone from that
candle's **body**, or its full wick-to-wick range if the body is small
(under half an ATR) relative to that candle.

**Fair Value Gap (FVG)**: a 3-candle pattern where candle 3's low sits
above candle 1's high (for a bullish gap) — meaning nobody has traded back
through that price yet. It's evidence the move was strong enough that even
a brief pullback didn't happen. TradeLab **requires** an FVG within the
displacement before it will treat a zone as valid — no FVG, no zone.

**Confirmation**: price above the 200-period EMA (long) or below it
(short), *and* the higher-timeframe trend agreeing. Both must hold before
this ever becomes a signal.

**What this is NOT**: proof that supply/demand zones have positive
expectancy. It's one trader's discretionary method, mechanized into
explicit rules so it can be honestly backtested — not evidence it works.
Check the Backtesting page's sample size and limitations before believing
anything about its edge.
""",
        live_example="fvg_supply_demand",
    ),
    Lesson(
        id="trend-filters-ema",
        title="6. Trend Filters: Moving Averages & the 200 EMA",
        summary="Why TradeLab layers a slow-moving average on top of market structure.",
        body="""
Market structure (Lesson 1) tells you what price has *already done*. A
moving average is a different, complementary lens: it smooths out noise
so you can see the prevailing direction at a glance, without having to
manually track every swing high and low.

**Simple Moving Average (SMA)**: the average close over the last N
candles, recalculated every candle. TradeLab's trend-aligned pullback
setup compares a 20-period SMA to a 50-period SMA — price above both, with
the 20 above the 50, defines an uptrend; the mirror image defines a
downtrend; anything else is "sideways."

**Exponential Moving Average (EMA)**: like an SMA, but weights recent
candles more heavily. TradeLab's supply/demand and opening-range-breakout
setups both use a **200-period EMA** as a slow, high-conviction trend
filter — a long lookback specifically so it doesn't flip on every minor
pullback. Price needs to be clearly on one side of it before either setup
will treat that side as the tradeable direction.

**Why layer a slow filter on top of a fast setup?** A supply/demand zone
or a range breakout can look identical whether the broader market is
trending or chopping sideways — the EMA200 is what tells the engine
"trade this direction, not the other," cutting down on setups that look
right for a few candles and then fail because they're going against the
larger trend.

**A trend filter is not a crystal ball.** Price closing above a 200 EMA
doesn't guarantee it stays there — it's a probability tilt, one input
among several (alongside structure, R:R, and the zone/breakout rules
themselves), never sufficient on its own to justify a trade.
""",
        live_example="trend_filters",
    ),
    Lesson(
        id="opening-range-breakout",
        title="7. Opening Range Breakout",
        summary="TradeLab's second bot strategy (bot.md Setup B) — a session-timed scalp.",
        body="""
Unlike the other two setups, this one is anchored to **time of day**, not
just price action — specifically the New York session open, historically
one of the most active windows in both forex and crypto.

**The opening range**: TradeLab marks the high and low of the 15-minute
candle covering **09:30-09:45 America/New_York** — correctly adjusted for
Daylight Saving Time (a common bug in naive implementations; TradeLab
verified this directly against real dates, not just assumed it). That
range becomes the day's reference box.

**Displacement breakout**: a single candle that closes *outside* the
range with real momentum — TradeLab requires that candle's range to be at
least **1.5× the 14-period ATR**, a lower bar than Setup A's 3× since this
is a single-candle measure, not a 3-candle one. A weak, low-momentum poke
outside the range doesn't count.

**Entry, stop, target**: entry is a pullback to the *edge* of the range
(not the whole zone) once a breakout has happened; the stop sits on the
*opposite* side of the entire range — noticeably wider than Setup A's
tight zone-based stop, which is exactly why this setup needs a bigger
move in its favor to clear the same 1.5 minimum Risk:Reward bar. Don't be
surprised if it qualifies less often than Setup A; that's a property of
how the stop is defined, not a bug.

**An honest limitation**: the source material described this on a
5-minute chart; TradeLab only fetches down to 15-minute candles, so the
opening range here is exactly one 15m candle rather than three 5m ones.
Documented, not hidden — see `bot.md` Section 3 if you want the full
reasoning.
""",
        live_example="orb",
    ),
    Lesson(
        id="how-a-signal-is-built",
        title="8. How a Signal Actually Gets Built",
        summary="Tying it together: what happens, in order, from raw candles to a TradingSignal.",
        body="""
Every lesson so far covered one ingredient. This one shows the actual
pipeline that turns them into the exact `TradingSignal` object you see on
the Strategy Lab page — the same object, unchanged, that also drives the
Scanner and the Backtesting engine, so what you read here is genuinely
what runs everywhere else in the app.

**1. Fetch candles.** OHLCV data for the asset/timeframe, from whichever
provider covers that asset class (Coinbase for crypto, Twelve Data for
forex).

**2. Compute indicators.** Moving averages, RSI, ATR, and — for the two
bot setups — displacement/zone/FVG/EMA200 columns, all computed causally
(only ever looking backward, never at future candles you wouldn't
actually have yet).

**3. Join timeframes.** A higher timeframe's trend gets attached to every
row of the entry timeframe, but only once that higher-timeframe candle has
*fully closed* — using "today's" still-forming daily candle to judge an
hourly bar would be looking into the future.

**4. Check every rule.** Confirmation level, zone/FVG/breakout conditions,
trend agreement, minimum Risk:Reward — every one of them has to pass.
Miss any single one and the result is `None`, not a weak signal. "No
qualifying setup" is the single most common output of this whole
pipeline, by design.

**5. Build the signal.** Only if every rule passed: entry zone, stop,
target, R:R, a confidence score, and — critically — `reasons` and
`confirmation_factors` that trace back to the specific rule that fired.
Nothing in TradeLab shows you a signal without also showing you why.

Use the live example below to watch this pipeline run right now, on
whichever asset and setup you pick.
""",
        live_example="signal_pipeline",
    ),
]


def get_lesson(lesson_id: str) -> Lesson | None:
    return next((lesson for lesson in LESSONS if lesson.id == lesson_id), None)
