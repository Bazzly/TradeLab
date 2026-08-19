from datetime import datetime

import requests

from lib.market_data.provider import Candle, epoch_to_utc_naive
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
        """Binance's klines endpoint caps each response at 1000 candles and,
        when a (startTime, endTime) window spans more than that, returns the
        OLDEST 1000 rather than the most recent — so a wide window silently
        truncates to its earliest slice unless we page forward in 1000-candle
        batches until `end` is reached.
        """
        symbol = asset.replace("/", "")
        interval = _INTERVAL_MAP[timeframe]
        cursor = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)

        candles: list[Candle] = []
        while cursor < end_ms:
            res = requests.get(
                _BASE_URL,
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": 1000,
                },
                timeout=10,
            )
            res.raise_for_status()
            rows = res.json()
            if not rows:
                break

            candles.extend(
                Candle(
                    time=epoch_to_utc_naive(row[0] / 1000),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                )
                for row in rows
            )

            last_open_ms = rows[-1][0]
            if last_open_ms <= cursor:  # safety: avoid an infinite loop
                break
            cursor = last_open_ms + 1

        return candles


binance_provider = BinanceProvider()
