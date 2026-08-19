"""Supply & Demand + Fair Value Gap setup (bot.md Section 1.1, 2).

Resolves bot.md Section 3's open questions with explicit, documented
defaults rather than guessing silently:

1. Displacement threshold: a 3-candle move whose (high-low) range over that
   window is >= DISPLACEMENT_ATR_MULT * ATR(14), with at least 2 of the 3
   candles same-direction. ATR-relative, not a fixed pip count, so it scales
   across assets/timeframes the source video's pip examples don't.
2. Take-profit target: reuses the existing trailing-extreme
   resistance/support columns from multi_timeframe.py — same documented
   simplification as the pullback setup (README_forex.md Section 9 item 3),
   not a second, inconsistent definition of "the nearest level."
3. Small-candle → wick threshold: body range < SMALL_BODY_ATR_MULT * ATR at
   the zone candle.
4. Multiple-FVG confidence boost: NOT implemented. The displacement window
   is fixed at exactly 3 candles here, which structurally only ever
   produces one candle-1-to-candle-3 gap to check — there's no "multiple"
   to count without allowing variable-length displacement windows, which
   this version doesn't. `zone_has_fvg` is a required boolean gate, not a
   confidence scalar. Documented simplification, not a silent gap.
5/6. Setup B (Opening Range Breakout) is out of scope for this module —
   deferred per bot.md's "keep this a reviewable increment" framing.

Zone state (which demand/supply zone is active, whether it's been
invalidated) depends on the whole preceding history, not a fixed lookback
window, so it's computed with a single causal forward scan rather than
vectorized rolling ops — same pattern lib/engines/backtest.py already uses
for its bar-by-bar trade simulation, not a new style introduced here.
"""

import pandas as pd

from lib.indicators import ema

DISPLACEMENT_ATR_MULT = 3.0
SMALL_BODY_ATR_MULT = 0.5


def compute_zone_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Adds: ema200, displacement_up/down, zone_direction ('DEMAND'/
    'SUPPLY'/None), zone_low, zone_high, zone_has_fvg. Requires `atr14`
    already present (i.e. call after multi_timeframe.compute_frame's own
    indicator columns are added)."""
    df = df.copy()
    df["ema200"] = ema(df["close"], 200)

    bullish = df["close"] > df["open"]
    bearish = df["close"] < df["open"]
    bullish_count_3 = bullish.rolling(3).sum()
    bearish_count_3 = bearish.rolling(3).sum()
    move_range_3 = df["high"].rolling(3).max() - df["low"].rolling(3).min()
    net_move_3 = df["close"] - df["close"].shift(2)

    displacement_up = (
        (net_move_3 > 0) & (bullish_count_3 >= 2) & (move_range_3 >= DISPLACEMENT_ATR_MULT * df["atr14"])
    )
    displacement_down = (
        (net_move_3 < 0) & (bearish_count_3 >= 2) & (move_range_3 >= DISPLACEMENT_ATR_MULT * df["atr14"])
    )
    df["displacement_up"] = displacement_up
    df["displacement_down"] = displacement_down

    n = len(df)
    zone_direction: list[str | None] = [None] * n
    zone_low: list[float] = [float("nan")] * n
    zone_high: list[float] = [float("nan")] * n
    zone_has_fvg: list[bool] = [False] * n

    active_direction: str | None = None
    active_low = float("nan")
    active_high = float("nan")
    active_has_fvg = False

    highs, lows, opens, closes, atrs = (
        df["high"].to_numpy(),
        df["low"].to_numpy(),
        df["open"].to_numpy(),
        df["close"].to_numpy(),
        df["atr14"].to_numpy(),
    )
    disp_up, disp_down = displacement_up.to_numpy(), displacement_down.to_numpy()
    bullish_arr, bearish_arr = bullish.to_numpy(), bearish.to_numpy()

    for i in range(n):
        if i >= 3:
            zone_idx = i - 3
            atr_at_zone = atrs[zone_idx]
            if pd.notna(atr_at_zone):
                zc_body_low, zc_body_high = min(opens[zone_idx], closes[zone_idx]), max(
                    opens[zone_idx], closes[zone_idx]
                )
                body_range = zc_body_high - zc_body_low
                use_wick = body_range < SMALL_BODY_ATR_MULT * atr_at_zone

                if disp_up[i] and bearish_arr[zone_idx]:
                    active_direction = "DEMAND"
                    active_low = lows[zone_idx] if use_wick else zc_body_low
                    active_high = highs[zone_idx] if use_wick else zc_body_high
                    active_has_fvg = bool(lows[i] > highs[i - 2])
                elif disp_down[i] and bullish_arr[zone_idx]:
                    active_direction = "SUPPLY"
                    active_low = lows[zone_idx] if use_wick else zc_body_low
                    active_high = highs[zone_idx] if use_wick else zc_body_high
                    active_has_fvg = bool(highs[i] < lows[i - 2])

        # Invalidate on a close back through the zone.
        if active_direction == "DEMAND" and closes[i] < active_low:
            active_direction = None
        elif active_direction == "SUPPLY" and closes[i] > active_high:
            active_direction = None

        zone_direction[i] = active_direction
        zone_low[i] = active_low if active_direction else float("nan")
        zone_high[i] = active_high if active_direction else float("nan")
        zone_has_fvg[i] = active_has_fvg if active_direction else False

    df["zone_direction"] = zone_direction
    df["zone_low"] = zone_low
    df["zone_high"] = zone_high
    df["zone_has_fvg"] = zone_has_fvg
    return df
