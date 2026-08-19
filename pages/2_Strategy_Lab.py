from datetime import UTC, datetime, timedelta

import pandas as pd
import streamlit as st

from lib.engines.multi_timeframe import build_analysis, build_multi_timeframe_series
from lib.engines.signal import generate_signal
from lib.market_data.binance import binance_provider

st.set_page_config(page_title="TradeLab — Strategy Lab", page_icon="🧪", layout="wide")

st.title("Strategy Lab")
st.caption(
    "One rules-based setup: trend-aligned pullback to support/resistance. "
    "\"No qualifying setup\" is a normal, expected outcome — not an error."
)

ASSETS = ["BTCUSDT"]
asset = st.selectbox("Asset", ASSETS)


@st.cache_data(ttl=300)
def load_joined_frame(asset: str) -> pd.DataFrame:
    end = datetime.now(UTC)
    start = end - timedelta(days=90)
    candles = binance_provider.get_candles(asset, "1H", start, end)
    df = pd.DataFrame([c.__dict__ for c in candles])
    return build_multi_timeframe_series(asset, df)


try:
    joined = load_joined_frame(asset)
except Exception as err:  # noqa: BLE001
    st.error(f"Could not load market data: {err}")
    st.stop()

analysis = build_analysis(asset, joined.iloc[-1], higher_tf="1D", intermediate_tf="4H")

c1, c2, c3 = st.columns(3)
c1.metric("Higher TF trend (1D)", analysis.higher_timeframe_trend)
c2.metric("Intermediate TF trend (4H)", analysis.intermediate_trend)
c3.metric("Lower TF structure (1H)", analysis.lower_timeframe_structure)

c4, c5, c6 = st.columns(3)
c4.metric("Momentum", analysis.momentum)
c5.metric("Volatility", analysis.volatility)
c6.metric("Confirmation level", analysis.confirmation_level)

if analysis.conflicting_signals:
    st.warning(" / ".join(analysis.conflicting_signals))

st.divider()

signal = generate_signal(asset, "1H", analysis)

if signal is None:
    st.info(
        "**No qualifying setup right now.** Criteria not met "
        "(confirmation level, risk:reward, or trend direction) — this is the expected "
        "default state, not a bug."
    )
else:
    st.success(f"**{signal.direction} setup found** — confidence {signal.confidence_score:.0%}")
    s1, s2, s3 = st.columns(3)
    s1.metric("Entry zone", f"{signal.entry_zone[0]:,.2f} – {signal.entry_zone[1]:,.2f}")
    s2.metric("Stop loss", f"{signal.stop_loss:,.2f}")
    s3.metric("Risk:Reward", f"{signal.risk_reward_ratio:.2f}")

    st.markdown("**Why:**")
    for reason in signal.reasons:
        st.markdown(f"- {reason}")

    st.markdown("**Confirmation factors:**")
    for factor in signal.confirmation_factors:
        st.markdown(f"- {factor}")

    st.markdown("**Invalidating conditions:**")
    for cond in signal.invalidating_conditions:
        st.markdown(f"- {cond}")

st.caption(
    f"Key support/resistance: {', '.join(f'{lv:,.2f}' for lv in analysis.key_support_resistance)}"
)
