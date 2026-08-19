"""Trading Journal CRUD (README_forex.md Section 4.7, 5.4, 9 item 6).

Every function requires `user_id` and routes through `get_connection`,
which sets `app.current_user_id` for the session — Row-Level Security on
the `journal_entries` table (migrations/0001_init.sql) is the actual
tenancy enforcement, this is not just an application-layer filter.
"""

from datetime import date

from psycopg.rows import dict_row

from lib.db.connection import get_connection
from lib.schemas import JournalEntry


def _row_to_entry(row: dict) -> JournalEntry:
    return JournalEntry(
        id=str(row["id"]),
        user_id=row["user_id"],
        date=row["date"],
        asset=row["asset"],
        direction=row["direction"],
        entry=float(row["entry"]),
        stop_loss=float(row["stop_loss"]),
        take_profit=float(row["take_profit"]),
        position_size=float(row["position_size"]),
        risk_amount=float(row["risk_amount"]),
        timeframe=row["timeframe"],
        reason_for_entry=row["reason_for_entry"],
        strategy_id=str(row["strategy_id"]) if row["strategy_id"] else None,
        chart_screenshot_url=row["chart_screenshot_url"],
        reason_for_exit=row["reason_for_exit"],
        result=row["result"],
        r_multiple=float(row["r_multiple"]) if row["r_multiple"] is not None else None,
        mistakes=list(row["mistakes"] or []),
        emotional_state=row["emotional_state"],
        lessons_learned=row["lessons_learned"],
    )


def create_entry(user_id: str, entry: JournalEntry) -> JournalEntry:
    with get_connection(user_id) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                insert into journal_entries (
                    user_id, date, asset, direction, entry, stop_loss, take_profit,
                    position_size, risk_amount, strategy_id, timeframe,
                    chart_screenshot_url, reason_for_entry, reason_for_exit,
                    result, r_multiple, mistakes, emotional_state, lessons_learned
                ) values (
                    %(user_id)s, %(date)s, %(asset)s, %(direction)s, %(entry)s, %(stop_loss)s,
                    %(take_profit)s, %(position_size)s, %(risk_amount)s, %(strategy_id)s,
                    %(timeframe)s, %(chart_screenshot_url)s, %(reason_for_entry)s,
                    %(reason_for_exit)s, %(result)s, %(r_multiple)s, %(mistakes)s,
                    %(emotional_state)s, %(lessons_learned)s
                )
                returning *
                """,
                {
                    "user_id": user_id,
                    "date": entry.date,
                    "asset": entry.asset,
                    "direction": entry.direction,
                    "entry": entry.entry,
                    "stop_loss": entry.stop_loss,
                    "take_profit": entry.take_profit,
                    "position_size": entry.position_size,
                    "risk_amount": entry.risk_amount,
                    "strategy_id": entry.strategy_id,
                    "timeframe": entry.timeframe,
                    "chart_screenshot_url": entry.chart_screenshot_url,
                    "reason_for_entry": entry.reason_for_entry,
                    "reason_for_exit": entry.reason_for_exit,
                    "result": entry.result,
                    "r_multiple": entry.r_multiple,
                    "mistakes": entry.mistakes,
                    "emotional_state": entry.emotional_state,
                    "lessons_learned": entry.lessons_learned,
                },
            )
            row = cur.fetchone()
            conn.commit()
            return _row_to_entry(row)


def list_entries(user_id: str) -> list[JournalEntry]:
    with get_connection(user_id) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select * from journal_entries order by date desc, created_at desc")
            return [_row_to_entry(row) for row in cur.fetchall()]


def update_entry_exit(
    user_id: str,
    entry_id: str,
    reason_for_exit: str,
    result: str,
    r_multiple: float,
    lessons_learned: str | None = None,
) -> None:
    with get_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update journal_entries
                set reason_for_exit = %(reason_for_exit)s,
                    result = %(result)s,
                    r_multiple = %(r_multiple)s,
                    lessons_learned = coalesce(%(lessons_learned)s, lessons_learned)
                where id = %(entry_id)s
                """,
                {
                    "reason_for_exit": reason_for_exit,
                    "result": result,
                    "r_multiple": r_multiple,
                    "lessons_learned": lessons_learned,
                    "entry_id": entry_id,
                },
            )
            conn.commit()


def delete_entry(user_id: str, entry_id: str) -> None:
    with get_connection(user_id) as conn:
        with conn.cursor() as cur:
            cur.execute("delete from journal_entries where id = %(entry_id)s", {"entry_id": entry_id})
            conn.commit()
