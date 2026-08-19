"""Shared, cached market-data loaders (README_forex.md Section 3.2's
"never duplicate fetch logic" rule, extended to caching too).

Every page was defining its own @st.cache_data-wrapped loader — since
Streamlit keys the cache by function identity, that meant visiting
Dashboard then Strategy Lab for the same asset triggered two independent
API calls for identical data, no cache sharing across pages at all. Routing
every page through these same two functions means the cache is now shared
across the whole session, which matters directly for staying under free-
tier rate limits (Twelve Data: 800 requests/day, 8/minute).

Uses `timezone.utc`, not the shorter `datetime.UTC` alias — that alias was
only added in Python 3.11, and Streamlit Community Cloud's deployed Python
version isn't guaranteed to be that new (confirmed live: it broke the
deployed app with an ImportError this exact alias caused). `timezone.utc`
has worked since Python 3.2 — don't "simplify" it back.
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from lib.engines.multi_timeframe import build_multi_timeframe_series
from lib.engines.orb import build_orb_frame
from lib.market_data.registry import get_provider
from lib.schemas import Timeframe


@st.cache_data(ttl=300)
def load_candles(asset: str, timeframe: Timeframe, days: int) -> pd.DataFrame:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    candles = get_provider(asset).get_candles(asset, timeframe, start, end)
    return pd.DataFrame([c.__dict__ for c in candles])


@st.cache_data(ttl=300)
def load_joined_frame(asset: str, days: int = 90) -> pd.DataFrame:
    df = load_candles(asset, "1H", days)
    return build_multi_timeframe_series(asset, df)


@st.cache_data(ttl=300)
def load_orb_frame(asset: str, days: int = 60) -> pd.DataFrame:
    """15m-based frame for the Opening Range Breakout setup (bot.md Section
    1.2) — a separate loader since it needs a different base timeframe than
    every other setup's 1H frame, not because it skips the shared cache."""
    df = load_candles(asset, "15m", days)
    return build_orb_frame(asset, df)
