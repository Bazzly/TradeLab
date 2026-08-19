import pandas as pd
import streamlit as st

from lib.content.share import build_scanner_share_text, build_stat_card_image, render_share_section
from lib.data import load_joined_frame
from lib.engines.scanner import scan
from lib.market_data.registry import ALL_ASSETS

st.set_page_config(page_title="TradeLab — Scanner", page_icon="🔎", layout="wide")

st.title("Market Scanner")
st.caption(
    "Runs the same rules-based Signal Engine across a watchlist. An empty "
    "High-Quality tier is a normal, expected result — never force-filled."
)

WATCHLIST = ALL_ASSETS

TIER_LABELS = {
    "HIGH_QUALITY_SETUPS": "🟢 High-Quality Setups",
    "WATCHLIST": "🟡 Watchlist",
    "WEAK_SETUPS": "⚪ Weak Setups",
    "NO_TRADE": "🔴 No Trade",
}


def load_frame(asset: str) -> pd.DataFrame | None:
    # load_joined_frame itself is cached (lib/data.py) and shared with every
    # other page — this wrapper only exists to keep one bad asset from
    # aborting the whole scan.
    try:
        return load_joined_frame(asset)
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

st.divider()
st.subheader("Share")
tier_counts = {tier: len(entries) for tier, entries in by_tier.items()}
top_picks = [
    {"asset": r.asset, "direction": r.signal.direction, "confidence": r.signal.confidence_score}
    for r in by_tier["HIGH_QUALITY_SETUPS"]
    if r.signal
]
share_text = build_scanner_share_text(tier_counts, top_picks)
card_bytes = build_stat_card_image(
    "Market Scanner",
    f"{len(WATCHLIST)} assets scanned",
    [
        ("🟢 High-Quality", str(tier_counts.get("HIGH_QUALITY_SETUPS", 0))),
        ("🟡 Watchlist", str(tier_counts.get("WATCHLIST", 0))),
        ("⚪ Weak Setups", str(tier_counts.get("WEAK_SETUPS", 0))),
        ("🔴 No Trade", str(tier_counts.get("NO_TRADE", 0))),
    ],
)
render_share_section(
    share_text,
    image_bytes=card_bytes,
    image_filename="tradelab-scan.png",
    url="https://tradelab.streamlit.app/Scanner",
)
