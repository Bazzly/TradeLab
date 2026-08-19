"""Opening Range Breakout setup (bot.md Section 1.2).

Adapted to TradeLab's supported timeframes (bot.md Section 3, question 5-6):
the source video uses a 5-minute chart with a 15-minute opening range.
Since 15m is our finest supported granularity, the "opening range" here IS
a single 15m candle — the one covering 09:30-09:45 America/New_York, which
maps exactly onto our 15m bucket with no approximation needed. Breakout
detection and entries also happen on 15m candles instead of 5m. This is an
explicit, documented adaptation, not an attempt to replicate a finer
timeframe we don't fetch.

Trend confirmation uses a 1H/4H hierarchy rather than Setup A's 1H/4H/1D —
a 15m-entry scalp needs a faster-moving trend filter than a full daily one.

DST is handled correctly (not by a fixed UTC-offset assumption) via the
stdlib `zoneinfo`, converting each candle's UTC time to America/New_York
before checking the session-open window.

Thin/holiday sessions (bot.md Section 3, question 6): if a trading day has
no candle at exactly 09:30 NY time (holiday, gap in data), no range is set
for that day and the breakout check simply never fires — "no qualifying
setup," not a crash, same as every other setup in this app.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from lib.engines.multi_timeframe import build_multi_timeframe_series

NY_TZ = ZoneInfo("America/New_York")
UTC_TZ = ZoneInfo("UTC")
SESSION_OPEN_HOUR = 9
SESSION_OPEN_MINUTE = 30

# A single candle's range >= this multiple of ATR counts as an "aggressive"
# breakout (bot.md's "break and close" vs. a weak first break). Separate
# constant from zones.py's 3-candle DISPLACEMENT_ATR_MULT since this is a
# single-candle measure, not directly comparable.
ORB_DISPLACEMENT_ATR_MULT = 1.5

# Entry is "right at the top/bottom of the range" (bot.md), a single price
# level in the source description — widened into a thin, ATR-scaled zone so
# it's meaningfully "touchable" in the same entry-zone-touch backtest
# simulation every other setup uses, rather than requiring an exact tick.
ENTRY_BUFFER_ATR_MULT = 0.1


def _is_ny_session_open_candle(utc_time: datetime) -> bool:
    ny_time = utc_time.replace(tzinfo=UTC_TZ).astimezone(NY_TZ)
    return ny_time.hour == SESSION_OPEN_HOUR and ny_time.minute == SESSION_OPEN_MINUTE


def compute_orb_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Adds: orb_range_high, orb_range_low (today's opening-range bounds),
    orb_direction ('LONG'/'SHORT'/None once a breakout has occurred today),
    orb_has_fvg. Requires `atr14` already present.
    """
    df = df.copy()
    n = len(df)

    is_range_candle = df["time"].apply(_is_ny_session_open_candle).to_numpy()
    highs, lows, closes = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    atrs = df["atr14"].to_numpy()
    times = df["time"].tolist()

    range_high = [float("nan")] * n
    range_low = [float("nan")] * n
    orb_direction: list[str | None] = [None] * n
    orb_has_fvg = [False] * n

    current_day = None
    current_high = float("nan")
    current_low = float("nan")
    active_direction: str | None = None
    active_has_fvg = False

    for i in range(n):
        day = times[i].date()
        if day != current_day:
            current_day = day
            current_high = float("nan")
            current_low = float("nan")
            active_direction = None
            active_has_fvg = False

        if is_range_candle[i]:
            current_high = highs[i]
            current_low = lows[i]
            active_direction = None

        if pd.notna(current_high) and active_direction is None and pd.notna(atrs[i]):
            candle_range = highs[i] - lows[i]
            aggressive = candle_range >= ORB_DISPLACEMENT_ATR_MULT * atrs[i]
            if closes[i] > current_high and aggressive:
                active_direction = "LONG"
                active_has_fvg = bool(i >= 2 and lows[i] > highs[i - 2])
            elif closes[i] < current_low and aggressive:
                active_direction = "SHORT"
                active_has_fvg = bool(i >= 2 and highs[i] < lows[i - 2])

        range_high[i] = current_high
        range_low[i] = current_low
        orb_direction[i] = active_direction
        orb_has_fvg[i] = active_has_fvg if active_direction else False

    df["orb_range_high"] = range_high
    df["orb_range_low"] = range_low
    df["orb_direction"] = orb_direction
    df["orb_has_fvg"] = orb_has_fvg
    return df


def build_orb_frame(
    asset: str, candles_15m: pd.DataFrame, higher_tf: str = "4H", intermediate_tf: str = "1H"
) -> pd.DataFrame:
    """15m base frame joined with 1H/4H trend (via the same
    build_multi_timeframe_series every setup uses), plus ORB-specific
    columns on top."""
    joined = build_multi_timeframe_series(
        asset, candles_15m, higher_tf=higher_tf, intermediate_tf=intermediate_tf
    )
    return compute_orb_columns(joined)
