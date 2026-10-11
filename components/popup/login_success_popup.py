import streamlit as st


# =========================================================
# Login Success Popup
# =========================================================

@st.dialog("What Would You Like to Do?")
def login_success_popup():

    st.markdown(
        """
        <div class="login-required-description">
            Continue your NovelMatch journey by choosing
            what you would like to do next.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    # -----------------------------------------------------
    # Edit Preferences
    # -----------------------------------------------------

    if st.button(
        "Edit My Preferences",
        use_container_width=True,
        key="success-edit-preferences-button"
    ):
        st.switch_page("pages/preferences.py")

    # -----------------------------------------------------
    # Find a Novel Match
    # -----------------------------------------------------

    if st.button(
        "Find a Novel Match →",
        type="primary",
        use_container_width=True,
        key="success-find-match-button"
    ):
        st.switch_page("pages/novel.py")

    # -----------------------------------------------------
    # Maybe Later
    # -----------------------------------------------------

    if st.button(
        "Maybe Later",
        use_container_width=True,
        key="success-cancel-button"
    ):
        st.switch_page("main.py")