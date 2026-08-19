import uuid
from datetime import date

import pandas as pd
import streamlit as st

from lib.db.connection import is_configured
from lib.db.journal import create_entry, delete_entry, list_entries, update_entry_exit
from lib.schemas import JournalEntry

st.set_page_config(page_title="TradeLab — Journal", page_icon="📓", layout="wide")

st.title("Trading Journal")
st.caption(
    "Manual trade entry. Grades process, not just outcome — every entry needs a reason "
    "before it needs a result."
)

# --- Identity -----------------------------------------------------------
# st.login()/st.user requires an OIDC provider configured in secrets
# (README_forex.md Section 3.1) — until that's wired up, fall back to a
# manually entered dev user id so the Journal itself is fully testable.
auth_configured = "auth" in st.secrets if hasattr(st, "secrets") else False

if auth_configured and st.user.is_logged_in:
    user_id = st.user.email
    st.sidebar.success(f"Logged in as {user_id}")
    if st.sidebar.button("Log out"):
        st.logout()
else:
    if not auth_configured:
        st.info(
            "Login isn't wired up yet (no OIDC provider in secrets — see "
            "`.streamlit/secrets.toml.example`). Using a manual dev user id for now; "
            "swap to `st.login()` once auth is configured."
        )
    user_id = st.sidebar.text_input("Dev user id (stand-in for login)", value="dev-user")
    if not user_id:
        st.stop()

if not is_configured():
    st.warning(
        "`DATABASE_URL` isn't set (see `.streamlit/secrets.toml.example`) — create a free "
        "[Neon](https://neon.tech) project and add its connection string to see the Journal "
        "actually persist entries. The form below will still validate, it just can't save yet."
    )

# --- New entry form -------------------------------------------------------
with st.expander("New journal entry", expanded=True):
    with st.form("new_entry"):
        c1, c2, c3 = st.columns(3)
        entry_date = c1.date_input("Date", value=date.today())
        asset = c2.text_input("Asset", value="BTC/USD")
        direction = c3.selectbox("Direction", ["LONG", "SHORT"])

        c4, c5, c6 = st.columns(3)
        entry_price = c4.number_input("Entry price", min_value=0.0, format="%.5f")
        stop_loss = c5.number_input("Stop loss", min_value=0.0, format="%.5f")
        take_profit = c6.number_input("Take profit", min_value=0.0, format="%.5f")

        c7, c8, c9 = st.columns(3)
        position_size = c7.number_input("Position size", min_value=0.0)
        risk_amount = c8.number_input("Risk amount ($)", min_value=0.0)
        timeframe = c9.selectbox("Timeframe", ["15m", "1H", "4H", "1D"], index=1)

        reason_for_entry = st.text_area("Reason for entry (required)")

        if entry_price and stop_loss and take_profit:
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            rr = reward / risk if risk > 0 else 0.0
            st.caption(f"Risk:Reward for this entry — **{rr:.2f}**")

        submitted = st.form_submit_button("Save entry")
        if submitted:
            if not reason_for_entry.strip():
                st.error("Reason for entry is required — no trade without a stated reason.")
            else:
                new_entry = JournalEntry(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    date=entry_date,
                    asset=asset,
                    direction=direction,
                    entry=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    position_size=position_size,
                    risk_amount=risk_amount,
                    timeframe=timeframe,
                    reason_for_entry=reason_for_entry,
                    result="OPEN",
                )
                try:
                    create_entry(user_id, new_entry)
                    st.success("Entry saved.")
                    st.cache_data.clear()
                except Exception as err:  # noqa: BLE001
                    st.error(f"Could not save entry: {err}")

# --- Existing entries -----------------------------------------------------
st.subheader("History")

entries = []
if is_configured():
    try:
        entries = list_entries(user_id)
    except Exception as err:  # noqa: BLE001
        st.error(f"Could not load journal entries: {err}")

if not entries:
    st.caption("No entries yet.")
else:
    df = pd.DataFrame(
        [
            {
                "Date": e.date,
                "Asset": e.asset,
                "Direction": e.direction,
                "Entry": e.entry,
                "Stop": e.stop_loss,
                "Target": e.take_profit,
                "Result": e.result,
                "R": e.r_multiple,
                "Reason": e.reason_for_entry,
            }
            for e in entries
        ]
    )
    st.dataframe(df, width="stretch")

    open_entries = [e for e in entries if e.result == "OPEN"]
    if open_entries:
        st.subheader("Close a trade")
        labels = [f"{e.date} {e.asset} {e.direction} @ {e.entry}" for e in open_entries]
        idx = st.selectbox("Open trade", range(len(labels)), format_func=lambda i: labels[i])
        target_entry = open_entries[idx]

        with st.form("close_trade"):
            result = st.selectbox("Result", ["WIN", "LOSS", "BREAKEVEN"])
            reason_for_exit = st.text_area("Reason for exit (required)")
            r_multiple = st.number_input("R multiple", step=0.1)
            lessons_learned = st.text_area("Lessons learned (optional)")

            if st.form_submit_button("Save exit"):
                if not reason_for_exit.strip():
                    st.error("Reason for exit is required.")
                else:
                    try:
                        update_entry_exit(
                            user_id,
                            target_entry.id,
                            reason_for_exit,
                            result,
                            r_multiple,
                            lessons_learned or None,
                        )
                        st.success("Trade closed.")
                        st.cache_data.clear()
                    except Exception as err:  # noqa: BLE001
                        st.error(f"Could not close trade: {err}")
