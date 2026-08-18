from datetime import datetime

import requests

from lib.market_data.provider import Candle
from lib.schemas import Timeframe

_INTERVAL_MAP: dict[Timeframe, str] = {
    "15m": "15m",
    "1H": "1h",
    "4H": "4h",
    "1D": "1d",
}

# Public klines endpoint; no API key required for market data.
_BASE_URL = "https://api.binance.com/api/v3/klines"


class BinanceProvider:
    name = "binance"

    def get_candles(
        self, asset: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        params = {
            "symbol": asset.replace("/", ""),
            "interval": _INTERVAL_MAP[timeframe],
            "startTime": int(start.timestamp() * 1000),
            "endTime": int(end.timestamp() * 1000),
            "limit": 1000,
        }
        res = requests.get(_BASE_URL, params=params, timeout=10)
        res.raise_for_status()

        return [
            Candle(
                time=datetime.fromtimestamp(row[0] / 1000),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
            for row in res.json()
        ]


binance_provider = BinanceProvider()
