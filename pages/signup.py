import streamlit as st
import base64

from components.navbar import navbar
from components.api_client import NovelMatchAPIError, login, signup


# =========================================================
# Page Config
# =========================================================

st.set_page_config(
    page_title="Sign Up | Novel Match",
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
# Sign Up Page
# =========================================================

with st.container(key="login-content"):

    st.markdown(
        """
        <h1>Create Your Account</h1>

        <div class="login-description">
            Sign up to discover novels that match your taste.
        </div>
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # Sign Up Card
    # =====================================================

    with st.container(
        border=True,
        key="login-card"
    ):

        st.markdown("### Sign Up")

        st.caption(
            "Enter your account details below."
        )


        # =================================================
        # Name
        # =================================================

        name = st.text_input(
            "Name",
            placeholder="Enter your name...",
            key="signup-name"
        )


        # =================================================
        # Email
        # =================================================

        email = st.text_input(
            "Email",
            placeholder="Enter your email...",
            key="signup-email"
        )


        # =================================================
        # Password
        # =================================================

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Create a password...",
            key="signup-password"
        )


        # =================================================
        # Confirm Password
        # =================================================

        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            placeholder="Confirm your password...",
            key="signup-confirm-password"
        )


        # =================================================
        # Sign Up Button
        # =================================================

        if st.button(
            "Create Account →",
            type="primary",
            use_container_width=True,
            key="login-button"
        ):

            if not name.strip():

                st.warning(
                    "Please enter your name."
                )

            elif not email.strip():

                st.warning(
                    "Please enter your email."
                )

            elif not password.strip():
                
                st.warning(
                    "Please create a password."
                )

            elif password != confirm_password:

                st.warning(
                    "Passwords do not match."
                )

            else:
                try:
                    result = signup(name.strip(), email.strip(), password)
                except NovelMatchAPIError as exc:
                    st.error(str(exc))
                else:
                    if not result.get("access_token"):
                        st.info("Account created. Check your email, then log in.")
                    else:
                        st.session_state.logged_in = True
                        st.session_state.access_token = result["access_token"]
                        st.session_state.user = result["user"]
                        st.session_state.user_id = result["user"]["id"]
                        st.session_state.username = name
                        st.session_state.user_email = email
                        st.switch_page("pages/preferences.py")


        # =================================================
        # Divider
        # =================================================

        st.markdown(
            """
            <div class="login-divider">
                <span>or</span>
            </div>
            """,
            unsafe_allow_html=True
        )


        # =================================================
        # Login
        # =================================================

        st.markdown(
            """
            <div class="login-signup-text">
                Already have an account?
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button(
            "Log In",
            use_container_width=True,
            key="signup-button"
        ):

            st.switch_page(
                "pages/login.py"
            )