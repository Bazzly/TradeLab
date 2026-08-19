import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from lib.economic_calendar.fmp import get_calendar

st.set_page_config(page_title="TradeLab — Calendar", page_icon="📅", layout="wide")

st.title("Economic Calendar")
st.caption(
    "Scheduled macro events, flagged by impact. High-impact windows are exactly when "
    "a technically clean setup can still get blown out by a headline — check here before sizing up."
)

if not os.environ.get("FMP_API_KEY"):
    st.warning(
        "`FMP_API_KEY` isn't set (see `.streamlit/secrets.toml.example`) — create a free "
        "[Financial Modeling Prep](https://financialmodelingprep.com) API key to see events here."
    )
    st.stop()

days_ahead = st.slider("Days ahead", min_value=1, max_value=14, value=7)
impact_filter = st.multiselect("Impact", ["HIGH", "MEDIUM", "LOW"], default=["HIGH", "MEDIUM"])

start = datetime.now()
end = start + timedelta(days=days_ahead)

try:
    events = get_calendar(start, end)
except Exception as err:  # noqa: BLE001
    st.error(f"Could not load economic calendar: {err}")
    st.stop()

filtered = [e for e in events if e.impact in impact_filter]
filtered.sort(key=lambda e: e.date)

if not filtered:
    st.caption("No matching events in this window.")
else:
    df = pd.DataFrame(
        [
            {
                "Date": e.date,
                "Country": e.country,
                "Event": e.event,
                "Impact": e.impact,
                "Actual": e.actual,
                "Forecast": e.forecast,
                "Previous": e.previous,
            }
            for e in filtered
        ]
    )
    st.dataframe(df, width="stretch")

    high_impact_soon = [e for e in filtered if e.impact == "HIGH" and e.date <= datetime.now() + timedelta(hours=24)]
    if high_impact_soon:
        st.warning(
            f"{len(high_impact_soon)} high-impact event(s) in the next 24 hours — "
            "consider this before opening new positions."
        )
