
import streamlit as st
import base64

from components.navbar import navbar
from components.api_client import NovelMatchAPIError, get_user_info, get_preferences


# =========================================================
# Page Config
# =========================================================

st.set_page_config(
    page_title="My Account",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

css_files = [
    "style/global.css",
    "style/navbar.css",
    "style/form.css",
    "style/account.css",
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

with open("assets/about-you-bg.png", "rb") as f:
    hero_bg = base64.b64encode(f.read()).decode()

st.markdown(
    f"""
    <style>
        .stApp {{
            background-image: url("data:image/png;base64,{hero_bg}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# Session State
# =========================================================

token = st.session_state.get("access_token")
if not token:
    st.warning("Session expired or not logged in. Please log in again.")
    st.switch_page("pages/login.py")
    st.stop()

try:
    user_info = get_user_info(token)
    username = user_info.get("user", {}).get("username", "")
    user_email = user_info.get("user", {}).get("email") or "No email provided"
except NovelMatchAPIError as exc:
    st.error(f"Failed to load account information: {exc}")
    st.stop()

preferences_response = {}
try:
    preferences_response = get_preferences(token)
except NovelMatchAPIError:
    preferences_response = {}

prefs_data = preferences_response.get("preferences", {})
genre_prefs = prefs_data.get("genre_preferences", {})
char_prefs = prefs_data.get("character_preferences", {})
story_prefs = prefs_data.get("story_element_preferences", {})

favorite_genres = genre_prefs.get("enjoyed_genres", [])
disliked_genres = genre_prefs.get("disliked_genres", [])

enjoy_characters = char_prefs.get("enjoyed_character", [])
liked_characters = char_prefs.get("liked_character") or ""
disliked_character = char_prefs.get("disliked_character") or ""

liked_stories = story_prefs.get("liked_story", [])
disliked_stories = story_prefs.get("disliked_story", [])


# =========================================================
# Helper: Preference Label
# =========================================================

def preference_label(text):
    st.markdown(
        f'<div class="preference-label">{text}</div>',
        unsafe_allow_html=True
    )


# =========================================================
# Page Content
# =========================================================

with st.container(key="preferences-content"):

    # =====================================================
    # Page Header
    # =====================================================

    st.markdown(
        """
        <h1>My<br>Account</h1>

        <div class="preferences-description">
            Manage your account and view your reading preferences.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    # =====================================================
    # Account Card
    # =====================================================

    with st.container(
        border=True,
        key="account-card"
    ):

        # =================================================
        # Account Information
        # =================================================

        st.markdown("### Account Information")

        col1, col2 = st.columns(2)

        with col1:
            st.text_input(
                "Username",
                value=username,
                disabled=True,
                key="account-username"
            )

        with col2:
            st.text_input(
                "Email",
                value=user_email,
                placeholder="No email provided",
                disabled=True,
                key="account-email"
            )

        st.divider()

        # =================================================
        # Reading Preferences
        # =================================================

        st.markdown("### Reading Preferences")


        # =================================================
        # Genres
        # =================================================

        col1, col2 = st.columns(2)

        with col1:
            preference_label("Genres You Enjoy")

            if favorite_genres:
                st.write(", ".join(favorite_genres))
            else:
                st.caption("None selected.")

        with col2:
            preference_label("Genres You Don't Like")

            if disliked_genres:
                st.write(", ".join(disliked_genres))
            else:
                st.caption("None selected.")

        st.divider()


        # =================================================
        # Character Preferences
        # =================================================

        st.markdown("### Character Preferences")

        col1, col2 = st.columns(2)

        with col1:
            preference_label("Character Traits You Enjoy")

            if enjoy_characters:
                st.write(", ".join(enjoy_characters))
            else:
                st.caption("None selected.")

        with col2:
            preference_label("Describe a Character You Like")

            if liked_characters.strip():
                st.write(liked_characters)
            else:
                st.caption("Not provided.")

            preference_label("Describe a Character You Dislike")
            if disliked_character.strip():
                st.write(disliked_character)
            else:
                st.caption("Not provided.")

        st.divider()


        # =================================================
        # Story Preferences
        # =================================================

        st.markdown("### Story Preferences")

        col1, col2 = st.columns(2)

        with col1:
            preference_label("Story Elements You Like")

            if liked_stories:
                st.write(", ".join(liked_stories))
            else:
                st.caption("None selected.")

        with col2:
            preference_label("Story Elements You Don't Like")

            if disliked_stories:
                st.write(", ".join(disliked_stories))
            else:
                st.caption("None selected.")

        st.divider()

        # =================================================
        # Actions
        # =================================================
        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "Edit Preferences",
                type="primary",
                use_container_width=True,
                key="account-edit-preferences"
            ):
                st.switch_page("pages/preferences.py")


        with col2:
            if st.button(
                "Back to Home",
                type="secondary",
                use_container_width=True,
                key="account-back-home"
            ):
                st.switch_page("main.py")
