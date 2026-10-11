
import streamlit as st


# =========================================================
# CSS
# =========================================================

with open("style/popup.css", encoding="utf-8") as f:
    st.markdown(
        f"<style>{f.read()}</style>",
        unsafe_allow_html=True
    )


# =========================================================
# Login Required Popup
# =========================================================

@st.dialog("Ready to Find Your Match?")
def login_required_popup():

    st.markdown(
        """
        <div class="login-required-description">
            Log in or create an account to discover novels
            tailored to your reading preferences.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    if st.button(
        "Log In →",
        type="primary",
        use_container_width=True,
        key="required-login-button"
    ):
        st.switch_page("pages/login.py")

    if st.button(
        "Create an Account",
        use_container_width=True,
        key="required-signup-button"
    ):
        st.switch_page("pages/signup.py")

    if st.button(
        "Maybe Later",
        use_container_width=True,
        key="required-cancel-button"
    ):
        st.switch_page("main.py")
