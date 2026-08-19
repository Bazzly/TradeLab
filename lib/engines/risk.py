"""Risk Management Engine (README_forex.md Section 4.6).

Position sizing, open-risk exposure, daily loss limits, and correlation
checks — the checks that are supposed to stop a user from chasing an entry
past what their own risk rules allow (Section 1.5, Section 2).
"""

from dataclasses import dataclass
from datetime import date

import pandas as pd

from lib.schemas import JournalEntry


def position_size(account_equity: float, risk_pct: float, entry: float, stop: float) -> float:
    """Units to buy/sell so that a stop-out risks exactly `risk_pct` of equity."""
    risk_amount = account_equity * (risk_pct / 100)
    per_unit_risk = abs(entry - stop)
    if per_unit_risk <= 0:
        return 0.0
    return risk_amount / per_unit_risk


@dataclass
class OpenRiskSummary:
    open_trade_count: int
    total_risk_amount: float
    pct_of_equity: float
    by_asset: dict[str, float]


def open_risk_summary(entries: list[JournalEntry], account_equity: float) -> OpenRiskSummary:
    open_entries = [e for e in entries if e.result == "OPEN"]
    total_risk = sum(e.risk_amount for e in open_entries)
    by_asset: dict[str, float] = {}
    for e in open_entries:
        by_asset[e.asset] = by_asset.get(e.asset, 0.0) + e.risk_amount

    return OpenRiskSummary(
        open_trade_count=len(open_entries),
        total_risk_amount=total_risk,
        pct_of_equity=(total_risk / account_equity * 100) if account_equity > 0 else 0.0,
        by_asset=by_asset,
    )


@dataclass
class LossLimitCheck:
    realized_amount: float  # negative = net loss
    pct_of_equity: float
    limit_breached: bool


def _realized_pnl(entries: list[JournalEntry], since: date) -> float:
    closed = [e for e in entries if e.result in ("WIN", "LOSS", "BREAKEVEN") and e.date >= since]
    total = 0.0
    for e in closed:
        if e.r_multiple is not None:
            total += e.r_multiple * e.risk_amount
    return total


def daily_loss_check(
    entries: list[JournalEntry], account_equity: float, daily_loss_limit_pct: float, today: date
) -> LossLimitCheck:
    realized = _realized_pnl(entries, since=today)
    pct = (realized / account_equity * 100) if account_equity > 0 else 0.0
    return LossLimitCheck(
        realized_amount=realized,
        pct_of_equity=pct,
        limit_breached=pct <= -abs(daily_loss_limit_pct),
    )


def correlation_matrix(candles_by_asset: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Pairwise correlation of hourly returns across the watchlist. Assets
    with too little overlapping history are simply excluded from the result
    rather than producing a misleading value.
    """
    returns = {}
    for asset, df in candles_by_asset.items():
        if len(df) < 2:
            continue
        returns[asset] = df.set_index("time")["close"].pct_change().dropna()

    if len(returns) < 2:
        return pd.DataFrame()

    aligned = pd.DataFrame(returns)
    return aligned.corr()


def correlation_warnings(
    open_assets: list[str], candidate_asset: str, corr: pd.DataFrame, threshold: float = 0.7
) -> list[str]:
    """Warn if `candidate_asset` is highly correlated with an already-open
    position — stacking correlated risk isn't diversification, even if it
    looks like separate trades."""
    warnings = []
    if candidate_asset not in corr.columns:
        return warnings
    for asset in open_assets:
        if asset == candidate_asset or asset not in corr.columns:
            continue
        value = corr.loc[candidate_asset, asset]
        if pd.notna(value) and abs(value) >= threshold:
            direction = "positively" if value > 0 else "negatively"
            warnings.append(
                f"{candidate_asset} is {direction} correlated with your open {asset} position "
                f"(r={value:.2f}) — this adds concentrated risk, not diversification."
            )
    return warnings
