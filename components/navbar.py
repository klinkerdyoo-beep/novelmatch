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


# =========================================================
# Navbar
# =========================================================

PAGE_HOME = "main.py"
PAGE_PREFERENCES = "pages/preferences.py"
PAGE_ACCOUNT = "pages/account.py"
PAGE_HISTORY = "pages/history.py"
PAGE_LOGIN = "pages/login.py"


def logout():
    st.session_state.clear()
    st.switch_page(PAGE_LOGIN)


def navbar():

    username = st.session_state.get("username", "")

    with st.container(key="navbar"):

        col_logo, col_space, col_pref, col_account = st.columns(
            [2, 6, 1.5, 2],
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
                st.page_link(PAGE_HOME, label="Home")

        with col_pref:
            with st.container(key="nav_pref"):
                st.page_link(PAGE_PREFERENCES, label="Preferences")

        # ---------------- Account ----------------
        with col_account:

            if username:
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

                    st.page_link(PAGE_ACCOUNT, label="My Account")
                    st.page_link(PAGE_HISTORY, label="Your Search History")

                    st.divider()

                    st.button(
                        "Log Out",
                        on_click=logout,
                        key="nav_logout",
                        use_container_width=True,
                    )

            else:
                with st.container(key="nav_login"):
                    st.page_link(PAGE_LOGIN, label="Log in")