from datetime import date

import pandas as pd
import streamlit as st

from lib.auth import get_user_id
from lib.data import load_candles
from lib.db.connection import is_configured
from lib.db.journal import list_entries
from lib.db.settings import UserSettings, get_settings, save_settings
from lib.engines.risk import (
    correlation_matrix,
    correlation_warnings,
    daily_loss_check,
    open_risk_summary,
    position_size,
)
from lib.market_data.registry import ALL_ASSETS

st.set_page_config(page_title="TradeLab — Risk", page_icon="🛡️", layout="wide")

st.title("Risk Management")
st.caption(
    "Position sizing, open exposure, daily loss limits, and correlation checks — "
    "the rules that exist to stop you chasing an entry past your own risk plan."
)

user_id = get_user_id()
if not user_id:
    st.stop()

if not is_configured():
    st.warning(
        "`DATABASE_URL` isn't set — settings and open-risk exposure need a Neon database "
        "(see `.streamlit/secrets.toml.example`). The position size calculator below still works."
    )
    settings = UserSettings(account_equity=10000.0, risk_pct_per_trade=1.0, daily_loss_limit_pct=3.0)
else:
    settings = get_settings(user_id)

# --- Settings -------------------------------------------------------------
with st.expander("Risk settings", expanded=not is_configured()):
    with st.form("risk_settings"):
        c1, c2, c3 = st.columns(3)
        account_equity = c1.number_input("Account equity ($)", min_value=0.0, value=settings.account_equity)
        risk_pct = c2.number_input(
            "Risk per trade (%)", min_value=0.0, max_value=100.0, value=settings.risk_pct_per_trade
        )
        daily_loss_limit_pct = c3.number_input(
            "Daily loss limit (%)", min_value=0.0, max_value=100.0, value=settings.daily_loss_limit_pct
        )
        if st.form_submit_button("Save settings") and is_configured():
            save_settings(user_id, UserSettings(account_equity, risk_pct, daily_loss_limit_pct))
            st.success("Saved.")

# --- Position size calculator ----------------------------------------------
st.subheader("Position Size Calculator")
c1, c2 = st.columns(2)
entry_price = c1.number_input("Entry price", min_value=0.0, format="%.5f", key="calc_entry")
stop_price = c2.number_input("Stop price", min_value=0.0, format="%.5f", key="calc_stop")
if entry_price and stop_price and entry_price != stop_price:
    size = position_size(account_equity, risk_pct, entry_price, stop_price)
    risk_dollars = account_equity * (risk_pct / 100)
    st.info(
        f"Risking **${risk_dollars:,.2f}** ({risk_pct:.1f}% of ${account_equity:,.0f}) with a "
        f"{abs(entry_price - stop_price):.5f} stop distance → position size **{size:,.4f} units**."
    )

st.divider()

# --- Open exposure + daily loss --------------------------------------------
if is_configured():
    try:
        entries = list_entries(user_id)
    except Exception as err:  # noqa: BLE001
        st.error(f"Could not load journal entries: {err}")
        entries = []

    st.subheader("Open Risk Exposure")
    exposure = open_risk_summary(entries, account_equity)
    e1, e2, e3 = st.columns(3)
    e1.metric("Open trades", exposure.open_trade_count)
    e2.metric("Total open risk", f"${exposure.total_risk_amount:,.2f}")
    e3.metric("% of equity at risk", f"{exposure.pct_of_equity:.1f}%")
    if exposure.by_asset:
        st.caption(
            "By asset: " + ", ".join(f"{a} (${r:,.0f})" for a, r in exposure.by_asset.items())
        )

    st.subheader("Daily Loss Limit")
    loss = daily_loss_check(entries, account_equity, daily_loss_limit_pct, today=date.today())
    l1, l2 = st.columns(2)
    l1.metric("Realized today", f"${loss.realized_amount:,.2f}", delta=f"{loss.pct_of_equity:.1f}% of equity")
    if loss.limit_breached:
        l2.error(f"Daily loss limit ({daily_loss_limit_pct:.1f}%) breached — stop trading for today.")
    else:
        l2.success("Within daily loss limit.")

    st.divider()

    # --- Correlation check ---------------------------------------------------
    st.subheader("Correlation Check")
    open_assets = list(exposure.by_asset.keys())
    watchlist = ALL_ASSETS

    def load_return_frames(assets: tuple[str, ...]) -> dict[str, pd.DataFrame]:
        # load_candles is cached in lib/data.py and shared with Dashboard's
        # 1H view — same (asset, "1H", 30 days) key, so a Dashboard visit
        # can save this page a fetch too.
        frames = {}
        for asset in assets:
            try:
                frames[asset] = load_candles(asset, "1H", days=30)
            except Exception:  # noqa: BLE001
                continue
        return frames

    frames = load_return_frames(tuple(watchlist))
    corr = correlation_matrix(frames)

    if not corr.empty:
        st.dataframe(corr.round(2), width="stretch")

        if open_assets:
            candidate = st.selectbox("Check a new candidate asset against your open positions", watchlist)
            warnings = correlation_warnings(open_assets, candidate, corr, threshold=0.7)
            if warnings:
                for w in warnings:
                    st.warning(w)
            else:
                st.success(f"No high correlation (≥0.7) between {candidate} and your open positions.")
    else:
        st.caption("Not enough data to compute correlations right now.")
else:
    st.caption("Open exposure, daily loss tracking, and correlation checks need a Neon database.")
