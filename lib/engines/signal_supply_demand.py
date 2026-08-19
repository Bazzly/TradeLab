"""Supply & Demand + Fair Value Gap Signal Engine (bot.md).

A second, independent setup type alongside lib/engines/signal.py's
trend-aligned pullback — same TradingSignal contract, same "no signal
unless every rule is met" discipline (README_forex.md Section 5.2), but
its own rule set entirely rather than a parametrized variant of the first
setup's logic (the two are different enough in shape — zone-based entry vs.
trailing-extreme pullback — that forcing one generalized function would
have made both harder to read).

Requires a row from lib.engines.multi_timeframe.build_multi_timeframe_series
(zone/EMA200 columns come from lib.engines.zones via compute_frame).
"""

import uuid
from datetime import datetime

import pandas as pd

from lib.engines.signal import MIN_RISK_REWARD_RATIO
from lib.schemas import Timeframe, TradingSignal

SETUP_TYPE = "supply_demand_fvg"


def generate_signal(
    asset: str, timeframe: Timeframe, row: pd.Series, higher_tf: str = "1D", intermediate_tf: str = "4H"
) -> TradingSignal | None:
    zone_direction = row.get("zone_direction")
    if zone_direction not in ("DEMAND", "SUPPLY"):
        return None
    if not row.get("zone_has_fvg"):
        return None

    ema200 = row.get("ema200")
    atr_val = row.get("atr14")
    if pd.isna(ema200) or pd.isna(atr_val):
        return None

    price = row["close"]
    zone_low, zone_high = row["zone_low"], row["zone_high"]
    higher_trend = row.get(f"{higher_tf.lower()}_trend")
    intermediate_trend = row.get(f"{intermediate_tf.lower()}_trend")

    if zone_direction == "DEMAND":
        if not (price > ema200 and higher_trend == "UPTREND"):
            return None
        direction = "LONG"
        stop = zone_low - atr_val
        target = row.get("resistance")
    else:
        if not (price < ema200 and higher_trend == "DOWNTREND"):
            return None
        direction = "SHORT"
        stop = zone_high + atr_val
        target = row.get("support")

    if target is None or pd.isna(target):
        return None

    entry_zone = (zone_low, zone_high)
    entry_price = (zone_low + zone_high) / 2
    risk = abs(entry_price - stop)
    reward = abs(target - entry_price)
    if risk <= 0 or reward <= 0:
        return None

    risk_reward_ratio = reward / risk
    if risk_reward_ratio < MIN_RISK_REWARD_RATIO:
        return None

    confidence_score = 0.75 if intermediate_trend == higher_trend else 0.6

    confirmation_factors = [
        f"{'Demand' if direction == 'LONG' else 'Supply'} zone with a confirming Fair Value Gap",
        f"Price {'above' if direction == 'LONG' else 'below'} the 200-period EMA",
        f"Higher timeframe trend: {higher_trend}",
        f"Intermediate timeframe trend: {intermediate_trend}",
    ]
    invalidating_conditions = [
        f"Price closes {'below' if direction == 'LONG' else 'above'} the zone ({stop:.5f})",
        "Higher-timeframe trend flips before entry is triggered",
    ]
    reasons = [
        f"{direction} setup: price returning to a {timeframe} "
        f"{'demand' if direction == 'LONG' else 'supply'} zone formed by a displacement move with an "
        f"unfilled Fair Value Gap, trading in the direction of both the higher-timeframe trend and the "
        f"200-EMA.",
        f"Risk:Reward {risk_reward_ratio:.2f} meets the minimum bar of {MIN_RISK_REWARD_RATIO}.",
    ]

    return TradingSignal(
        id=str(uuid.uuid4()),
        asset=asset,
        direction=direction,
        timeframe=timeframe,
        setup_type=SETUP_TYPE,
        entry_zone=entry_zone,
        stop_loss=stop,
        take_profit_levels=[target],
        risk_reward_ratio=risk_reward_ratio,
        confirmation_factors=confirmation_factors,
        invalidating_conditions=invalidating_conditions,
        confidence_score=confidence_score,
        reasons=reasons,
        market_conditions=f"zone={zone_direction}, has_fvg={row.get('zone_has_fvg')}",
        timestamp=row["time"] if isinstance(row.get("time"), datetime) else datetime.now(),
    )
