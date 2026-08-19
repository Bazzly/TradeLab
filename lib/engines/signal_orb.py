"""Opening Range Breakout Signal Engine (bot.md Section 1.2, lib/engines/orb.py).

Same TradingSignal contract and "no signal unless every rule is met"
discipline as the other two setups. Requires a row from
lib.engines.orb.build_orb_frame.
"""

import uuid
from datetime import datetime

import pandas as pd

from lib.engines.orb import ENTRY_BUFFER_ATR_MULT
from lib.engines.signal import MIN_RISK_REWARD_RATIO
from lib.schemas import Timeframe, TradingSignal

SETUP_TYPE = "opening_range_breakout"


def generate_signal(
    asset: str, timeframe: Timeframe, row: pd.Series, higher_tf: str = "4H", intermediate_tf: str = "1H"
) -> TradingSignal | None:
    direction = row.get("orb_direction")
    if direction not in ("LONG", "SHORT"):
        return None
    if not row.get("orb_has_fvg"):
        return None

    ema200 = row.get("ema200")
    atr_val = row.get("atr14")
    if pd.isna(ema200) or pd.isna(atr_val):
        return None

    price = row["close"]
    range_high, range_low = row["orb_range_high"], row["orb_range_low"]
    higher_trend = row.get(f"{higher_tf.lower()}_trend")
    intermediate_trend = row.get(f"{intermediate_tf.lower()}_trend")

    buffer = ENTRY_BUFFER_ATR_MULT * atr_val

    if direction == "LONG":
        if not (price > ema200 and higher_trend == "UPTREND"):
            return None
        entry_zone = (range_high - buffer, range_high + buffer)
        stop = range_low
        target = row.get("resistance")
    else:
        if not (price < ema200 and higher_trend == "DOWNTREND"):
            return None
        entry_zone = (range_low - buffer, range_low + buffer)
        stop = range_high
        target = row.get("support")

    if target is None or pd.isna(target):
        return None

    entry_price = (entry_zone[0] + entry_zone[1]) / 2
    risk = abs(entry_price - stop)
    reward = abs(target - entry_price)
    if risk <= 0 or reward <= 0:
        return None

    risk_reward_ratio = reward / risk
    if risk_reward_ratio < MIN_RISK_REWARD_RATIO:
        return None

    confidence_score = 0.75 if intermediate_trend == higher_trend else 0.6

    confirmation_factors = [
        f"Aggressive break-and-close outside the opening range (09:30-09:45 NY) with a confirming Fair Value Gap",
        f"Price {'above' if direction == 'LONG' else 'below'} the 200-period EMA",
        f"Higher timeframe trend: {higher_trend}",
        f"Intermediate timeframe trend: {intermediate_trend}",
    ]
    invalidating_conditions = [
        f"Price closes back {'below' if direction == 'LONG' else 'above'} the opposite side of the "
        f"opening range ({stop:.5f})",
        "Higher-timeframe trend flips before entry is triggered",
    ]
    reasons = [
        f"{direction} setup: pullback to the opening range boundary after an aggressive breakout, "
        f"trading in the direction of both the higher-timeframe trend and the 200-EMA.",
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
        market_conditions=f"orb_direction={direction}, has_fvg={row.get('orb_has_fvg')}",
        timestamp=row["time"] if isinstance(row.get("time"), datetime) else datetime.now(),
    )
