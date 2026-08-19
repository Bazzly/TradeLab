from datetime import UTC, datetime, timedelta

import pandas as pd
import streamlit as st

from lib.content.share import build_share_pdf, build_share_text, build_stat_card_image, render_share_section
from lib.data import load_joined_frame, load_orb_frame
from lib.db.bot_trades import list_trades
from lib.db.connection import is_configured
from lib.engines.bot import refresh_bot
from lib.engines.confidence import SETUP_KEYS, get_empirical_confidence
from lib.market_data.registry import ALL_ASSETS, FOREX_ASSETS

st.set_page_config(page_title="TradeLab — Bot", page_icon="🤖", layout="wide")

st.title("Paper Trading Bot")
st.caption(
    "Automatically opens, tracks, and closes simulated trades when a setup qualifies — same "
    "engines, same rules as Strategy Lab, just running continuously instead of on-demand. "
    "**Not real money, not a signal service** — a live demonstration of what following these "
    "exact rules would have done."
)
st.info(
    "Streamlit apps don't run in the background — this only checks for new signals and "
    "updates open trades when this page is loaded, not truly in real time between visits. "
    "State persists in the database, so the trade log still builds a real track record across visits."
)

SETUP_LABELS = {
    "pullback": "Trend-Aligned Pullback",
    "supply_demand": "Supply & Demand + FVG",
    "orb": "Opening Range Breakout",
}

if not is_configured():
    st.warning("`DATABASE_URL` isn't set — the bot needs a Neon database to persist its trade log.")
    st.stop()

with st.spinner("Refreshing bot (checking for new signals, updating open trades)..."):
    notes = refresh_bot(ALL_ASSETS)

if notes:
    with st.expander(f"This refresh: {len(notes)} update(s)", expanded=True):
        for note in notes:
            st.markdown(f"- {note}")

st.divider()

trades = list_trades()
open_trades = [t for t in trades if t["status"] in ("PENDING", "OPEN")]
closed_trades = [t for t in trades if t["status"] == "CLOSED"]

# --- Track record summary ---------------------------------------------------
st.subheader("Track Record")
if closed_trades:
    wins = [t for t in closed_trades if float(t["r_multiple"] or 0) > 0]
    win_rate = len(wins) / len(closed_trades)
    total_r = sum(float(t["r_multiple"] or 0) for t in closed_trades)
    c1, c2, c3 = st.columns(3)
    c1.metric("Closed trades", len(closed_trades))
    c2.metric("Win rate", f"{win_rate:.0%}")
    c3.metric("Total R", f"{total_r:+.2f}")
    if len(closed_trades) < 30:
        st.caption(
            f"Only {len(closed_trades)} closed trades so far — same rule as everywhere else in "
            "this app: treat this as preliminary until there's a real sample size."
        )
else:
    st.caption("No closed trades yet — the track record builds up as open trades resolve.")

st.divider()

# --- Share -------------------------------------------------------------------
st.subheader("Share")
share_text = build_share_text(open_trades, closed_trades)
pdf_bytes = build_share_pdf(open_trades, closed_trades)

n_closed = len(closed_trades)
wins = [t for t in closed_trades if float(t["r_multiple"] or 0) > 0]
win_rate = (len(wins) / n_closed) if n_closed else 0.0
total_r = sum(float(t["r_multiple"] or 0) for t in closed_trades)
card_bytes = build_stat_card_image(
    "Paper Trading Bot — Track Record",
    f"{len(open_trades)} open/pending across 3 rules-based setups",
    [
        ("Closed trades", str(n_closed)),
        ("Win rate", f"{win_rate:.0%}" if n_closed else "—"),
        ("Total R", f"{total_r:+.2f}" if n_closed else "—"),
    ],
    sample_size=n_closed,
    reliable=n_closed >= 30,
)

render_share_section(
    share_text,
    pdf_bytes=pdf_bytes,
    pdf_filename=f"tradelab-bot-report-{datetime.now(UTC).strftime('%Y-%m-%d')}.pdf",
    image_bytes=card_bytes,
    image_filename="tradelab-bot-report.png",
)

st.divider()

# --- Open / pending trades ---------------------------------------------------
st.subheader(f"Open & Pending ({len(open_trades)})")
if not open_trades:
    st.caption("Nothing open right now — that's a normal state, not an error.")
for t in open_trades:
    decimals = 5 if t["asset"] in FOREX_ASSETS else 2
    label = f"{t['asset']} — {SETUP_LABELS.get(t['setup_type'], t['setup_type'])} — {t['direction']} — {t['status']}"
    with st.expander(label):
        c1, c2, c3 = st.columns(3)
        c1.metric("Entry zone", f"{float(t['entry_zone_low']):,.{decimals}f} – {float(t['entry_zone_high']):,.{decimals}f}")
        c2.metric("Stop loss", f"{float(t['stop_loss']):,.{decimals}f}")
        c3.metric("Target", f"{float(t['target']):,.{decimals}f}")
        st.caption(f"Risk:Reward {float(t['risk_reward_ratio']):.2f} — logged {t['signal_timestamp']}")
        if t["reasons"]:
            st.markdown("**Why:**")
            for r in t["reasons"]:
                st.markdown(f"- {r}")

st.divider()

# --- Closed trades ------------------------------------------------------------
st.subheader(f"Closed ({len(closed_trades)})")
if closed_trades:
    df = pd.DataFrame(
        [
            {
                "Asset": t["asset"],
                "Setup": SETUP_LABELS.get(t["setup_type"], t["setup_type"]),
                "Direction": t["direction"],
                "Exit reason": t["exit_reason"],
                "R multiple": round(float(t["r_multiple"] or 0), 2),
                "Closed": t["closed_at"],
            }
            for t in closed_trades
        ]
    )
    st.dataframe(df, width="stretch")
else:
    st.caption("No closed trades yet.")

st.divider()

# --- Readiness board -----------------------------------------------------------
st.subheader("Readiness Board")
st.caption(
    "How close each asset is to a signal right now, per setup — rules-based state, not a "
    "prediction of what price will do next."
)

setup_choice = st.selectbox("Setup", SETUP_KEYS, format_func=lambda k: SETUP_LABELS[k])

rows = []
for asset in ALL_ASSETS:
    try:
        if setup_choice == "orb":
            row = load_orb_frame(asset).iloc[-1]
            rows.append(
                {
                    "Asset": asset,
                    "Breakout": row.get("orb_direction") or "—",
                    "Has FVG": "✅" if row.get("orb_has_fvg") else "—",
                    "4H trend": row.get("4h_trend", "UNKNOWN"),
                }
            )
        elif setup_choice == "supply_demand":
            row = load_joined_frame(asset).iloc[-1]
            zone = row.get("zone_direction")
            ema200 = row.get("ema200")
            above_ema = "Above" if pd.notna(ema200) and row["close"] > ema200 else "Below" if pd.notna(ema200) else "—"
            rows.append(
                {
                    "Asset": asset,
                    "Zone": zone or "—",
                    "Has FVG": "✅" if row.get("zone_has_fvg") else "—",
                    "Price vs 200 EMA": above_ema,
                    "1D trend": row.get("1d_trend", "UNKNOWN"),
                }
            )
        else:
            row = load_joined_frame(asset).iloc[-1]
            trends = [row.get("trend", "UNKNOWN"), row.get("4h_trend", "UNKNOWN"), row.get("1d_trend", "UNKNOWN")]
            if "UNKNOWN" in trends:
                alignment = "Insufficient history"
            elif trends.count("UPTREND") == 3 or trends.count("DOWNTREND") == 3:
                alignment = "All 3 agree"
            elif trends.count("UPTREND") == 2 or trends.count("DOWNTREND") == 2:
                alignment = "2 of 3 agree"
            else:
                alignment = "Mixed / sideways"
            rows.append(
                {
                    "Asset": asset,
                    "1H structure": trends[0],
                    "4H trend": trends[1],
                    "1D trend": trends[2],
                    "Alignment": alignment,
                }
            )
    except Exception:  # noqa: BLE001
        continue

if rows:
    st.dataframe(pd.DataFrame(rows), width="stretch")

st.divider()

# --- Empirical confidence -------------------------------------------------------
st.subheader("Historical Track Record by Setup")
st.caption(
    "Real backtested win-rate for this exact setup on this exact asset — not a forecast, a "
    "report card. Sample size always shown; treat anything under ~30 trades as preliminary."
)
conf_asset = st.selectbox("Asset", ALL_ASSETS, key="conf_asset")
conf_rows = []
for setup_key in SETUP_KEYS:
    try:
        conf = get_empirical_confidence(conf_asset, setup_key)
        conf_rows.append(
            {
                "Setup": SETUP_LABELS[setup_key],
                "Win rate": f"{conf.win_rate:.0%}",
                "Sample size": conf.sample_size,
                "Expectancy (R)": round(conf.expectancy, 2),
                "Reliable?": "Yes" if conf.reliable else f"No (<{30})",
            }
        )
    except Exception:  # noqa: BLE001
        continue
if conf_rows:
    st.dataframe(pd.DataFrame(conf_rows), width="stretch")
