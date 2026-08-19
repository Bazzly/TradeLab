from datetime import datetime, timedelta

import requests

from lib.market_data.provider import Candle
from lib.schemas import Timeframe

_GRANULARITY_SECONDS: dict[Timeframe, int] = {
    "15m": 900,
    "1H": 3600,
    "4H": 21600,
    "1D": 86400,
}

# Coinbase Exchange's public market-data endpoints (candles/ticker) require
# no API key and, unlike Binance.com, aren't geo-blocked for US-hosted
# traffic (e.g. Streamlit Community Cloud) — see README_forex.md Section 3.3.
_BASE_URL = "https://api.exchange.coinbase.com"
_MAX_CANDLES_PER_REQUEST = 300


class CoinbaseProvider:
    name = "coinbase"

    def get_candles(
        self, asset: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        product_id = asset.replace("/", "-")
        granularity = _GRANULARITY_SECONDS[timeframe]
        window = timedelta(seconds=granularity * _MAX_CANDLES_PER_REQUEST)

        candles: list[Candle] = []
        cursor = start
        while cursor < end:
            chunk_end = min(cursor + window, end)
            res = requests.get(
                f"{_BASE_URL}/products/{product_id}/candles",
                params={
                    "start": cursor.isoformat(),
                    "end": chunk_end.isoformat(),
                    "granularity": granularity,
                },
                headers={"User-Agent": "TradeLab/1.0"},
                timeout=10,
            )
            res.raise_for_status()
            rows = res.json()  # each row: [time, low, high, open, close, volume]

            candles.extend(
                Candle(
                    time=datetime.fromtimestamp(row[0]),
                    open=float(row[3]),
                    high=float(row[2]),
                    low=float(row[1]),
                    close=float(row[4]),
                    volume=float(row[5]),
                )
                for row in rows
            )

            cursor = chunk_end

        candles.sort(key=lambda c: c.time)
        return candles


coinbase_provider = CoinbaseProvider()
