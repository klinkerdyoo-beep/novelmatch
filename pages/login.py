import streamlit as st
import base64
from components.navbar import navbar, save_session_to_cookies
from components.popup.login_success_popup import login_success_popup
from components.api_client import NovelMatchAPIError, login

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


navbar()

if st.session_state.get("access_token"):
    st.switch_page("main.py")


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

        username_or_email = st.text_input(
            "Username or Email",
            placeholder="Enter your username or email...",
            key="login-username-or-email"
        )
        

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

            if not username_or_email.strip():
                st.warning("Please enter your username or email.")

            elif not password.strip():
                st.warning("Please enter your password.")

            else:
                try:
                    result = login(username_or_email.strip(), password)
                except NovelMatchAPIError as exc:
                    st.error("username or password is invalid")
                else:
                    st.session_state.logged_in = True
                    st.session_state.access_token = result["access_token"]
                    st.session_state.user = result["user"]
                    st.session_state.user_id = result["user"]["id"]
                    user_meta = result.get("user", {}).get("user_metadata", {})
                    display_name = user_meta.get("name") or username_or_email.strip()
                    st.session_state.username = display_name

                    save_session_to_cookies(
                        result["access_token"],
                        display_name,
                        result["user"]["id"],
                    )
                    
                    login_success_popup()


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