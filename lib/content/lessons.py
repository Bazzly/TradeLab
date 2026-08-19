"""Learning/Mentor Engine content (README_forex.md Section 4.11, 9 item 7).

v1 scope: static beginner lessons, no persistence yet. Progress tracking
(README_forex.md Section 4.11) is deferred until Neon is wired up — the
Journal page's session-only pattern will extend here once it is.
"""

from dataclasses import dataclass


@dataclass
class Lesson:
    id: str
    title: str
    summary: str
    body: str  # markdown


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
    ),
]


def get_lesson(lesson_id: str) -> Lesson | None:
    return next((lesson for lesson in LESSONS if lesson.id == lesson_id), None)
