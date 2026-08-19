"""Paper Trading Bot trade log CRUD (migrations/0004_bot_trades.sql).

No user_id/RLS scoping — this is a single shared, public log (see the
migration's own comment for why). lib.db.connection.get_connection still
works fine without a user_id; it just skips the session-scoped RLS setting.
"""

from datetime import datetime

from psycopg.rows import dict_row

from lib.db.connection import get_connection
from lib.schemas import TradingSignal


def get_active_trade(asset: str, setup_type: str) -> dict | None:
    """The PENDING or OPEN trade for this asset+setup, if any — used to
    avoid opening a second trade while one's already in flight."""
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select * from bot_trades
                where asset = %(asset)s and setup_type = %(setup_type)s
                  and status in ('PENDING', 'OPEN')
                order by created_at desc
                limit 1
                """,
                {"asset": asset, "setup_type": setup_type},
            )
            return cur.fetchone()


def create_pending_trade(asset: str, setup_type: str, signal: TradingSignal) -> dict:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                insert into bot_trades (
                    asset, setup_type, direction, entry_zone_low, entry_zone_high,
                    stop_loss, target, risk_reward_ratio, confidence_score,
                    reasons, confirmation_factors, status, signal_timestamp
                ) values (
                    %(asset)s, %(setup_type)s, %(direction)s, %(entry_zone_low)s, %(entry_zone_high)s,
                    %(stop_loss)s, %(target)s, %(risk_reward_ratio)s, %(confidence_score)s,
                    %(reasons)s, %(confirmation_factors)s, 'PENDING', %(signal_timestamp)s
                )
                returning *
                """,
                {
                    "asset": asset,
                    "setup_type": setup_type,
                    "direction": signal.direction,
                    "entry_zone_low": signal.entry_zone[0],
                    "entry_zone_high": signal.entry_zone[1],
                    "stop_loss": signal.stop_loss,
                    "target": signal.take_profit_levels[0],
                    "risk_reward_ratio": signal.risk_reward_ratio,
                    "confidence_score": signal.confidence_score,
                    "reasons": signal.reasons,
                    "confirmation_factors": signal.confirmation_factors,
                    "signal_timestamp": signal.timestamp,
                },
            )
            row = cur.fetchone()
            conn.commit()
            return row


def fill_entry(trade_id: str, entry_price: float, filled_at: datetime) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update bot_trades
                set status = 'OPEN', entry_price = %(entry_price)s, entry_filled_at = %(filled_at)s
                where id = %(id)s
                """,
                {"entry_price": entry_price, "filled_at": filled_at, "id": trade_id},
            )
            conn.commit()


def close_trade(trade_id: str, exit_price: float, exit_reason: str, r_multiple: float, closed_at: datetime) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update bot_trades
                set status = 'CLOSED', exit_price = %(exit_price)s, exit_reason = %(exit_reason)s,
                    r_multiple = %(r_multiple)s, closed_at = %(closed_at)s
                where id = %(id)s
                """,
                {
                    "exit_price": exit_price,
                    "exit_reason": exit_reason,
                    "r_multiple": r_multiple,
                    "closed_at": closed_at,
                    "id": trade_id,
                },
            )
            conn.commit()


def expire_trade(trade_id: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("update bot_trades set status = 'EXPIRED' where id = %(id)s", {"id": trade_id})
            conn.commit()


def list_trades(status: str | None = None, limit: int = 200) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if status:
                cur.execute(
                    "select * from bot_trades where status = %(status)s order by created_at desc limit %(limit)s",
                    {"status": status, "limit": limit},
                )
            else:
                cur.execute("select * from bot_trades order by created_at desc limit %(limit)s", {"limit": limit})
            return cur.fetchall()
