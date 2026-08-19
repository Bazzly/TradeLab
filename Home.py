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

    - **Dashboard** — live price, trend, and core indicators (MA, RSI, ATR),
      across crypto (works now) and the 5 major forex pairs — EUR/USD,
      USD/JPY, GBP/USD, USD/CHF, AUD/USD (needs a free [Twelve
      Data](https://twelvedata.com) API key; code-complete, not yet
      live-verified)
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
    - **Risk** — position sizing, open exposure, daily loss limits, and
      correlation checks against your actual open Journal positions
    - **Calendar** — FOMC, ECB, and US jobs report dates, no API key needed
      (a static maintained list, not a full country-by-country feed)
    - **Learning** — the beginner curriculum behind the engines above

    The Journal page also includes an **AI Trade Review** (needs a free
    Google Gemini API key) — it grades process, not outcome.

    See `README_forex.md` for the full build spec, architecture decisions,
    and the anti-hype rules that govern every feature in this app.
    """
)
