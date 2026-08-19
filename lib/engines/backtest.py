"""Basic Backtesting Engine (README_forex.md Section 4.5, 5.3, 9 item 5).

Walks the same joined, indicator-enriched frame the live dashboard uses
(`lib.engines.multi_timeframe.build_multi_timeframe_series`) bar by bar,
generating signals with `lib.engines.signal.generate_signal` exactly as the
live engine would, then simulates whether each signal's entry zone gets
touched and how the resulting trade resolves. No column here is computed
with knowledge of future bars (see multi_timeframe.py's module docstring).
"""

import statistics
from dataclasses import dataclass
from typing import Callable

import pandas as pd

from lib.engines.multi_timeframe import build_analysis
from lib.engines.signal import SETUP_TYPE, generate_signal
from lib.schemas import StrategyPerformanceReport, Timeframe, TradingSignal

ENTRY_EXPIRY_BARS = 20  # signal considered stale if the entry zone isn't touched within this many bars
MAX_HOLDING_BARS = 100  # forced timeout exit if neither stop nor target is hit

# A signal function takes (asset, timeframe, row) and returns a TradingSignal
# or None — this is the seam that lets a second setup type (e.g.
# lib.engines.signal_supply_demand) reuse this exact simulation/stats engine
# instead of duplicating it. Defaults to the original pullback setup.
SignalFn = Callable[[str, Timeframe, pd.Series], TradingSignal | None]


def _pullback_signal_fn(higher_tf: str, intermediate_tf: str) -> SignalFn:
    def fn(asset: str, timeframe: Timeframe, row: pd.Series) -> TradingSignal | None:
        analysis = build_analysis(asset, row, higher_tf, intermediate_tf)
        return generate_signal(asset, timeframe, analysis)

    return fn


@dataclass
class SimulatedTrade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: str
    entry_price: float
    exit_price: float
    exit_reason: str  # "TARGET" | "STOP" | "TIMEOUT"
    r_multiple: float


def _simulate_trades(
    asset: str, joined: pd.DataFrame, timeframe: Timeframe, signal_fn: SignalFn
) -> list[SimulatedTrade]:
    trades: list[SimulatedTrade] = []
    state = "SCANNING"
    pending = None  # (signal, since_idx)
    open_trade = None  # dict

    for i in range(len(joined)):
        row = joined.iloc[i]

        if state == "SCANNING":
            signal = signal_fn(asset, timeframe, row)
            if signal is not None:
                pending = (signal, i)
                state = "WAITING_ENTRY"

        elif state == "WAITING_ENTRY":
            signal, since_idx = pending
            if i - since_idx > ENTRY_EXPIRY_BARS:
                pending = None
                state = "SCANNING"
                continue

            zone_lo, zone_hi = signal.entry_zone
            touched = row["low"] <= zone_hi and row["high"] >= zone_lo
            if touched:
                open_trade = {
                    "entry_time": row["time"],
                    "entry_idx": i,
                    "direction": signal.direction,
                    "entry_price": (zone_lo + zone_hi) / 2,
                    "stop": signal.stop_loss,
                    "target": signal.take_profit_levels[0],
                }
                pending = None
                state = "IN_TRADE"

        elif state == "IN_TRADE":
            direction = open_trade["direction"]
            hit_stop = (
                row["low"] <= open_trade["stop"]
                if direction == "LONG"
                else row["high"] >= open_trade["stop"]
            )
            hit_target = (
                row["high"] >= open_trade["target"]
                if direction == "LONG"
                else row["low"] <= open_trade["target"]
            )

            exit_reason = None
            exit_price = None
            if hit_stop:
                # Conservative: if both stop and target are inside the same
                # bar's range, assume the stop was hit first — we don't have
                # intrabar tick data to know the true order.
                exit_reason, exit_price = "STOP", open_trade["stop"]
            elif hit_target:
                exit_reason, exit_price = "TARGET", open_trade["target"]
            elif i - open_trade["entry_idx"] >= MAX_HOLDING_BARS:
                exit_reason, exit_price = "TIMEOUT", row["close"]

            if exit_reason:
                risk = abs(open_trade["entry_price"] - open_trade["stop"])
                pnl = (
                    exit_price - open_trade["entry_price"]
                    if direction == "LONG"
                    else open_trade["entry_price"] - exit_price
                )
                trades.append(
                    SimulatedTrade(
                        entry_time=open_trade["entry_time"],
                        exit_time=row["time"],
                        direction=direction,
                        entry_price=open_trade["entry_price"],
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        r_multiple=(pnl / risk) if risk > 0 else 0.0,
                    )
                )
                open_trade = None
                state = "SCANNING"

    return trades


def _max_drawdown(r_multiples: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in r_multiples:
        equity += r
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
    return max_dd


def _longest_streak(results: list[bool]) -> int:
    longest = current = 0
    for is_match in results:
        current = current + 1 if is_match else 0
        longest = max(longest, current)
    return longest


def run_backtest(
    asset: str,
    joined: pd.DataFrame,
    timeframe: Timeframe,
    higher_tf: str = "1D",
    intermediate_tf: str = "4H",
    signal_fn: SignalFn | None = None,
    setup_type: str = SETUP_TYPE,
) -> StrategyPerformanceReport:
    trades = _simulate_trades(
        asset, joined, timeframe, signal_fn or _pullback_signal_fn(higher_tf, intermediate_tf)
    )

    sample_size = len(trades)
    r_multiples = [t.r_multiple for t in trades]
    wins = [r for r in r_multiples if r > 0]
    losses = [r for r in r_multiples if r <= 0]

    win_rate = len(wins) / sample_size if sample_size else 0.0
    loss_rate = len(losses) / sample_size if sample_size else 0.0
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    expectancy = statistics.fmean(r_multiples) if r_multiples else 0.0
    avg_win = statistics.fmean(wins) if wins else 0.0
    avg_loss = statistics.fmean(losses) if losses else 0.0
    max_drawdown = _max_drawdown(r_multiples)
    sharpe = (
        statistics.fmean(r_multiples) / statistics.pstdev(r_multiples)
        if len(r_multiples) > 1 and statistics.pstdev(r_multiples) > 0
        else 0.0
    )
    consecutive_wins = _longest_streak([r > 0 for r in r_multiples])
    consecutive_losses = _longest_streak([r <= 0 for r in r_multiples])

    monthly: dict[str, float] = {}
    for t in trades:
        key = t.exit_time.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0.0) + t.r_multiple
    monthly_performance = [{"month": m, "pnl": pnl} for m, pnl in sorted(monthly.items())]

    # Cumulative R after each closed trade, in exit order — trades are already
    # appended to `trades` in the order the simulation resolved them, so no
    # re-sort is needed. Starts implicitly at 0 (not stored) — the first
    # value here is the running total *after* the first trade.
    running = 0.0
    equity_curve = []
    for r in r_multiples:
        running += r
        equity_curve.append(running)

    date_range = (
        (joined["time"].iloc[0].date(), joined["time"].iloc[-1].date())
        if len(joined)
        else (None, None)
    )
    days_covered = (date_range[1] - date_range[0]).days if date_range[0] else 0
    annualized_performance = expectancy * (365 / days_covered) * sample_size if days_covered else 0.0

    overfitting_flags = []
    if sample_size < 30:
        overfitting_flags.append(
            f"Sample size ({sample_size}) is below the ~30-trade floor for any statistical reliability."
        )
    if sample_size < 100:
        overfitting_flags.append(
            "Below README_forex.md's suggested >=100-trade threshold for treating results as more than preliminary."
        )

    limitations = (
        f"Single-asset ({asset}), single setup type ({setup_type}), backtest over {days_covered} days "
        f"producing {sample_size} trades. No transaction costs, spread, or slippage modeled. "
        "Support/resistance is a trailing rolling-extreme proxy, not true swing-point detection. "
        "When a stop and target both fall inside the same bar's range, the stop is conservatively assumed "
        "hit first (no intrabar tick data available to confirm order). Not walk-forward tested; not "
        "evaluated out-of-sample. Indicator/lookback parameters are fixed defaults, not optimized against "
        "this data — but also not validated across other assets or market regimes. Treat all results as "
        "preliminary until sample size and out-of-sample testing requirements (README_forex.md Section 2) are met."
    )

    return StrategyPerformanceReport(
        strategy_id=setup_type,
        sample_size=sample_size,
        date_range=date_range,
        win_rate=win_rate,
        loss_rate=loss_rate,
        profit_factor=profit_factor,
        expectancy=expectancy,
        avg_win=avg_win,
        avg_loss=avg_loss,
        max_drawdown=max_drawdown,
        sharpe_ratio=sharpe,
        consecutive_wins=consecutive_wins,
        consecutive_losses=consecutive_losses,
        monthly_performance=monthly_performance,
        equity_curve=equity_curve,
        annualized_performance=annualized_performance,
        out_of_sample=False,
        walk_forward_tested=False,
        overfitting_flags=overfitting_flags,
        limitations=limitations,
    )
