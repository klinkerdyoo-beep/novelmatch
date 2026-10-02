import streamlit as st
import base64

from components.navbar import navbar


# =========================================================
# Page Config
# =========================================================

st.set_page_config(
    page_title="Log In | Novel Match",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

css_files = [
    "style/global.css",
    "style/navbar.css",
    "style/login.css",
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

navbar()


# =========================================================
# Background
# =========================================================

with open("assets/login-you-bg.png", "rb") as f:
    hero_bg = base64.b64encode(f.read()).decode()

st.markdown(
    f"""
    <style>
        .stApp {{
            background-image:
                url("data:image/png;base64,{hero_bg}");

            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# Login Page
# =========================================================

with st.container(key="login-content"):

    st.markdown(
        """
            <h1>Welcome Back</h1>
            <div class="login-description">
                 Log in to continue discovering novels
                that match your taste.
            </div>
        """,
        unsafe_allow_html=True
    )


    # -----------------------------------------------------
    # Login Card
    # -----------------------------------------------------

    with st.container(
        border=True,
        key="login-card"
    ):
        st.markdown("### Log In")
        st.caption("Enter your account details below.")

        email = st.text_input(
            "Email",
            placeholder="Enter your email...",
            key="login-email"
        )


        # ------------------------------------------------
        # Password
        # -------------------------------------------------

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password...",
            key="login-password"
        )


        # -------------------------------------------------
        # Login Button
        # -------------------------------------------------

        if st.button(
            "Log In →",
            type="primary",
            use_container_width=True,
            key="login-button"
        ):

            if not email.strip():

                st.warning("Please enter your email.")

            elif not password.strip():

                st.warning("Please enter your password.")

            else:

                st.session_state.logged_in = True
                st.session_state.user_email = email

                st.switch_page(
                    "pages/preferences.py"
                )


        # -------------------------------------------------
        # Divider
        # -------------------------------------------------

        st.markdown(
            """
            <div class="login-divider">
                <span>or</span>
            </div>
            """,
            unsafe_allow_html=True
        )


        # -------------------------------------------------
        # Sign Up
        # -------------------------------------------------

        st.markdown(
            """
            <div class="login-signup-text">
                Don't have an account?
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button(
            "Create an Account",
            use_container_width=True,
            key="signup-button"
        ):
            st.switch_page(
                "pages/signup.py"
            )