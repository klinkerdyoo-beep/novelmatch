import streamlit as st
import base64

from components.navbar import navbar
from components.popup.login_required_popup import login_required_popup


# =========================================================
# Page Config
# =========================================================

st.set_page_config(
    page_title="Tell Us About You",
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
# Session State
# =========================================================

if "favorite_genres" not in st.session_state:
    st.session_state.favorite_genres = []

if "disliked_genres" not in st.session_state:
    st.session_state.disliked_genres = []

if "liked_characters" not in st.session_state:
    st.session_state.liked_characters = ""

if "enjoy_characters" not in st.session_state:
    st.session_state.enjoy_characters = []

if "disliked_character_description" not in st.session_state:
    st.session_state.disliked_character_description = ""

if "liked_stories" not in st.session_state:
    st.session_state.liked_stories = []

if "disliked_stories" not in st.session_state:
    st.session_state.disliked_stories = []


# =========================================================
# Data
# =========================================================

genres = [
    "Romance",
    "Fantasy",
    "Mystery",
    "Action",
    "Adventure",
    "Comedy",
    "Drama",
    "Horror",
    "Science Fiction",
    "Thriller",
    "Historical",
    "Young Adult",
]

characters = [
    "Intelligent",
    "Funny",
    "Strong",
    "Kind",
    "Brave",
    "Clever",
    "Mysterious",
    "Independent",
    "Calm",
    "Confident",
]

story_preferences = [
    "Fast-paced",
    "Slow-paced",
    "Complex story",
    "Simple story",
    "Plot-driven",
    "Character-driven",
    "Emotional",
    "Light-hearted",
    "Unexpected twists",
]


# =========================================================
# Main Layout
# =========================================================

with st.container(key="preferences-content"):

    col1, col2 = st.columns(
        [0.4, 1.6],
        gap="large"
    )

    # =========================================================
    # Left - Introduction
    # =========================================================
    with col1:

        st.markdown(
            """
                <h1>
                    Tell Us<br>
                    About You
                </h1>

                <div class="preferences-description">
                    Tell us about your reading preferences
                    so we can find novels that match you.
                </div>

                <div class="preferences-step">
                    1/3 Step
                </div>
            """,
            unsafe_allow_html=True
        )

    # =========================================================
    # Right - Preference Form
    # =========================================================

    with col2:

        with st.container(
            border=True,
            key="preferences-card"
        ):
            st.markdown(
                '<p class="preferences-eyebrow">LET\'S GET TO KNOW YOU</p>',
                unsafe_allow_html=True
            )
            st.markdown("### Your Reading Profile")
            st.markdown("There are no right or wrong answers.Just tell us what you enjoy.")
            st.markdown("---")


            # =====================================================
            # Favorite Genres
            # =====================================================

            st.markdown("### Favorite Genres")
            st.markdown("Which genres do you enjoy reading?")

            st.markdown("#### Which genres do you enjoy?")
            st.caption("Select the genres you enjoy reading the most.")
            favorite_genres = st.multiselect(
                "Favorite Genres",
                options=genres,
                default=st.session_state.favorite_genres,
                placeholder="Select genres...",
                label_visibility="collapsed",
                key="favorite_genres_select",
            )

            st.session_state.favorite_genres = favorite_genres

            st.markdown("#### Which genres do you prefer to avoid?")
            st.caption("Select the genres you usually don't enjoy reading.")
            disliked_genres = st.multiselect(
                "Disliked Genres",
                options=genres,
                default=st.session_state.disliked_genres,
                placeholder="Select genres...",
                label_visibility="collapsed",
                key="disliked_genres_select",
            )

            st.session_state.disliked_genres = disliked_genres

            st.write("")
            # =====================================================
            # Character Preferences
            # =====================================================

            st.markdown("### Character Preferences")
            st.markdown("Tell us about the personalities that appeal to you.")

            st.markdown("#### What personality traits do you like in a character?")
            st.caption("Select the personality traits you enjoy in a character.")
            enjoy_characters = st.multiselect(
                "Liked Character Traits",
                options=characters,
                default=st.session_state.enjoy_characters,
                placeholder="Select character traits...",
                label_visibility="collapsed",
                key="enjoy_characters_select",
            )

            st.session_state.enjoy_characters = enjoy_characters    

            # Question 2: Ideal Character
            st.markdown("#### What do you like about a character?")
            st.caption("Describe the personality, behavior, or character development you enjoy.")
            liked_characters  = st.text_area(
                "Liked Character Description",
                placeholder="Describe a character you enjoy reading about...",
                height=100,
                label_visibility="collapsed",
                key="liked_characters ",
            )


            # Question 3: Disliked Character Traits
            st.markdown("#### What character traits or behaviors do you dislike?")
            st.caption("Describe the traits or behaviors that make you less interested in a character.")

            disliked_character_description = st.text_area(
                "Disliked Character Traits",
                placeholder="Describe character traits you dislike...",
                height=100,
                label_visibility="collapsed",
                key="disliked_character_description",
            )

            st.write("")
            # =====================================================
            # Story Preferences
            # =====================================================

            st.markdown("### Story Preferences")
            st.markdown("Tell us what makes a story enjoyable for you.")

            
            st.markdown("#### What do you enjoy in a story?")
            st.caption("Select the storytelling styles and elements you enjoy reading.")
            liked_stories = st.multiselect(
                "Story Elements You Like",
                options=story_preferences,
                default=st.session_state.liked_stories,
                placeholder="Select story preferences...",
                label_visibility="collapsed",
                key="liked_stories_select",
            )

            st.session_state.liked_stories = liked_stories

            st.markdown("#### What do you prefer to avoid in a story?")
            st.caption("Select the storytelling styles and elements you usually don't enjoy.")
            disliked_stories = st.multiselect(
                "Story Elements You Don't Like",
                options=story_preferences,
                default=st.session_state.disliked_stories,
                placeholder="Select story preferences...",
                label_visibility="collapsed",
                key="disliked_stories_select",
            )

            st.session_state.disliked_stories = disliked_stories


            # =====================================================
            # Complete
            # =====================================================

            st.divider()

            if st.button(
                "Complete →",
                type="primary",
                use_container_width=True,
            ):

                st.session_state.preferences_completed = True

                st.switch_page(
                    "pages/novel.py"
                )

if not st.session_state.get("logged_in", False):
    login_required_popup()