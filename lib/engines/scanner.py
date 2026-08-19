"""Market Scanner (README_forex.md Section 4.9, 5.5).

Runs the Signal Engine across a watchlist and ranks each asset into one of
four fixed tiers. HIGH_QUALITY_SETUPS is allowed — expected — to come back
empty; nothing here force-fills it.
"""

from dataclasses import dataclass

import pandas as pd

from lib.engines.multi_timeframe import MultiTimeframeAnalysis, build_analysis
from lib.engines.signal import generate_signal
from lib.schemas import ScannerTier, Timeframe, TradingSignal


@dataclass
class ScanResult:
    asset: str
    tier: ScannerTier
    analysis: MultiTimeframeAnalysis
    signal: TradingSignal | None


def _classify(analysis: MultiTimeframeAnalysis, signal: TradingSignal | None) -> ScannerTier:
    if signal is not None:
        return "HIGH_QUALITY_SETUPS" if analysis.confirmation_level == "STRONG" else "WATCHLIST"

    # No qualifying signal, but there's still a defined entry zone and a
    # non-conflicting trend read — worth a human glance, not a trade.
    has_structure = bool(analysis.possible_entry_zones) and analysis.confirmation_level == "WEAK"
    if has_structure:
        return "WEAK_SETUPS"

    return "NO_TRADE"


def scan(watchlist: dict[str, pd.DataFrame], timeframe: Timeframe = "1H") -> list[ScanResult]:
    """`watchlist` maps asset -> its joined multi-timeframe frame (last row used).
    Caller is responsible for fetching/building those frames (Streamlit-cached
    per asset) so the scanner itself stays a pure ranking function."""
    results = []
    for asset, joined in watchlist.items():
        if joined.empty:
            continue
        analysis = build_analysis(asset, joined.iloc[-1], higher_tf="1D", intermediate_tf="4H")
        signal = generate_signal(asset, timeframe, analysis)
        tier = _classify(analysis, signal)
        results.append(ScanResult(asset=asset, tier=tier, analysis=analysis, signal=signal))
    return results


def to_leaderboard(results: list[ScanResult]) -> dict[ScannerTier, list[ScanResult]]:
    """Bucket by tier. Note: only HIGH_QUALITY_SETUPS and WATCHLIST entries
    carry a signal — WEAK_SETUPS/NO_TRADE exist by definition *because* no
    signal qualified, so their ScanResult.signal is always None. Callers
    that need the ranked assets in those tiers (not just live signals) want
    this over filtering on `.signal`.
    """
    leaderboard: dict[ScannerTier, list[ScanResult]] = {
        "HIGH_QUALITY_SETUPS": [],
        "WATCHLIST": [],
        "WEAK_SETUPS": [],
        "NO_TRADE": [],
    }
    for result in results:
        leaderboard[result.tier].append(result)
    return leaderboard
