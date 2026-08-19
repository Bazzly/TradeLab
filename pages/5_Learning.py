import pandas as pd
import streamlit as st

from lib.content.illustrations import (
    candlesticks_example,
    fvg_supply_demand_example,
    market_structure_example,
    orb_example,
    risk_management_example,
    signal_pipeline_example,
    support_resistance_example,
    trend_filters_example,
)
from lib.content.lessons import LESSONS
from lib.data import load_candles, load_joined_frame, load_orb_frame
from lib.engines.multi_timeframe import build_analysis
from lib.engines.risk import position_size
from lib.engines.signal import generate_signal as generate_pullback_signal
from lib.engines.signal_orb import generate_signal as generate_orb_signal
from lib.engines.signal_supply_demand import generate_signal as generate_supply_demand_signal
from lib.market_data.registry import ALL_ASSETS, FOREX_ASSETS, default_asset

ILLUSTRATIONS = {
    "market_structure": market_structure_example,
    "candlesticks": candlesticks_example,
    "support_resistance": support_resistance_example,
    "risk_management": risk_management_example,
    "fvg_supply_demand": fvg_supply_demand_example,
    "trend_filters": trend_filters_example,
    "orb": orb_example,
    "signal_pipeline": signal_pipeline_example,
}

st.set_page_config(page_title="TradeLab — Learning", page_icon="🎓", layout="wide")

st.title("Learning")
st.caption(
    "Beginner-to-practical curriculum: the concepts TradeLab's engines are actually built on, "
    "each one demonstrated against real, current data — not just described. "
    "Progress tracking is session-only for now."
)

if "completed_lessons" not in st.session_state:
    st.session_state.completed_lessons = set()

titles = [lesson.title for lesson in LESSONS]
selected_title = st.sidebar.radio("Lessons", titles)
lesson = next(lesson for lesson in LESSONS if lesson.title == selected_title)

st.header(lesson.title)
st.caption(lesson.summary)

if lesson.live_example in ILLUSTRATIONS:
    st.plotly_chart(ILLUSTRATIONS[lesson.live_example](), width="stretch", key=f"illustration_{lesson.id}")
    st.caption(
        "⚠️ Illustrative example — hand-built to make this one concept clear, **not real market "
        "data**. See \"Try it live\" below for what's actually happening right now."
    )

st.markdown(lesson.body)

st.divider()

is_done = lesson.id in st.session_state.completed_lessons
done = st.checkbox("Mark as read", value=is_done, key=f"done_{lesson.id}")
if done:
    st.session_state.completed_lessons.add(lesson.id)
else:
    st.session_state.completed_lessons.discard(lesson.id)

progress = len(st.session_state.completed_lessons) / len(LESSONS)
st.progress(progress, text=f"{len(st.session_state.completed_lessons)}/{len(LESSONS)} lessons read this session")

# --- Live example ----------------------------------------------------------
if lesson.live_example:
    st.divider()
    st.subheader("Try it live")

    asset = st.selectbox(
        "Asset", ALL_ASSETS, index=ALL_ASSETS.index(default_asset()), key=f"asset_{lesson.id}"
    )
    price_decimals = 5 if asset in FOREX_ASSETS else 2

    try:
        if lesson.live_example == "market_structure":
            joined = load_joined_frame(asset)
            row = joined.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric("1H structure (right now)", row.get("trend", "UNKNOWN"))
            c2.metric("4H trend", row.get("4h_trend", "UNKNOWN"))
            c3.metric("1D trend", row.get("1d_trend", "UNKNOWN"))
            st.caption(
                f"These are the exact `trend` values TradeLab's Multi-Timeframe Analysis Engine "
                f"computes for {asset} right now — same numbers the Strategy Lab page reads."
            )

        elif lesson.live_example == "candlesticks":
            candles = load_candles(asset, "1H", 2)
            last = candles.iloc[-1]
            if last["close"] > last["open"]:
                direction = "Bullish (close above open)"
            elif last["close"] < last["open"]:
                direction = "Bearish (close below open)"
            else:
                direction = "Doji (close equals open)"
            st.metric("Most recent 1H candle", direction)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Open", f"{last['open']:,.{price_decimals}f}")
            c2.metric("High", f"{last['high']:,.{price_decimals}f}")
            c3.metric("Low", f"{last['low']:,.{price_decimals}f}")
            c4.metric("Close", f"{last['close']:,.{price_decimals}f}")
            full_range = last["high"] - last["low"]
            if full_range > 0:
                body_pct = abs(last["close"] - last["open"]) / full_range
                st.caption(f"The body is {body_pct:.0%} of this candle's full high-low range.")

            with st.expander("Quick check"):
                guess = st.radio(
                    "If close is LOWER than open, is the candle bullish or bearish?",
                    ["Bullish", "Bearish"],
                    key=f"quiz_{lesson.id}",
                )
                if st.button("Check answer", key=f"quizbtn_{lesson.id}"):
                    if guess == "Bearish":
                        st.success("Correct — price fell over that candle, so it's bearish.")
                    else:
                        st.error("Not quite — close below open means price fell, which is bearish.")

        elif lesson.live_example == "support_resistance":
            joined = load_joined_frame(asset)
            row = joined.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric("Current price", f"{row['close']:,.{price_decimals}f}")
            c2.metric(
                "Trailing resistance (20-bar high)",
                f"{row['resistance']:,.{price_decimals}f}" if pd.notna(row["resistance"]) else "—",
            )
            c3.metric(
                "Trailing support (20-bar low)",
                f"{row['support']:,.{price_decimals}f}" if pd.notna(row["support"]) else "—",
            )
            st.caption(
                "These are trailing 20-candle extremes, not true swing-point detection — the "
                "documented MVP simplification this lesson mentioned above."
            )

        elif lesson.live_example == "risk_management":
            st.markdown("**Mini position-size calculator** — same formula as the Risk page:")
            c1, c2 = st.columns(2)
            equity = c1.number_input("Account equity ($)", min_value=0.0, value=10000.0, key="learn_equity")
            risk_pct = c2.number_input(
                "Risk per trade (%)", min_value=0.0, max_value=100.0, value=1.0, key="learn_risk_pct"
            )
            c3, c4 = st.columns(2)
            entry = c3.number_input("Entry price", min_value=0.0, value=100.0, key="learn_entry")
            stop = c4.number_input("Stop price", min_value=0.0, value=95.0, key="learn_stop")
            if entry != stop:
                size = position_size(equity, risk_pct, entry, stop)
                st.info(f"Position size: **{size:,.4f} units** (risking ${equity * risk_pct / 100:,.2f})")

            with st.expander("Quick check"):
                st.markdown(
                    "You have $10,000 and want to risk 1% on a trade with a $50-per-unit stop "
                    "distance. What's your position size?"
                )
                answer = st.number_input("Your answer (units)", min_value=0.0, key=f"quiz_{lesson.id}")
                if st.button("Check answer", key=f"quizbtn_{lesson.id}"):
                    correct = position_size(10000, 1.0, 100, 50)  # entry/stop values don't matter, only the distance
                    if abs(answer - correct) < 0.01:
                        st.success(f"Correct — {correct:.2f} units (risk $100 ÷ $50 stop distance = 2 units).")
                    else:
                        st.error(f"Not quite — it's {correct:.2f} units: risk amount ($100) ÷ stop distance ($50).")

        elif lesson.live_example == "fvg_supply_demand":
            joined = load_joined_frame(asset)
            row = joined.iloc[-1]
            zone = row.get("zone_direction")
            c1, c2, c3 = st.columns(3)
            c1.metric("Active zone right now", zone or "None")
            c2.metric("Zone has Fair Value Gap", "Yes" if row.get("zone_has_fvg") else "No")
            ema200 = row.get("ema200")
            if pd.isna(ema200):
                ema_position = "Unknown (not enough history yet)"
            else:
                ema_position = "Above" if row["close"] > ema200 else "Below"
            c3.metric("Price vs 200 EMA", ema_position)
            if zone:
                st.caption(
                    f"Zone range: {row['zone_low']:,.{price_decimals}f} – {row['zone_high']:,.{price_decimals}f}"
                )
            else:
                st.caption(f"No active demand/supply zone for {asset} right now — that's a normal state.")

            with st.expander("Quick check"):
                guess = st.radio(
                    "For a BULLISH Fair Value Gap across 3 candles, which must be true?",
                    [
                        "Candle 3's low is above candle 1's high",
                        "Candle 3's high is above candle 1's low",
                    ],
                    key=f"quiz_{lesson.id}",
                )
                if st.button("Check answer", key=f"quizbtn_{lesson.id}"):
                    if guess == "Candle 3's low is above candle 1's high":
                        st.success("Correct — that gap between them is the imbalance nobody's traded back through.")
                    else:
                        st.error("Not quite — it's candle 3's LOW vs. candle 1's HIGH that must leave a gap.")

        elif lesson.live_example == "trend_filters":
            joined = load_joined_frame(asset)
            row = joined.iloc[-1]
            ema200 = row.get("ema200")
            c1, c2, c3 = st.columns(3)
            if pd.isna(ema200):
                c1.metric("200 EMA", "Not enough history yet")
            else:
                c1.metric("200 EMA", f"{ema200:,.{price_decimals}f}")
                c2.metric("Price vs 200 EMA", "Above" if row["close"] > ema200 else "Below")
            c3.metric("SMA-based trend (20 vs 50)", row.get("trend", "UNKNOWN"))
            st.caption(
                "Two different trend reads, both live right now — structure/SMA-based (Lesson 1's "
                "engine) and the slower 200-EMA filter the bot setups require."
            )

        elif lesson.live_example == "orb":
            joined = load_orb_frame(asset)
            row = joined.iloc[-1]
            c1, c2 = st.columns(2)
            if pd.notna(row.get("orb_range_high")):
                c1.metric("Today's opening range", f"{row['orb_range_low']:,.{price_decimals}f} – {row['orb_range_high']:,.{price_decimals}f}")
            else:
                c1.metric("Today's opening range", "Not set yet")
            c2.metric("Today's breakout direction", row.get("orb_direction") or "None yet")
            st.caption(
                "The opening range is set once the 09:30-09:45 America/New_York candle closes each "
                "trading day — outside that window, or before it happens today, there's nothing to show yet."
            )

        else:  # signal_pipeline
            setup = st.selectbox(
                "Setup",
                ["Trend-Aligned Pullback", "Supply & Demand + FVG", "Opening Range Breakout"],
                key=f"setup_{lesson.id}",
            )
            if setup == "Trend-Aligned Pullback":
                joined = load_joined_frame(asset)
                analysis = build_analysis(asset, joined.iloc[-1], higher_tf="1D", intermediate_tf="4H")
                signal = generate_pullback_signal(asset, "1H", analysis)
            elif setup == "Supply & Demand + FVG":
                joined = load_joined_frame(asset)
                signal = generate_supply_demand_signal(
                    asset, "1H", joined.iloc[-1], higher_tf="1D", intermediate_tf="4H"
                )
            else:
                joined = load_orb_frame(asset)
                signal = generate_orb_signal(asset, "15m", joined.iloc[-1], higher_tf="4H", intermediate_tf="1H")

            if signal is None:
                st.info(
                    "**No qualifying setup right now** — step 4 in the pipeline above just failed "
                    "one or more rules. This is the most common output, not an error."
                )
            else:
                st.success(f"**{signal.direction} setup found** — confidence {signal.confidence_score:.0%}")
                st.markdown(f"- Entry zone: {signal.entry_zone[0]:,.{price_decimals}f} – {signal.entry_zone[1]:,.{price_decimals}f}")
                st.markdown(f"- Stop loss: {signal.stop_loss:,.{price_decimals}f}")
                st.markdown(f"- Risk:Reward: {signal.risk_reward_ratio:.2f}")
                st.markdown("**Reasons this fired:**")
                for reason in signal.reasons:
                    st.markdown(f"  - {reason}")

    except Exception as err:  # noqa: BLE001
        st.warning(f"Could not load live data for this example: {err}")
