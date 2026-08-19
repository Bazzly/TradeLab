import pandas as pd
import streamlit as st

from lib.data import load_joined_frame
from lib.engines.backtest import run_backtest
from lib.engines.signal_supply_demand import SETUP_TYPE as SUPPLY_DEMAND_SETUP_TYPE
from lib.engines.signal_supply_demand import generate_signal as generate_supply_demand_signal
from lib.market_data.registry import ALL_ASSETS, default_asset

st.set_page_config(page_title="TradeLab — Backtesting", page_icon="📉", layout="wide")

st.title("Backtesting")
st.caption(
    "No survivorship bias, no cherry-picked date range — see Limitations below before drawing conclusions."
)

c1, c2, c3 = st.columns(3)
asset = c1.selectbox("Asset", ALL_ASSETS, index=ALL_ASSETS.index(default_asset()))
setup = c2.selectbox("Setup", ["Trend-Aligned Pullback", "Supply & Demand + FVG"])
days = c3.slider("History (days)", min_value=30, max_value=180, value=90, step=30)

try:
    joined = load_joined_frame(asset, days)
    if setup == "Trend-Aligned Pullback":
        report = run_backtest(asset, joined, "1H")
    else:
        def supply_demand_signal_fn(asset, timeframe, row):
            return generate_supply_demand_signal(asset, timeframe, row, higher_tf="1D", intermediate_tf="4H")

        report = run_backtest(
            asset, joined, "1H", signal_fn=supply_demand_signal_fn, setup_type=SUPPLY_DEMAND_SETUP_TYPE
        )
except Exception as err:  # noqa: BLE001
    st.error(f"Backtest failed: {err}")
    st.stop()

st.subheader(f"{report.sample_size} trades — {report.date_range[0]} to {report.date_range[1]}")

if report.sample_size < 30:
    st.warning(
        f"Only {report.sample_size} trades in this window. Treat every statistic below as "
        "**preliminary** — not a reliable estimate of edge (README_forex.md Section 2)."
    )

m1, m2, m3, m4 = st.columns(4)
m1.metric("Win rate", f"{report.win_rate:.0%}")
m2.metric("Profit factor", f"{report.profit_factor:.2f}" if report.profit_factor != float("inf") else "∞")
m3.metric("Expectancy (R)", f"{report.expectancy:.2f}")
m4.metric("Max drawdown (R)", f"{report.max_drawdown:.2f}")

m5, m6, m7, m8 = st.columns(4)
m5.metric("Avg win (R)", f"{report.avg_win:.2f}")
m6.metric("Avg loss (R)", f"{report.avg_loss:.2f}")
m7.metric("Longest win streak", report.consecutive_wins)
m8.metric("Longest loss streak", report.consecutive_losses)

if report.monthly_performance:
    st.subheader("Monthly performance (R)")
    monthly_df = pd.DataFrame(report.monthly_performance).set_index("month")
    st.bar_chart(monthly_df)

if report.overfitting_flags:
    st.subheader("Flags")
    for flag in report.overfitting_flags:
        st.markdown(f"- ⚠️ {flag}")

st.subheader("Limitations")
st.markdown(report.limitations)
