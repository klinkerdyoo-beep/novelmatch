import streamlit as st
import base64
from components.api_client import NovelMatchAPIError, get_preferences

from components.navbar import navbar


# =========================================================
# Page Config
# =========================================================

st.set_page_config(
    page_title="Preview",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

css_files = [
    "style/global.css",
    "style/navbar.css",
    "style/form.css",
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
# Helper Function
# =========================================================

def show_list(title, items):
    st.markdown(f"#### {title}")

    if items:
        st.write(", ".join(items))
    else:
        st.caption("None selected.")


def show_text(title, value, empty_message="Not provided."):
    st.markdown(f"#### {title}")

    if value and value.strip():
        st.write(value)
    else:
        st.caption(empty_message)


token = st.session_state.get("access_token")
if token and not st.session_state.get("preferences_loaded", False):
    try:
        preferences_response = get_preferences(token)
    except NovelMatchAPIError as exc:
        st.error(f"Could not load your preferences: {exc}")
    else:
        saved = preferences_response.get("preferences", {})
        genres = saved.get("genre_preferences", {})
        characters = saved.get("character_preferences", {})
        stories = saved.get("story_element_preferences", {})
        st.session_state.enjoyed_genres = genres.get("enjoyed_genres", [])
        st.session_state.disliked_genres = genres.get("disliked_genres", [])
        st.session_state.enjoyed_character = characters.get("enjoyed_character", [])
        st.session_state.liked_character = characters.get("liked_character", "")
        st.session_state.disliked_character = characters.get("disliked_character", "")
        st.session_state.enjoyed_story = stories.get("liked_story", [])
        st.session_state.disliked_story = stories.get("disliked_story", [])
        st.session_state.preferences_loaded = True


# =========================================================
# Main Layout
# =========================================================

with st.container(key="preview-content"):

    col1, col2 = st.columns(
        [0.4, 1.6],
        gap="large"
    )

    # =====================================================
    # Left - Introduction
    # =====================================================

    with col1:

        st.markdown(
            """
            <h1>
                Preview
            </h1>

            <div class="preview-description">
                Review your reading preferences and novel information
                before continuing with your personalized analysis.
            </div>

            <div class="preview-step">
                3/3 Step
            </div>
            """,
            unsafe_allow_html=True
        )

    # =====================================================
    # Right - Preview Card
    # =====================================================

    with col2:

        with st.container(
            border=True,
            key="preview-card"
        ):

            st.markdown(
                '<p class="preferences-eyebrow">ALMOST THERE</p>',
                unsafe_allow_html=True
            )

            st.markdown("### Review Your Information")

            st.markdown(
                "Check your information below before continuing."
            )

            # =================================================
            # NOVEL INFORMATION
            # =================================================

            st.markdown(
                '<div class="preview-section-title">Novel Details</div>',
                unsafe_allow_html=True
            )

            show_text(
                "Novel Title",
                st.session_state.get("novel_title", "")
            )

            show_text(
                "Author",
                st.session_state.get("novel_author", "")
            )

            show_text(
                "Synopsis",
                st.session_state.get("novel_synopsis", ""),
                "No synopsis provided."
            )


            # =================================================
            # READING PREFERENCES
            # =================================================

            st.markdown(
                '<div class="preview-section-title">Your Reading Preferences</div>',
                unsafe_allow_html=True
            )

            # -------------------------------------------------
            # Genres
            # -------------------------------------------------

            st.markdown("### Favorite Genres")

            show_list(
                "Genres You Enjoy",
                st.session_state.get("enjoyed_genres", [])
            )

            show_list(
                "Genres You Prefer to Avoid",
                st.session_state.get("disliked_genres", [])
            )

            # -------------------------------------------------
            # Character Preferences
            # -------------------------------------------------

            st.markdown("### Character Preferences")

            show_list(
                "Character Traits You Enjoy",
                st.session_state.get("enjoyed_character", [])
            )

            show_text(
                "Describe a Character You Like",
                st.session_state.get("liked_character", "")
            )

            show_text(
                "Describe Traits You Dislike",
                st.session_state.get("disliked_character", "")
            )

            # -------------------------------------------------
            # Story Preferences
            # -------------------------------------------------

            st.markdown("### Story Preferences")

            show_list(
                "Story Elements You Enjoy",
                st.session_state.get("enjoyed_story", [])
            )

            show_list(
                "Story Elements You Prefer to Avoid",
                st.session_state.get("disliked_story", [])
            )

            st.divider()

            # =================================================
            # BUTTONS
            # =================================================

            back_col, continue_col = st.columns(2)

            with back_col:

                if st.button(
                    "← Back to Novel",
                    use_container_width=True,
                    key="preview_back"
                ):
                    st.switch_page("pages/novel.py")

            with continue_col:

                if st.button(
                    "Continue →",
                    type="primary",
                    use_container_width=True,
                    key="preview_continue"
                ):
                    st.session_state["analysis_complete"] = False
                    st.session_state["analysis_error"] = False
                    st.session_state["analysis_started"] = False
                    st.session_state.pop("analysis_result", None)
                    st.switch_page("pages/loading.py")