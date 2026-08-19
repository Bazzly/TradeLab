"""Centralized secret lookup — fixes a real ordering bug found live
(README_forex.md Section 11, 2026-08-19).

Streamlit only mirrors secrets.toml into os.environ lazily, the first time
ANYTHING in the running process touches st.secrets. A module that reads a
secret via plain os.environ.get(key) sees an empty environment if it's
reached before anything else has touched st.secrets in that process —
confirmed live: TWELVEDATA_API_KEY was genuinely configured, but
os.environ.get("TWELVEDATA_API_KEY") returned None when Dashboard (which
never touches st.secrets itself) was the first page run, only becoming
populated after a *different* page (Journal, via lib.auth) touched
st.secrets first in the same process. Since page load order isn't
controlled — Dashboard is page 1, so this would misfire in production for
any fresh session that starts there — every secret lookup in this codebase
should go through get_secret() instead of os.environ.get() directly.

get_secret() reads st.secrets directly (no ordering dependency) and falls
back to os.environ for contexts with no Streamlit runtime at all (one-off
scripts, migrations, tests that set os.environ manually).
"""

import os

import streamlit as st


def get_secret(key: str, default: str | None = None) -> str | None:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:  # noqa: BLE001 — no secrets.toml at all, e.g. a fresh clone
        pass
    return os.environ.get(key, default)
