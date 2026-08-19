"""Shared identity resolution for pages that need a user id (Journal, Risk).

Handles both the real st.login()/OIDC flow and, until that's configured, a
manual dev-user-id fallback so those pages stay testable without blocking
on Google Cloud OAuth setup.
"""

import streamlit as st


def _google_oauth_configured() -> bool:
    if not hasattr(st, "secrets") or "auth" not in st.secrets:
        return False
    google = st.secrets["auth"].get("google", {})
    # An empty [auth.google] block (client_id/client_secret both blank) is
    # what secrets.toml.example ships with — that must NOT count as
    # configured, or st.login() gets offered with credentials that can't work.
    return bool(google.get("client_id")) and bool(google.get("client_secret"))


def get_user_id() -> str | None:
    """Returns the current user's id, or None if the caller should st.stop()
    (not logged in yet, or no dev user id typed in)."""
    if _google_oauth_configured():
        if not st.user.is_logged_in:
            st.info("Please log in to continue.")
            if st.button("Log in with Google"):
                st.login("google")
            return None
        user_id = st.user.email
        st.sidebar.success(f"Logged in as {user_id}")
        if st.sidebar.button("Log out"):
            st.logout()
        return user_id

    st.info(
        "Login isn't wired up yet (no Google OAuth client in secrets — see "
        "`.streamlit/secrets.toml.example`). Using a manual dev user id for now; "
        "this will switch to real login automatically once configured."
    )
    user_id = st.sidebar.text_input("Dev user id (stand-in for login)", value="dev-user")
    return user_id or None
