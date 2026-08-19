from dataclasses import dataclass

from psycopg.rows import dict_row

from lib.db.connection import get_connection

DEFAULTS = {"account_equity": 10000.0, "risk_pct_per_trade": 1.0, "daily_loss_limit_pct": 3.0}


@dataclass
class UserSettings:
    account_equity: float
    risk_pct_per_trade: float
    daily_loss_limit_pct: float


def get_settings(user_id: str) -> UserSettings:
    with get_connection(user_id) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select * from user_settings where user_id = %(user_id)s", {"user_id": user_id})
            row = cur.fetchone()
            if row is None:
                return UserSettings(**DEFAULTS)
            return UserSettings(
                account_equity=float(row["account_equity"]),
                risk_pct_per_trade=float(row["risk_pct_per_trade"]),
                daily_loss_limit_pct=float(row["daily_loss_limit_pct"]),
            )


def save_settings(user_id: str, settings: UserSettings) -> None:
    with get_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into user_settings (user_id, account_equity, risk_pct_per_trade, daily_loss_limit_pct)
                values (%(user_id)s, %(account_equity)s, %(risk_pct_per_trade)s, %(daily_loss_limit_pct)s)
                on conflict (user_id) do update set
                    account_equity = excluded.account_equity,
                    risk_pct_per_trade = excluded.risk_pct_per_trade,
                    daily_loss_limit_pct = excluded.daily_loss_limit_pct,
                    updated_at = now()
                """,
                {
                    "user_id": user_id,
                    "account_equity": settings.account_equity,
                    "risk_pct_per_trade": settings.risk_pct_per_trade,
                    "daily_loss_limit_pct": settings.daily_loss_limit_pct,
                },
            )
            conn.commit()
