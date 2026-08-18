# TradeLab

Build spec and architecture decisions live in [README_forex.md](./README_forex.md) — read that first.

## Getting Started

1. `python3.12 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in credentials as you wire each up (see README_forex.md Section 3).
4. `streamlit run Home.py` — dashboard at [http://localhost:8501](http://localhost:8501)

Crypto market data (Binance) works with no credentials. Forex data (OANDA) requires `OANDA_API_KEY` from a free practice/demo account. Journal/auth features require a free [Neon](https://neon.tech) Postgres project.

## Deploying

Push to a GitHub repo, then deploy for free at [share.streamlit.io](https://share.streamlit.io), pointing it at `Home.py`. Add the same keys from `.streamlit/secrets.toml` under the app's Settings → Secrets.
