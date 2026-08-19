import pandas as pd
import streamlit as st

from lib.data import load_joined_frame
from lib.engines.multi_timeframe import build_analysis
from lib.engines.signal import generate_signal as generate_pullback_signal
from lib.engines.signal_supply_demand import generate_signal as generate_supply_demand_signal
from lib.market_data.registry import ALL_ASSETS, FOREX_ASSETS, default_asset

st.set_page_config(page_title="TradeLab — Strategy Lab", page_icon="🧪", layout="wide")

st.title("Strategy Lab")
st.caption(
    "\"No qualifying setup\" is a normal, expected outcome for either setup below — not an error."
)

c1, c2 = st.columns(2)
asset = c1.selectbox("Asset", ALL_ASSETS, index=ALL_ASSETS.index(default_asset()))
setup = c2.selectbox("Setup", ["Trend-Aligned Pullback", "Supply & Demand + FVG"])
price_decimals = 5 if asset in FOREX_ASSETS else 2

try:
    joined = load_joined_frame(asset)
except Exception as err:  # noqa: BLE001
    st.error(f"Could not load market data: {err}")
    st.stop()

row = joined.iloc[-1]

if setup == "Trend-Aligned Pullback":
    analysis = build_analysis(asset, row, higher_tf="1D", intermediate_tf="4H")

    m1, m2, m3 = st.columns(3)
    m1.metric("Higher TF trend (1D)", analysis.higher_timeframe_trend)
    m2.metric("Intermediate TF trend (4H)", analysis.intermediate_trend)
    m3.metric("Lower TF structure (1H)", analysis.lower_timeframe_structure)

    m4, m5, m6 = st.columns(3)
    m4.metric("Momentum", analysis.momentum)
    m5.metric("Volatility", analysis.volatility)
    m6.metric("Confirmation level", analysis.confirmation_level)

    if analysis.conflicting_signals:
        st.warning(" / ".join(analysis.conflicting_signals))

    st.caption(
        f"Key support/resistance: "
        f"{', '.join(f'{lv:,.{price_decimals}f}' for lv in analysis.key_support_resistance)}"
    )

    signal = generate_pullback_signal(asset, "1H", analysis)
else:
    zone = row.get("zone_direction")
    m1, m2, m3 = st.columns(3)
    m1.metric("Active zone", zone or "None")
    m2.metric("Zone has Fair Value Gap", "Yes" if row.get("zone_has_fvg") else "No")
    ema200 = row.get("ema200")
    if pd.isna(ema200):
        ema_position = "Unknown (not enough history yet)"
    else:
        ema_position = "Above" if row["close"] > ema200 else "Below"
    m3.metric("Price vs 200 EMA", ema_position)

    m4, m5 = st.columns(2)
    m4.metric("Higher TF trend (1D)", row.get("1d_trend", "UNKNOWN"))
    m5.metric("Intermediate TF trend (4H)", row.get("4h_trend", "UNKNOWN"))

    if zone:
        st.caption(f"Zone range: {row['zone_low']:,.{price_decimals}f} – {row['zone_high']:,.{price_decimals}f}")

    signal = generate_supply_demand_signal(asset, "1H", row, higher_tf="1D", intermediate_tf="4H")

st.divider()

if signal is None:
    st.info(
        "**No qualifying setup right now.** Criteria not met — this is the expected "
        "default state, not a bug."
    )
else:
    st.success(f"**{signal.direction} setup found** — confidence {signal.confidence_score:.0%}")
    s1, s2, s3 = st.columns(3)
    s1.metric("Entry zone", f"{signal.entry_zone[0]:,.{price_decimals}f} – {signal.entry_zone[1]:,.{price_decimals}f}")
    s2.metric("Stop loss", f"{signal.stop_loss:,.{price_decimals}f}")
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
