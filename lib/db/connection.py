import os
from contextlib import contextmanager
from typing import Iterator

import psycopg


def is_configured() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


@contextmanager
def get_connection(user_id: str | None = None) -> Iterator[psycopg.Connection]:
    """Yields a Neon Postgres connection. If `user_id` is given, sets
    `app.current_user_id` for the session so Row-Level Security policies
    (see migrations/0001_init.sql) can scope queries to that user — this is
    the tenancy enforcement boundary, not application-layer filtering alone.
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL is not set — see .streamlit/secrets.toml.example. "
            "Create a free Neon project (neon.tech) and paste its connection string."
        )

    with psycopg.connect(dsn) as conn:
        if user_id is not None:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('app.current_user_id', %s, false)", (user_id,))
        yield conn
