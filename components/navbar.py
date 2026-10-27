import streamlit as st
import base64


# =========================================================
# Logo
# =========================================================

with open("assets/logo.png", "rb") as f:
    logo = base64.b64encode(f.read()).decode()


# =========================================================
# CSS
# =========================================================

css_files = [
    "style/global.css",
    "style/navbar.css",
]

for css_file in css_files:
    with open(css_file, encoding="utf-8") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True
        )


import json
from datetime import datetime, timedelta
import extra_streamlit_components as stx

# =========================================================
# Cookie Session Manager
# =========================================================

COOKIE_NAME = "novelmatch_session"
cookie_manager = stx.CookieManager(key="novelmatch_cookie_manager")


def save_session_to_cookies(
    access_token: str,
    username: str,
    user_id,
    days: int = 7,
) -> None:
    """Save user authentication credentials to browser cookies."""
    payload = json.dumps({
        "access_token": access_token,
        "username": username,
        "user_id": str(user_id),
    })
    try:
        cookie_manager.set(
            COOKIE_NAME,
            payload,
            expires_at=datetime.now() + timedelta(days=days),
            key="save_auth_cookie",
        )
    except Exception:
        pass


def restore_session_from_cookies() -> bool:
    """Restore session_state from browser cookies if not already authenticated."""
    if st.session_state.get("access_token") and st.session_state.get("username"):
        return True

    try:
        raw = cookie_manager.get(COOKIE_NAME)
        if not raw:
            return False

        data = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(data, dict) and data.get("access_token"):
            st.session_state["access_token"] = data["access_token"]
            st.session_state["username"] = data.get("username", "")
            st.session_state["user_id"] = data.get("user_id", "")
            st.session_state["logged_in"] = True
            return True
    except Exception:
        pass

    return False


def clear_session_cookies() -> None:
    """Remove authentication cookie on logout."""
    try:
        cookie_manager.delete(COOKIE_NAME, key="clear_auth_cookie")
    except Exception:
        pass


PAGE_HOME = "main.py"
PAGE_PREFERENCES = "pages/preferences.py"
PAGE_ACCOUNT = "pages/account.py"
PAGE_HISTORY = "pages/history.py"
PAGE_LOGIN = "pages/login.py"


def logout():
    clear_session_cookies()
    st.session_state.clear()
    st.switch_page(PAGE_LOGIN)


def navbar():
    restore_session_from_cookies()

    username = st.session_state.get("username", "")

    with st.container(key="navbar"):

        col_logo, col_space, col_pref, col_account = st.columns(
            [2.2, 5.8, 1.8, 2.2],
            vertical_alignment="center",
        )

        with col_logo:
            with st.container(key="nav_logo"):
                st.html(
                    f"""
                    <img
                        src="data:image/png;base64,{logo}"
                        class="nav-logo"
                        alt="Novel Match"
                    />
                    """
                )
                st.page_link(PAGE_HOME, label="")

        with col_pref:
            with st.container(key="nav_pref"):
                st.page_link(PAGE_PREFERENCES, label="Preferences", use_container_width=True)

        # ---------------- Account ----------------
        with col_account:

            if username:
                with st.container(key="nav_account"):
                    with st.popover(username, use_container_width=True):

                        st.markdown(
                            f"""
                            <div class="account-welcome">
                                <span>Welcome,</span>
                                <strong>{username}</strong>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        st.divider()

                        st.page_link(PAGE_ACCOUNT, label="My Account", use_container_width=True)
                        st.page_link(PAGE_HISTORY, label="Your Search History", use_container_width=True)

                        st.divider()

                        st.button(
                            "Log Out",
                            on_click=logout,
                            key="nav_logout",
                            use_container_width=True,
                        )

            else:
                with st.container(key="nav_login"):
                    st.page_link(PAGE_LOGIN, label="Log in", use_container_width=True)