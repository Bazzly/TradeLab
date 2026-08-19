import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.data import load_candles
from lib.indicators import atr, rsi, sma
from lib.market_data.registry import ALL_ASSETS, FOREX_ASSETS, default_asset
from lib.schemas import Timeframe

st.set_page_config(page_title="TradeLab — Dashboard", page_icon="📊", layout="wide")

st.title("Market Dashboard")
st.caption(
    "MVP slice: live data + core indicators. Not a signal, not advice — "
    "just what the data shows."
)

ASSETS = ALL_ASSETS
TIMEFRAMES: list[Timeframe] = ["15m", "1H", "4H", "1D"]

col1, col2 = st.columns(2)
asset = col1.selectbox("Asset", ASSETS, index=ASSETS.index(default_asset()))
timeframe = col2.selectbox("Timeframe", TIMEFRAMES, index=1)


try:
    df = load_candles(asset, timeframe, days=30)
except Exception as err:  # noqa: BLE001 — surface any provider error to the user
    st.error(f"Could not load market data: {err}")
    st.stop()

if df.empty:
    st.warning("No candles returned for this asset/timeframe.")
    st.stop()

df["sma20"] = sma(df["close"], 20)
df["rsi14"] = rsi(df["close"], 14)
df["atr14"] = atr(df["high"], df["low"], df["close"], 14)

last = df.iloc[-1]
prev = df.iloc[-2] if len(df) > 1 else None
pct_change = ((last["close"] - prev["close"]) / prev["close"] * 100) if prev is not None else None
trend = None if pct_change is None else ("Up" if pct_change >= 0 else "Down")

# Forex majors trade in the 0.6-155 range with pip-level precision that
# matters (e.g. EUR/USD ~1.1607) — 2 decimals rounds real movement to 0.00
# for both price and ATR. Crypto's 2 decimals is fine at its price scale.
price_decimals = 5 if asset in FOREX_ASSETS else 2

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Price", f"{last['close']:,.{price_decimals}f}")
m2.metric(
    "Change (last candle)",
    f"{pct_change:.2f}%" if pct_change is not None else "—",
    delta=trend,
)
m3.metric("RSI (14)", f"{last['rsi14']:.1f}" if pd.notna(last["rsi14"]) else "—")
m4.metric("SMA (20)", f"{last['sma20']:.{price_decimals}f}" if pd.notna(last["sma20"]) else "—")
m5.metric("ATR (14)", f"{last['atr14']:.{price_decimals}f}" if pd.notna(last["atr14"]) else "—")

st.caption(
    "RSI: above 70 = overbought, below 30 = oversold — not a signal by itself. "
    "SMA: smoothed trend reference. ATR: typical recent movement per candle, useful for sizing stops."
)

fig = go.Figure(
    data=[
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=asset,
        ),
        go.Scatter(x=df["time"], y=df["sma20"], name="SMA 20", line=dict(width=1)),
    ]
)
fig.update_layout(height=500, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=20, b=0))
st.plotly_chart(fig, width="stretch")
