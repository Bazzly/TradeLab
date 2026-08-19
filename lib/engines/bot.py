"""Paper Trading Bot (README_forex.md Section 8 Phase 8, Section 11).

Runs on each visit to the Bot page — Streamlit apps don't run continuously
in the background, so "the bot" only actually checks anything when someone
loads the page. Trade state persists in Neon (lib/db/bot_trades.py) so it
still accumulates a real track record across visits rather than resetting
every time, but "continuous real-time" it is not — documented, not hidden.

For each (asset, setup) pair with no trade already in flight: generate a
signal exactly the way Strategy Lab/Scanner would, and if one fires, log a
PENDING trade. For every PENDING/OPEN trade, scan candles since it was
logged for an entry-zone touch, then a stop/target hit — the exact same
touch-then-resolve logic backtest.py's `_simulate_trades` uses, just walking
forward from "when the trade was logged" to "now" instead of across all of
history.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from lib.data import load_joined_frame, load_orb_frame
from lib.db.bot_trades import close_trade, create_pending_trade, expire_trade, fill_entry, get_active_trade
from lib.engines.multi_timeframe import build_analysis
from lib.engines.signal import SETUP_TYPE as PULLBACK_SETUP_TYPE
from lib.engines.signal import generate_signal as generate_pullback_signal
from lib.engines.signal_orb import SETUP_TYPE as ORB_SETUP_TYPE
from lib.engines.signal_orb import generate_signal as generate_orb_signal
from lib.engines.signal_supply_demand import SETUP_TYPE as SUPPLY_DEMAND_SETUP_TYPE
from lib.engines.signal_supply_demand import generate_signal as generate_supply_demand_signal
from lib.schemas import TradingSignal

ENTRY_EXPIRY_BARS = 20  # same constant/meaning as backtest.py

SETUPS = {
    "pullback": PULLBACK_SETUP_TYPE,
    "supply_demand": SUPPLY_DEMAND_SETUP_TYPE,
    "orb": ORB_SETUP_TYPE,
}


def _naive_utc(dt: datetime) -> datetime:
    """`timestamptz` columns come back from psycopg as timezone-aware
    datetimes; every candle DataFrame in this app uses naive-but-UTC
    timestamps (lib/market_data/provider.py's convention). Comparing the
    two directly raises in pandas ("Invalid comparison between
    dtype=datetime64[us] and datetime") — confirmed live, not theoretical.
    """
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def _load_frame_and_generate(asset: str, setup_key: str) -> tuple[pd.DataFrame, TradingSignal | None, str]:
    if setup_key == "pullback":
        joined = load_joined_frame(asset)
        analysis = build_analysis(asset, joined.iloc[-1], higher_tf="1D", intermediate_tf="4H")
        return joined, generate_pullback_signal(asset, "1H", analysis), "1H"
    elif setup_key == "supply_demand":
        joined = load_joined_frame(asset)
        signal = generate_supply_demand_signal(asset, "1H", joined.iloc[-1], higher_tf="1D", intermediate_tf="4H")
        return joined, signal, "1H"
    else:  # orb
        joined = load_orb_frame(asset)
        signal = generate_orb_signal(asset, "15m", joined.iloc[-1], higher_tf="4H", intermediate_tf="1H")
        return joined, signal, "15m"


def _advance_pending(trade: dict, joined: pd.DataFrame) -> None:
    since = joined[joined["time"] > _naive_utc(trade["signal_timestamp"])]
    zone_lo, zone_hi = float(trade["entry_zone_low"]), float(trade["entry_zone_high"])

    bars_waited = 0
    for _, row in since.iterrows():
        bars_waited += 1
        if row["low"] <= zone_hi and row["high"] >= zone_lo:
            fill_entry(trade["id"], (zone_lo + zone_hi) / 2, row["time"])
            return
        if bars_waited > ENTRY_EXPIRY_BARS:
            expire_trade(trade["id"])
            return


def _advance_open(trade: dict, joined: pd.DataFrame) -> None:
    since = joined[joined["time"] > _naive_utc(trade["entry_filled_at"])]
    direction = trade["direction"]
    entry_price = float(trade["entry_price"])
    stop = float(trade["stop_loss"])
    target = float(trade["target"])
    risk = abs(entry_price - stop)

    for _, row in since.iterrows():
        hit_stop = row["low"] <= stop if direction == "LONG" else row["high"] >= stop
        hit_target = row["high"] >= target if direction == "LONG" else row["low"] <= target
        if hit_stop:
            pnl = (stop - entry_price) if direction == "LONG" else (entry_price - stop)
            close_trade(trade["id"], stop, "STOP", pnl / risk if risk > 0 else 0.0, row["time"])
            return
        if hit_target:
            pnl = (target - entry_price) if direction == "LONG" else (entry_price - target)
            close_trade(trade["id"], target, "TARGET", pnl / risk if risk > 0 else 0.0, row["time"])
            return


@st.cache_data(ttl=300)
def refresh_bot(watchlist: list[str]) -> list[str]:
    """Returns a list of human-readable notes about what happened this
    refresh (new trades opened, fills, closes) — for a status message, not
    required for the bot to function.

    Cached deliberately: this has real side effects (DB writes), and the
    underlying candle data it reads is itself cached for the same 300s in
    lib/data.py — re-running the full check within that window would just
    re-derive the same result at the cost of ~39 DB round-trips (13 assets
    x 3 setups) for nothing.
    """
    notes = []
    for asset in watchlist:
        for setup_key, setup_type in SETUPS.items():
            try:
                active = get_active_trade(asset, setup_type)
                joined, signal, _timeframe = _load_frame_and_generate(asset, setup_key)

                if active is None:
                    if signal is not None:
                        create_pending_trade(asset, setup_type, signal)
                        notes.append(f"New {signal.direction} signal logged: {asset} / {setup_type}")
                elif active["status"] == "PENDING":
                    _advance_pending(active, joined)
                elif active["status"] == "OPEN":
                    _advance_open(active, joined)
            except Exception as err:  # noqa: BLE001 — one bad asset/setup shouldn't stop the rest
                notes.append(f"Could not refresh {asset} / {setup_key}: {err}")
    return notes
