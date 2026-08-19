"""Routes an asset symbol to the provider that actually serves it
(README_forex.md Section 3.2's MarketDataProvider abstraction) so pages can
mix forex and crypto in one watchlist without knowing which vendor backs
which asset.
"""

from lib.market_data import twelvedata as twelvedata_module
from lib.market_data.coinbase import coinbase_provider
from lib.market_data.provider import MarketDataProvider

# The five majors: the most liquid, tightest-spread forex pairs, which is
# exactly why they're the standard beginner starting point (README_forex.md
# Section 9's "Learning" module covers why spread/liquidity matter).
FOREX_ASSETS = ["EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF", "AUD/USD"]

CRYPTO_ASSETS = ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "ADA/USD", "DOGE/USD", "LTC/USD", "LINK/USD"]

ALL_ASSETS = FOREX_ASSETS + CRYPTO_ASSETS


def get_provider(asset: str) -> MarketDataProvider:
    # Twelve Data is the default forex provider — OANDA (lib/market_data/
    # oanda.py) is broker-KYC-gated and rejects signups from some countries,
    # confirmed live by the user (README_forex.md Section 11). Kept for
    # anyone OANDA does accept, or for its future paper-trading broker role.
    return twelvedata_module.twelvedata_provider if asset in FOREX_ASSETS else coinbase_provider


def default_asset() -> str:
    """Crypto needs no API key and always works; forex needs
    TWELVEDATA_API_KEY. Defaulting a selectbox to a forex pair before that's
    configured would make every page's default view an error state — pick
    whichever asset class is actually usable right now."""
    return FOREX_ASSETS[0] if twelvedata_module.is_configured() else CRYPTO_ASSETS[0]
