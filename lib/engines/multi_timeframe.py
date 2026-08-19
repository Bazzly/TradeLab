"""Multi-Timeframe Analysis Engine (README_forex.md Section 4.3, 5.1).

Design note on avoiding lookahead: every column added by `compute_frame` is a
rolling/ewm calculation, which by construction only depends on data up to and
including that row — so a full history can be computed once and indexed at
any point without leaking future information. The one place lookahead could
sneak in is joining a coarser timeframe (4H/1D) onto a finer one (1H): using
"today's" still-forming daily candle to analyze an intraday bar would leak
the rest of that day into the past. `join_higher_timeframe` guards against
this by only ever joining a higher-timeframe candle once it has fully closed.
"""

from dataclasses import replace
from datetime import timedelta

import numpy as np
import pandas as pd

from lib.engines.zones import compute_zone_columns
from lib.indicators import atr, rsi, sma
from lib.schemas import ConfirmationLevel, MultiTimeframeAnalysis

TIMEFRAME_TO_PANDAS_RULE = {"15m": "15min", "1H": "1h", "4H": "4h", "1D": "1D"}
TIMEFRAME_TO_TIMEDELTA = {
    "15m": timedelta(minutes=15),
    "1H": timedelta(hours=1),
    "4H": timedelta(hours=4),
    "1D": timedelta(days=1),
}

SUPPORT_RESISTANCE_LOOKBACK = 20
MIN_TREND_LOOKBACK = 50  # bars needed before sma50 is defined


def resample_ohlc(candles: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample a finer-grained candle frame up to a coarser timeframe."""
    rule = TIMEFRAME_TO_PANDAS_RULE[timeframe]
    out = (
        candles.set_index("time")
        .resample(rule)
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
        .reset_index()
    )
    return out


def compute_frame(candles: pd.DataFrame) -> pd.DataFrame:
    """Add indicator + classification columns. Every column is causal (rolling/ewm)."""
    df = candles.copy()
    df["sma20"] = sma(df["close"], 20)
    df["sma50"] = sma(df["close"], MIN_TREND_LOOKBACK)
    df["rsi14"] = rsi(df["close"], 14)
    df["atr14"] = atr(df["high"], df["low"], df["close"], 14)

    # Trailing (non-centered) rolling extremes — a causal proxy for recent
    # support/resistance. Not true swing-point detection; documented MVP
    # simplification (README_forex.md Section 9 item 3).
    df["resistance"] = df["high"].rolling(SUPPORT_RESISTANCE_LOOKBACK).max()
    df["support"] = df["low"].rolling(SUPPORT_RESISTANCE_LOOKBACK).min()

    df["trend"] = np.select(
        [
            (df["close"] > df["sma20"]) & (df["sma20"] > df["sma50"]),
            (df["close"] < df["sma20"]) & (df["sma20"] < df["sma50"]),
        ],
        ["UPTREND", "DOWNTREND"],
        default="SIDEWAYS",
    )
    df.loc[df["sma50"].isna(), "trend"] = "UNKNOWN"

    df["momentum"] = np.select(
        [df["rsi14"] >= 70, df["rsi14"] <= 30],
        ["OVERBOUGHT", "OVERSOLD"],
        default="NEUTRAL",
    )
    df.loc[df["rsi14"].isna(), "momentum"] = "UNKNOWN"

    atr_pct = df["atr14"] / df["close"] * 100
    df["volatility"] = np.select(
        [atr_pct < 0.5, atr_pct < 1.5],
        ["LOW", "MODERATE"],
        default="HIGH",
    )
    df.loc[df["atr14"].isna(), "volatility"] = "UNKNOWN"

    # Supply/Demand + FVG setup columns (bot.md, lib/engines/zones.py) —
    # computed here too so build_multi_timeframe_series's join gives every
    # setup type the same base frame, one source of truth per README_forex.md
    # Section 3.2's "never duplicate fetch logic" rule.
    df = compute_zone_columns(df)

    return df


def join_higher_timeframe(lower: pd.DataFrame, higher: pd.DataFrame, higher_timeframe: str) -> pd.DataFrame:
    """For each row in `lower`, attach the most recent `higher` row whose
    candle has fully closed as of that lower-timeframe timestamp — never the
    still-forming current higher-timeframe candle.
    """
    higher_closed = higher.copy()
    higher_closed["close_time"] = higher_closed["time"] + TIMEFRAME_TO_TIMEDELTA[higher_timeframe]

    prefix = higher_timeframe.lower() + "_"
    renamed = higher_closed.add_prefix(prefix).rename(columns={f"{prefix}close_time": "close_time"})

    merged = pd.merge_asof(
        lower.sort_values("time"),
        renamed.sort_values("close_time"),
        left_on="time",
        right_on="close_time",
        direction="backward",
    )
    return merged


def _entry_setup(row: pd.Series) -> tuple[list[tuple[float, float]], list[float], list[float], float]:
    """Trend-aligned pullback to support/resistance (README_forex.md Section 9 item 4).

    Returns (possible_entry_zones, invalidation_levels, targets, risk_reward_ratio).
    Empty lists / rr=0.0 mean "no qualifying zone" — a valid, expected output.
    """
    atr_val = row["atr14"]  # base (lower-timeframe) frame column, unprefixed
    support = row["support"]
    resistance = row["resistance"]
    trend = row["trend"]

    if pd.isna(atr_val) or pd.isna(support) or pd.isna(resistance):
        return [], [], [], 0.0

    if trend == "UPTREND":
        entry_zone = (support, support + atr_val)
        entry_price = sum(entry_zone) / 2
        stop = support - atr_val
        target = resistance
        risk = entry_price - stop
        reward = target - entry_price
    elif trend == "DOWNTREND":
        entry_zone = (resistance - atr_val, resistance)
        entry_price = sum(entry_zone) / 2
        stop = resistance + atr_val
        target = support
        risk = stop - entry_price
        reward = entry_price - target
    else:
        return [], [], [], 0.0

    if risk <= 0 or reward <= 0:
        return [], [], [], 0.0

    rr = reward / risk
    return [entry_zone], [stop], [target], rr


def _confirmation_level(higher_trend: str, intermediate_trend: str, lower_trend: str) -> tuple[ConfirmationLevel, list[str]]:
    trends = [higher_trend, intermediate_trend, lower_trend]
    if "UNKNOWN" in trends:
        return "NO_TRADE", ["Insufficient history on one or more timeframes"]

    up = trends.count("UPTREND")
    down = trends.count("DOWNTREND")
    conflicts = []
    if up > 0 and down > 0:
        conflicts.append(
            f"Timeframes disagree: higher={higher_trend}, intermediate={intermediate_trend}, lower={lower_trend}"
        )
        return "CONFLICTING", conflicts

    if up == 3 or down == 3:
        return "STRONG", conflicts
    if up == 2 or down == 2:
        return "MODERATE", conflicts
    return "WEAK", conflicts


def build_analysis(asset: str, row: pd.Series, higher_tf: str, intermediate_tf: str) -> MultiTimeframeAnalysis:
    """Build a MultiTimeframeAnalysis from one row of the joined frame
    produced by `join_higher_timeframe` (called twice: 1D onto 4H, then
    4H+1D onto 1H) — see multi_timeframe.build_live_analysis for the join order.
    """
    higher_prefix = higher_tf.lower() + "_"
    intermediate_prefix = intermediate_tf.lower() + "_"

    higher_trend = row[f"{higher_prefix}trend"]
    intermediate_trend = row[f"{intermediate_prefix}trend"]
    lower_trend = row["trend"]

    confirmation_level, conflicts = _confirmation_level(higher_trend, intermediate_trend, lower_trend)
    entry_zones, invalidation, targets, rr = _entry_setup(row)

    key_levels = [row["support"], row["resistance"]]
    key_levels = [float(lv) for lv in key_levels if pd.notna(lv)]

    return MultiTimeframeAnalysis(
        asset=asset,
        timestamp=row["time"],
        higher_timeframe_trend=str(higher_trend),
        intermediate_trend=str(intermediate_trend),
        lower_timeframe_structure=str(lower_trend),
        key_support_resistance=key_levels,
        momentum=str(row["momentum"]),
        volatility=str(row["volatility"]),
        possible_entry_zones=entry_zones,
        invalidation_levels=invalidation,
        targets=targets,
        risk_reward_ratio=rr,
        confirmation_level=confirmation_level,
        conflicting_signals=conflicts,
    )


def build_multi_timeframe_series(
    asset: str,
    candles_1h: pd.DataFrame,
    candles_4h: pd.DataFrame | None = None,
    candles_1d: pd.DataFrame | None = None,
    higher_tf: str = "1D",
    intermediate_tf: str = "4H",
) -> pd.DataFrame:
    """Compute the full joined, indicator-enriched frame for every 1H bar.
    Used by both the live dashboard (take the last row) and the backtest
    engine (iterate every row) — same code path, so results can never
    diverge between "what the dashboard showed" and "what the backtest saw."

    If `candles_4h`/`candles_1d` aren't supplied, they're derived by
    resampling `candles_1h` (fine for MVP; a real provider feed for each
    timeframe is a documented future improvement).
    """
    lower = compute_frame(candles_1h)

    intermediate_source = candles_4h if candles_4h is not None else resample_ohlc(candles_1h, intermediate_tf)
    intermediate = compute_frame(intermediate_source)

    higher_source = candles_1d if candles_1d is not None else resample_ohlc(candles_1h, higher_tf)
    higher = compute_frame(higher_source)

    joined = join_higher_timeframe(lower, intermediate, intermediate_tf)
    joined = join_higher_timeframe(joined, higher, higher_tf)
    return joined


def analyze_latest(
    asset: str,
    candles_1h: pd.DataFrame,
    candles_4h: pd.DataFrame | None = None,
    candles_1d: pd.DataFrame | None = None,
) -> MultiTimeframeAnalysis:
    joined = build_multi_timeframe_series(asset, candles_1h, candles_4h, candles_1d)
    return build_analysis(asset, joined.iloc[-1], higher_tf="1D", intermediate_tf="4H")
