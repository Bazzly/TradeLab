# TradeLab

Live at **[tradelab.streamlit.app](https://tradelab.streamlit.app/)**.

Build spec and architecture decisions live in [README_forex.md](./README_forex.md) — read that first.

## Getting Started

1. `python3.12 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in credentials as you wire each up (see README_forex.md Section 3).
4. `streamlit run Home.py` — dashboard at [http://localhost:8501](http://localhost:8501)

Crypto market data (Binance) works with no credentials. Forex data (OANDA) requires `OANDA_API_KEY` from a free practice/demo account. Journal/auth features require a free [Neon](https://neon.tech) Postgres project.

## Deploying

Deployed via [share.streamlit.io](https://share.streamlit.io) at [tradelab.streamlit.app](https://tradelab.streamlit.app/), pointing at `Home.py`. Secrets are pasted into the app's Settings → Secrets (same keys as `.streamlit/secrets.toml`, but with the deployed `redirect_uri` — see the comment in `.streamlit/secrets.toml.example`).
