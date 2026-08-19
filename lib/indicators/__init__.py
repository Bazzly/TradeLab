import pandas as pd


def sma(close: pd.Series, period: int) -> pd.Series:
    """Simple moving average of closes over `period` candles."""
    return close.rolling(window=period).mean()


def ema(close: pd.Series, period: int) -> pd.Series:
    """Exponential moving average of closes over `period` candles."""
    return close.ewm(span=period, min_periods=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI over `period` candles (default 14)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    result = 100 - (100 / (1 + rs))
    return result.where(avg_loss != 0, 100)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range over `period` candles (default 14)."""
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.rolling(window=period).mean()
