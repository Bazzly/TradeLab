from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

ConfirmationLevel = Literal["STRONG", "MODERATE", "WEAK", "CONFLICTING", "NO_TRADE"]
Direction = Literal["LONG", "SHORT"]
Timeframe = Literal["15m", "1H", "4H", "1D"]
ScannerTier = Literal["HIGH_QUALITY_SETUPS", "WATCHLIST", "WEAK_SETUPS", "NO_TRADE"]
SubscriptionStatus = Literal["free", "active", "past_due", "canceled"]


@dataclass
class MultiTimeframeAnalysis:
    asset: str
    timestamp: datetime
    higher_timeframe_trend: str
    intermediate_trend: str
    lower_timeframe_structure: str
    key_support_resistance: list[float]
    momentum: str
    volatility: str
    possible_entry_zones: list[tuple[float, float]]
    invalidation_levels: list[float]
    targets: list[float]
    risk_reward_ratio: float
    confirmation_level: ConfirmationLevel
    conflicting_signals: list[str] = field(default_factory=list)


@dataclass
class TradingSignal:
    """No signal object is created unless predefined criteria are met."""

    id: str
    asset: str
    direction: Direction
    timeframe: Timeframe
    setup_type: str
    entry_zone: tuple[float, float]
    stop_loss: float
    take_profit_levels: list[float]
    risk_reward_ratio: float
    confirmation_factors: list[str]
    invalidating_conditions: list[str]
    confidence_score: float
    reasons: list[str]
    market_conditions: str
    timestamp: datetime


@dataclass
class StrategyPerformanceReport:
    """`limitations` is required and non-empty — never render a report without it."""

    strategy_id: str
    sample_size: int
    date_range: tuple[date, date]
    win_rate: float
    loss_rate: float
    profit_factor: float
    expectancy: float
    avg_win: float
    avg_loss: float
    max_drawdown: float
    sharpe_ratio: float
    consecutive_wins: int
    consecutive_losses: int
    monthly_performance: list[dict]
    equity_curve: list[float]
    annualized_performance: float
    out_of_sample: bool
    walk_forward_tested: bool
    overfitting_flags: list[str]
    limitations: str

    def __post_init__(self) -> None:
        if not self.limitations.strip():
            raise ValueError("StrategyPerformanceReport.limitations must be non-empty")


@dataclass
class JournalEntry:
    id: str
    user_id: str
    date: date
    asset: str
    direction: Direction
    entry: float
    stop_loss: float
    take_profit: float
    position_size: float
    risk_amount: float
    timeframe: Timeframe
    reason_for_entry: str
    strategy_id: str | None = None
    chart_screenshot_url: str | None = None
    reason_for_exit: str | None = None
    result: Literal["WIN", "LOSS", "BREAKEVEN", "OPEN"] | None = None
    r_multiple: float | None = None
    mistakes: list[str] = field(default_factory=list)
    emotional_state: str | None = None
    lessons_learned: str | None = None


@dataclass
class Subscription:
    user_id: str
    stripe_customer_id: str
    status: SubscriptionStatus
    stripe_subscription_id: str | None = None
    price_id: str | None = None
    current_period_end: datetime | None = None


EventImpact = Literal["LOW", "MEDIUM", "HIGH"]


@dataclass
class EconomicEvent:
    date: datetime
    country: str
    event: str
    impact: EventImpact
    actual: str | None = None
    forecast: str | None = None
    previous: str | None = None
