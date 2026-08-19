"""Rules-based Signal Engine (README_forex.md Section 4.4, 5.2).

Rule: no TradingSignal is created unless predefined criteria are met.
Returning None ("no qualifying setup") is a valid, expected, and common
outcome — never force a signal to fill the UI.
"""

import uuid
from datetime import datetime

from lib.schemas import ConfirmationLevel, MultiTimeframeAnalysis, Timeframe, TradingSignal

# Predefined criteria for the MVP's one setup type: trend-aligned pullback
# to support/resistance. Both thresholds are explicit, defined rules — not
# tuned/optimized — so any signal this engine emits can point back to them.
MIN_CONFIRMATION_LEVELS: set[ConfirmationLevel] = {"STRONG", "MODERATE"}
MIN_RISK_REWARD_RATIO = 1.5

SETUP_TYPE = "trend_aligned_pullback"


def generate_signal(
    asset: str, timeframe: Timeframe, analysis: MultiTimeframeAnalysis
) -> TradingSignal | None:
    if analysis.confirmation_level not in MIN_CONFIRMATION_LEVELS:
        return None
    if not analysis.possible_entry_zones or not analysis.invalidation_levels or not analysis.targets:
        return None
    if analysis.risk_reward_ratio < MIN_RISK_REWARD_RATIO:
        return None

    if analysis.higher_timeframe_trend == "UPTREND":
        direction = "LONG"
    elif analysis.higher_timeframe_trend == "DOWNTREND":
        direction = "SHORT"
    else:
        return None

    confirmation_factors = [
        f"Higher timeframe trend: {analysis.higher_timeframe_trend}",
        f"Intermediate timeframe trend: {analysis.intermediate_trend}",
        f"Lower timeframe structure: {analysis.lower_timeframe_structure}",
        f"Confirmation level: {analysis.confirmation_level}",
    ]
    invalidating_conditions = [
        f"Price closes beyond invalidation level {analysis.invalidation_levels[0]:.2f}",
        "Higher-timeframe trend flips before entry is triggered",
    ]
    confidence_score = {"STRONG": 0.8, "MODERATE": 0.6}[analysis.confirmation_level]

    reasons = [
        f"{direction} setup: {timeframe} pullback into "
        f"{'support' if direction == 'LONG' else 'resistance'} while higher "
        f"timeframes agree on trend direction ({analysis.confirmation_level} confirmation).",
        f"Risk:Reward {analysis.risk_reward_ratio:.2f} meets the minimum bar of {MIN_RISK_REWARD_RATIO}.",
    ]
    if analysis.conflicting_signals:
        reasons.append("Note: " + "; ".join(analysis.conflicting_signals))

    return TradingSignal(
        id=str(uuid.uuid4()),
        asset=asset,
        direction=direction,
        timeframe=timeframe,
        setup_type=SETUP_TYPE,
        entry_zone=analysis.possible_entry_zones[0],
        stop_loss=analysis.invalidation_levels[0],
        take_profit_levels=analysis.targets,
        risk_reward_ratio=analysis.risk_reward_ratio,
        confirmation_factors=confirmation_factors,
        invalidating_conditions=invalidating_conditions,
        confidence_score=confidence_score,
        reasons=reasons,
        market_conditions=f"volatility={analysis.volatility}, momentum={analysis.momentum}",
        timestamp=analysis.timestamp if isinstance(analysis.timestamp, datetime) else datetime.now(),
    )
