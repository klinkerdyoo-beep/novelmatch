import streamlit as st
import base64

from components.navbar import navbar


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

if "favorite_novels" not in st.session_state:
    st.session_state.favorite_novels = [""] * 5

if "liked_characters" not in st.session_state:
    st.session_state.liked_characters = []

if "disliked_characters" not in st.session_state:
    st.session_state.disliked_characters = []

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
# Page Header
# =========================================================

with st.container(key="preferences-content"):

    st.markdown(
        """
            <h1> Tell Us<br>About You</h1>
            <div class="preferences-description"> "Tell us about your reading preferences so we can find novels that match you."</div>
            <div class="preferences-step"> 1/2 Step </div>
        """,
        unsafe_allow_html=True
    )
# =========================================================
# Preference Form
# =========================================================

    with st.container(
        border=True,
        key="preferences-card"
    ):


        # =====================================================
        # Favorite Genres
        # =====================================================

        st.markdown("### Favorite Genres")

        favorite_genres = st.multiselect(
            "Genres You Enjoy",
            options=genres,
            default=st.session_state.favorite_genres,
            placeholder="Select genres...",
        )

        st.session_state.favorite_genres = favorite_genres


        # =====================================================
        # Disliked Genres
        # =====================================================

        disliked_genres = st.multiselect(
            "Genres You Don't Like",
            options=genres,
            default=st.session_state.disliked_genres,
            placeholder="Select genres...",
        )

        st.session_state.disliked_genres = disliked_genres

        # =====================================================
        # Favorite Novels
        # =====================================================

        st.markdown("### Favorite Novels")

        novels = []

        for i in range(len(st.session_state.favorite_novels)):

            novel = st.text_input(
                f"Novel {i + 1}",
                value=st.session_state.favorite_novels[i],
                placeholder="Enter novel title...",
                key=f"favorite_novel_{i}",
            )

            novels.append(novel)

        st.session_state.favorite_novels = novels


        # =====================================================
        # Add Another Novel
        # =====================================================

        if len(st.session_state.favorite_novels) < 10:

            if st.button(
                "+ Add another novel",
                key="add_favorite_novel",
            ):
                st.session_state.favorite_novels.append("")
                st.rerun()


        # =====================================================
        # Character Preferences
        # =====================================================

        st.markdown("### Character Preferences")

        liked_characters = st.multiselect(
            "Characters You Like",
            options=characters,
            default=st.session_state.liked_characters,
            placeholder="Select character traits...",
        )

        st.session_state.liked_characters = liked_characters


        disliked_characters = st.multiselect(
            "Characters You Don't Like",
            options=characters,
            default=st.session_state.disliked_characters,
            placeholder="Select character traits...",
        )

        st.session_state.disliked_characters = disliked_characters


        # =====================================================
        # Story Preferences
        # =====================================================

        st.markdown("### Story Preferences")

        liked_stories = st.multiselect(
            "Story Elements You Like",
            options=story_preferences,
            default=st.session_state.liked_stories,
            placeholder="Select story preferences...",
        )

        st.session_state.liked_stories = liked_stories


        disliked_stories = st.multiselect(
            "Story Elements You Don't Like",
            options=story_preferences,
            default=st.session_state.disliked_stories,
            placeholder="Select story preferences...",
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