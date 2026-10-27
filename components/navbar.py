import streamlit as st
import streamlit.components.v1 as components
import base64
import json
from datetime import datetime, timedelta
import extra_streamlit_components as stx

# =========================================================
# 1. Cookie Session Manager & Helpers
# =========================================================
COOKIE_NAME = "novelmatch_session"


def get_cookie_manager():
    """Get or create session-isolated CookieManager instance."""
    if "cookie_manager" not in st.session_state:
        st.session_state["cookie_manager"] = stx.CookieManager(key="novelmatch_cookie_manager")
    return st.session_state["cookie_manager"]


def save_session_to_cookies(
    access_token: str,
    username: str,
    user_id,
    days: int = 7,
) -> None:
    """Save user authentication credentials to browser cookies."""
    st.session_state.pop("logged_out", None)
    payload = json.dumps({
        "access_token": access_token,
        "username": username,
        "user_id": str(user_id),
    })
    try:
        cookie_mgr = get_cookie_manager()
        cookie_mgr.set(
            COOKIE_NAME,
            payload,
            expires_at=datetime.now() + timedelta(days=days),
            key="save_auth_cookie",
        )
    except Exception:
        pass


def restore_session_from_cookies() -> bool:
    """Restore session_state from browser cookies if not already authenticated."""
    if st.session_state.get("logged_out"):
        return False

    if st.session_state.get("access_token") and st.session_state.get("username"):
        return True

    try:
        cookie_mgr = get_cookie_manager()
        cookies = cookie_mgr.get_all(key="get_all_cookies")
        raw = (cookies or {}).get(COOKIE_NAME) or cookie_mgr.get(COOKIE_NAME)
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
        cookie_mgr = get_cookie_manager()
        cookie_mgr.set(
            COOKIE_NAME,
            "",
            path="/",
            expires_at=datetime.now() - timedelta(days=1),
            max_age=0,
            key="clear_cookie_set",
        )
        cookie_mgr.delete(COOKIE_NAME, key="clear_auth_cookie")
    except Exception:
        pass
    try:
        components.html(
            f"""
            <script>
                window.parent.document.cookie = "{COOKIE_NAME}=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT;";
                window.document.cookie = "{COOKIE_NAME}=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT;";
            </script>
            """,
            height=0,
            width=0,
        )
    except Exception:
        pass


PAGE_HOME = "main.py"
PAGE_PREFERENCES = "pages/preferences.py"
PAGE_ACCOUNT = "pages/account.py"
PAGE_HISTORY = "pages/history.py"
PAGE_LOGIN = "pages/login.py"


def logout():
    # Revoke token on Supabase so other browsers can't reuse it
    token = st.session_state.get("access_token")
    if token:
        from components.api_client import logout_user
        logout_user(token)
    clear_session_cookies()
    st.session_state.clear()
    st.session_state["logged_out"] = True
    st.switch_page(PAGE_LOGIN)


# =========================================================
# 2. โหลด Logo และ CSS
# =========================================================
try:
    with open("assets/logo.png", "rb") as f:
        logo = base64.b64encode(f.read()).decode()
except Exception:
    logo = ""

css_files = [
    "style/global.css",
    "style/navbar.css",
]

for css_file in css_files:
    try:
        with open(css_file, encoding="utf-8") as f:
            st.markdown(
                f"<style>{f.read()}</style>",
                unsafe_allow_html=True
            )
    except Exception:
        pass


# =========================================================
# 3. ฟังก์ชัน Navbar (ประกาศให้สมบูรณ์ในก้อนเดียว)
# =========================================================
def navbar():
    if st.session_state.get("logged_out"):
        clear_session_cookies()
    else:
        restored = restore_session_from_cookies()
        # CookieManager loads async — on the first cycle after refresh it may
        # return empty.  Do exactly ONE rerun so it has time to sync cookies.
        if not restored and not st.session_state.get("_cookie_retry_done"):
            st.session_state["_cookie_retry_done"] = True
            st.rerun()
        st.session_state.pop("_cookie_retry_done", None)

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
                    <a href="/" target="_self" class="nav-logo-link">
                        <img
                            src="data:image/png;base64,{logo}"
                            class="nav-logo"
                            alt="Novel Match"
                        />
                    </a>
                    """
                )

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