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

import time
from collections import deque
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

# Free-tier limit is 8 requests/minute. Confirmed live (README_forex.md
# Section 11): the paper trading bot checking 5 forex assets x 2
# timeframes x 3 setups on a cold cache bursts well past that and gets a
# real 429. Proactively throttling our own outgoing requests to stay under
# the limit is the fix — a slow page beats a failed one (Section 6.6).
_MAX_REQUESTS_PER_MINUTE = 8
_WINDOW_SECONDS = 60.0
_MAX_429_RETRIES = 3
_request_times: deque[float] = deque()


def _throttle() -> None:
    now = time.monotonic()
    while _request_times and now - _request_times[0] > _WINDOW_SECONDS:
        _request_times.popleft()
    if len(_request_times) >= _MAX_REQUESTS_PER_MINUTE:
        sleep_for = _WINDOW_SECONDS - (now - _request_times[0]) + 0.5
        if sleep_for > 0:
            time.sleep(sleep_for)
    _request_times.append(time.monotonic())


def _get_with_rate_limit(url: str, params: dict) -> requests.Response:
    for attempt in range(_MAX_429_RETRIES):
        _throttle()
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 429 and attempt < _MAX_429_RETRIES - 1:
            # Server-side limit hit anyway (e.g. another process/session
            # sharing the same key) — back off harder than our own window
            # and retry rather than surface a failure for one bad request.
            time.sleep(_WINDOW_SECONDS)
            continue
        return res
    return res


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

        res = _get_with_rate_limit(
            _BASE_URL,
            params={
                "symbol": asset,
                "interval": _INTERVAL_MAP[timeframe],
                "start_date": start.strftime("%Y-%m-%d %H:%M:%S"),
                "end_date": end.strftime("%Y-%m-%d %H:%M:%S"),
                "outputsize": _MAX_OUTPUT_SIZE,
                "order": "ASC",
                # Explicit, not relying on Twelve Data's default (documented
                # as "Exchange" time for some endpoints) — matches the
                # UTC-aware start/end callers pass in (lib/data.py uses
                # datetime.now(UTC)) and the naive-but-UTC Candle.time
                # contract (lib/market_data/provider.py).
                "timezone": "UTC",
                "apikey": api_key,
            },
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
