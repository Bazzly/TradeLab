"""Forex data via Twelve Data (README_forex.md Section 3.3, 11).

Replaces OANDA as the forex provider: OANDA is a regulated broker requiring
KYC/residency checks, and rejected signup outright for the user based on
country of residence ("OANDA cannot accept new clients from your country").
Twelve Data is a pure market-data API (no brokerage account, no KYC), so
that specific blocker doesn't apply. Not yet live-verified against a real,
self-registered free key — their shared "demo" key did return real EUR/USD
candles (a good sign), but demo-key behavior isn't proof of real free-tier
terms; treat this the same as any other "should work" claim here until
tested against an actual account.

lib/market_data/oanda.py is kept as-is for anyone in a country OANDA does
accept, or for the Section 9 item 1 paper-trading use case it also covers
(Twelve Data is data-only, not a broker, so it can't replace that role).
"""

from datetime import datetime

import requests

from lib.market_data.provider import Candle
from lib.schemas import Timeframe
from lib.secrets import get_secret

_INTERVAL_MAP: dict[Timeframe, str] = {
    "15m": "15min",
    "1H": "1h",
    "4H": "4h",
    "1D": "1day",
}

_BASE_URL = "https://api.twelvedata.com/time_series"

# Twelve Data returns at most 5000 values per request regardless of outputsize;
# page by requesting backward from `end_date` using `start_date`/`end_date`
# bounds so a wide window doesn't silently truncate (same bug class as
# Binance/OANDA — see README_forex.md Section 11).
_MAX_OUTPUT_SIZE = 5000


def is_configured() -> bool:
    return bool(get_secret("TWELVEDATA_API_KEY"))


class TwelveDataProvider:
    name = "twelvedata"

    def get_candles(
        self, asset: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        api_key = get_secret("TWELVEDATA_API_KEY")
        if not api_key:
            raise RuntimeError("TWELVEDATA_API_KEY is not set — see .streamlit/secrets.toml.example")

        res = requests.get(
            _BASE_URL,
            params={
                "symbol": asset,
                "interval": _INTERVAL_MAP[timeframe],
                "start_date": start.strftime("%Y-%m-%d %H:%M:%S"),
                "end_date": end.strftime("%Y-%m-%d %H:%M:%S"),
                "outputsize": _MAX_OUTPUT_SIZE,
                "order": "ASC",
                "apikey": api_key,
            },
            timeout=10,
        )
        res.raise_for_status()
        body = res.json()

        if body.get("status") == "error":
            raise RuntimeError(f"Twelve Data error: {body.get('message', body)}")

        values = body.get("values", [])
        return [
            Candle(
                time=datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M:%S"),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row.get("volume") or 0),
            )
            for row in values
        ]


twelvedata_provider = TwelveDataProvider()
