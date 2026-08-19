"""Empirical, backtest-derived confidence (README_forex.md Section 11 —
the honest reframe of "predict the next signal": real historical win-rate
for this exact rule on this exact asset, not a forecast of future price).

Separate from TradingSignal.confidence_score, which stays the static
rule-confirmation-tier heuristic (STRONG/MODERATE -> 0.6-0.8) used
unchanged inside lib.engines.backtest's own simulation. This module MUST
NOT be called from inside a backtest's per-bar signal_fn — it runs its own
backtest internally, so calling it per-bar during another backtest would
turn an O(n) simulation into O(n^2). It's for the display layer only
(Strategy Lab, Scanner, the paper trading bot).
"""

from dataclasses import dataclass

import streamlit as st

from lib.data import load_joined_frame, load_orb_frame
from lib.engines.backtest import run_backtest
from lib.engines.multi_timeframe import build_analysis
from lib.engines.signal import SETUP_TYPE as PULLBACK_SETUP_TYPE
from lib.engines.signal import generate_signal as generate_pullback_signal
from lib.engines.signal_orb import SETUP_TYPE as ORB_SETUP_TYPE
from lib.engines.signal_orb import generate_signal as generate_orb_signal
from lib.engines.signal_supply_demand import SETUP_TYPE as SUPPLY_DEMAND_SETUP_TYPE
from lib.engines.signal_supply_demand import generate_signal as generate_supply_demand_signal

MIN_RELIABLE_SAMPLE = 30  # matches backtest.py's own reliability floor

SETUP_KEYS = ("pullback", "supply_demand", "orb")


@dataclass
class EmpiricalConfidence:
    win_rate: float
    sample_size: int
    expectancy: float
    profit_factor: float

    @property
    def reliable(self) -> bool:
        return self.sample_size >= MIN_RELIABLE_SAMPLE


@st.cache_data(ttl=3600)
def get_empirical_confidence(asset: str, setup_key: str, days: int = 90) -> EmpiricalConfidence:
    if setup_key == "pullback":
        joined = load_joined_frame(asset, days)

        def signal_fn(a, tf, row):
            analysis = build_analysis(a, row, higher_tf="1D", intermediate_tf="4H")
            return generate_pullback_signal(a, tf, analysis)

        report = run_backtest(asset, joined, "1H", signal_fn=signal_fn, setup_type=PULLBACK_SETUP_TYPE)

    elif setup_key == "supply_demand":
        joined = load_joined_frame(asset, days)

        def signal_fn(a, tf, row):
            return generate_supply_demand_signal(a, tf, row, higher_tf="1D", intermediate_tf="4H")

        report = run_backtest(asset, joined, "1H", signal_fn=signal_fn, setup_type=SUPPLY_DEMAND_SETUP_TYPE)

    elif setup_key == "orb":
        joined = load_orb_frame(asset, days)

        def signal_fn(a, tf, row):
            return generate_orb_signal(a, tf, row, higher_tf="4H", intermediate_tf="1H")

        report = run_backtest(asset, joined, "15m", signal_fn=signal_fn, setup_type=ORB_SETUP_TYPE)

    else:
        raise ValueError(f"Unknown setup_key: {setup_key}")

    return EmpiricalConfidence(
        win_rate=report.win_rate,
        sample_size=report.sample_size,
        expectancy=report.expectancy,
        profit_factor=report.profit_factor,
    )
