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
    - More pages (Strategy Lab, Backtesting, Journal, Learning) ship per the
      phased roadmap in `README_forex.md`

    See `README_forex.md` for the full build spec, architecture decisions,
    and the anti-hype rules that govern every feature in this app.
    """
)
