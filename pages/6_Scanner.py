from datetime import UTC, datetime, timedelta

import pandas as pd
import streamlit as st

from lib.engines.multi_timeframe import build_multi_timeframe_series
from lib.engines.scanner import scan
from lib.market_data.coinbase import coinbase_provider

st.set_page_config(page_title="TradeLab — Scanner", page_icon="🔎", layout="wide")

st.title("Market Scanner")
st.caption(
    "Runs the same rules-based Signal Engine across a watchlist. An empty "
    "High-Quality tier is a normal, expected result — never force-filled."
)

WATCHLIST = ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "ADA/USD", "DOGE/USD", "LTC/USD", "LINK/USD"]

TIER_LABELS = {
    "HIGH_QUALITY_SETUPS": "🟢 High-Quality Setups",
    "WATCHLIST": "🟡 Watchlist",
    "WEAK_SETUPS": "⚪ Weak Setups",
    "NO_TRADE": "🔴 No Trade",
}


@st.cache_data(ttl=300)
def load_frame(asset: str) -> pd.DataFrame | None:
    try:
        end = datetime.now(UTC)
        start = end - timedelta(days=90)
        candles = coinbase_provider.get_candles(asset, "1H", start, end)
        df = pd.DataFrame([c.__dict__ for c in candles])
        return build_multi_timeframe_series(asset, df)
    except Exception:  # noqa: BLE001 — surfaced per-asset below, scan continues for the rest
        return None


progress = st.progress(0.0, text="Scanning watchlist...")
frames: dict[str, pd.DataFrame] = {}
failed: list[str] = []
for i, asset in enumerate(WATCHLIST):
    frame = load_frame(asset)
    if frame is not None:
        frames[asset] = frame
    else:
        failed.append(asset)
    progress.progress((i + 1) / len(WATCHLIST), text=f"Scanning {asset}...")
progress.empty()

if failed:
    st.warning(f"Could not load data for: {', '.join(failed)} — excluded from this scan.")

results = scan(frames)
by_tier = {tier: [r for r in results if r.tier == tier] for tier in TIER_LABELS}

tier_cols = st.columns(4)
for col, (tier, label) in zip(tier_cols, TIER_LABELS.items()):
    col.metric(label, len(by_tier[tier]))

st.divider()

for tier, label in TIER_LABELS.items():
    entries = by_tier[tier]
    st.subheader(f"{label} ({len(entries)})")
    if not entries:
        st.caption("Nothing in this tier right now.")
        continue

    rows = []
    for r in entries:
        row = {
            "Asset": r.asset,
            "Higher TF": r.analysis.higher_timeframe_trend,
            "Confirmation": r.analysis.confirmation_level,
            "Momentum": r.analysis.momentum,
        }
        if r.signal:
            row.update(
                {
                    "Direction": r.signal.direction,
                    "R:R": round(r.signal.risk_reward_ratio, 2),
                    "Confidence": f"{r.signal.confidence_score:.0%}",
                }
            )
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), width="stretch")
