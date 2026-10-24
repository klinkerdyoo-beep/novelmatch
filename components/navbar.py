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



def navbar():
    username = st.session_state.get(
        "username",
        ""
    )

    # -----------------------------------------------------
    # Logged In
    # -----------------------------------------------------

    if username:

        account_html = f"""
        <div class="nav-account">

            <div class="nav-account-trigger">
                <span>{username}</span>
                <span class="nav-account-arrow">⌄</span>
            </div>

            <div class="nav-account-dropdown">

                <div class="account-welcome">
                    <span>Welcome,</span>
                    <strong>{username}</strong>
                </div>

                <div class="account-divider"></div>

                <a
                    href="?nav=account"
                    target="_self"
                    class="account-menu-item"
                >
                    <span>My Account</span>
                </a>

                <a
                    href="?nav=history"
                    target="_self"
                    class="account-menu-item"
                >
                    <span>Your Search History</span>
                </a>

                <div class="account-divider"></div>

                <a
                    href="pages/logout.py"
                    target="_self"
                    class="account-menu-item account-logout"
                >
                    <span>Log Out</span>
                </a>

            </div>

        </div>
        """

    # -----------------------------------------------------
    # Logged Out
    # -----------------------------------------------------

    else:

        account_html = """
        <a
            href="pages/login.py"
            target="_self"
            class="nav-button nav-login-button"
        >
            Log in
        </a>
        """


    # =====================================================
    # Navbar HTML
    # =====================================================

    st.html(
        f"""
        <div class="navbar">

            <a
                href="pages/home.py"
                target="_self"
                class="nav-logo-link"
            >
                <img
                    src="data:image/png;base64,{logo}"
                    class="nav-logo"
                    alt="Novel Match"
                />
            </a>


            <div class="nav-actions">

                <a
                    href="pages/preferences.py"
                    target="_self"
                    class="nav-button"
                >
                    Preferences
                </a>

                {account_html}

            </div>

        </div>
        """
    )