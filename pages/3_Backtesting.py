from datetime import UTC, datetime, timedelta

import pandas as pd
import streamlit as st

from lib.engines.backtest import run_backtest
from lib.engines.multi_timeframe import build_multi_timeframe_series
from lib.market_data.binance import binance_provider

st.set_page_config(page_title="TradeLab — Backtesting", page_icon="📉", layout="wide")

st.title("Backtesting")
st.caption(
    "Historical performance of the trend-aligned pullback setup. "
    "No survivorship bias, no cherry-picked date range — see Limitations below before drawing conclusions."
)

ASSETS = ["BTCUSDT"]
c1, c2 = st.columns(2)
asset = c1.selectbox("Asset", ASSETS)
days = c2.slider("History (days)", min_value=30, max_value=180, value=90, step=30)


@st.cache_data(ttl=600)
def load_joined_frame(asset: str, days: int) -> pd.DataFrame:
    end = datetime.now(UTC)
    start = end - timedelta(days=days)
    candles = binance_provider.get_candles(asset, "1H", start, end)
    df = pd.DataFrame([c.__dict__ for c in candles])
    return build_multi_timeframe_series(asset, df)


try:
    joined = load_joined_frame(asset, days)
    report = run_backtest(asset, joined, "1H")
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
