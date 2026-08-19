import streamlit as st

st.set_page_config(page_title="TradeLab", page_icon="📊", layout="wide")

st.title("TradeLab")
st.caption(
    "A personal, rules-based trading research and education platform. "
    "Not a signal-selling service — every number here must be traceable to a rule."
)

st.markdown(
    """
    Use the sidebar to navigate:

    - **Dashboard** — live price, trend, and core indicators (MA, RSI, ATR)
    - **Strategy Lab** — the current multi-timeframe read and whether a
      rules-based setup qualifies right now ("no qualifying setup" is a
      normal outcome, not an error)
    - **Backtesting** — historical performance of that same setup, with
      sample size and limitations shown up front
    - **Journal** — manual trade logging with a required reason for every
      entry and exit (needs a free [Neon](https://neon.tech) database to
      persist — works without one, it just can't save yet)
    - **Scanner** — the Signal Engine run across a watchlist, ranked into
      four fixed tiers (an empty High-Quality tier is normal, not an error)
    - **Learning** — the beginner curriculum behind the engines above

    See `README_forex.md` for the full build spec, architecture decisions,
    and the anti-hype rules that govern every feature in this app.
    """
)
