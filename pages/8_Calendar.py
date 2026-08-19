from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from lib.economic_calendar.static import get_calendar

st.set_page_config(page_title="TradeLab — Calendar", page_icon="📅", layout="wide")

st.title("Economic Calendar")
st.caption(
    "Scheduled macro events, flagged by impact. High-impact windows are exactly when "
    "a technically clean setup can still get blown out by a headline — check here before sizing up."
)
st.info(
    "No external API — this is a maintained list of the highest-impact recurring events "
    "(FOMC, ECB rate decisions, US jobs report) sourced from official calendars, not a "
    "full country-by-country feed. Notably **not included: CPI** — its release day isn't a "
    "fixed rule, and the source that would confirm exact dates blocks automated access. "
    "See `lib/economic_calendar/static.py` for sourcing and maintenance notes."
)

days_ahead = st.slider("Days ahead", min_value=1, max_value=180, value=30)

start = datetime.now()
end = start + timedelta(days=days_ahead)
events = get_calendar(start, end)

if not events:
    st.caption("No events in this window.")
else:
    df = pd.DataFrame(
        [{"Date": e.date.date(), "Country": e.country, "Event": e.event, "Impact": e.impact} for e in events]
    )
    st.dataframe(df, width="stretch")

    high_impact_soon = [e for e in events if e.impact == "HIGH" and e.date <= datetime.now() + timedelta(hours=24)]
    if high_impact_soon:
        st.warning(
            f"{len(high_impact_soon)} high-impact event(s) in the next 24 hours — "
            "consider this before opening new positions."
        )
