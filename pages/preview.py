import streamlit as st
import base64

from components.navbar import navbar


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
# Preview Header
# =========================================================

with st.container(key="preview-content"):

    st.markdown(
        """
        <h1>
            Preview
        </h1>

        <div class="preview-description">
            Review your preferences and novel information
            before continuing.
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.container(
        border=True,
        key="preview-card"
    ):

        # =================================================
        # NOVEL INFORMATION
        # =================================================

        st.markdown("### Novel Information")

        st.markdown("#### Novel Title")

        st.write(
            st.session_state.get(
                "novel_title",
                "—"
            )
        )

        st.markdown("#### Author")

        st.write(
            st.session_state.get(
                "novel_author",
                "—"
            )
        )

        st.markdown("#### Synopsis")

        synopsis = st.session_state.get(
            "novel_synopsis",
            ""
        )

        if synopsis:
            st.write(synopsis)
        else:
            st.caption("No synopsis provided.")


        st.divider()


        # =================================================
        # READING PREFERENCES
        # =================================================

        st.markdown("### Reading Preferences")


        st.markdown("#### Favorite Genres")

        favorite_genres = st.session_state.get(
            "favorite_genres",
            []
        )

        if favorite_genres:
            st.write(", ".join(favorite_genres))
        else:
            st.caption("None selected.")


        st.markdown("#### Genres You Don't Like")

        disliked_genres = st.session_state.get(
            "disliked_genres",
            []
        )

        if disliked_genres:
            st.write(", ".join(disliked_genres))
        else:
            st.caption("None selected.")


        # =================================================
        # FAVORITE NOVELS
        # =================================================

        st.markdown("#### Favorite Novels")

        favorite_novels = st.session_state.get(
            "favorite_novels",
            []
        )

        favorite_novels = [
            novel
            for novel in favorite_novels
            if novel.strip()
        ]

        if favorite_novels:

            for novel in favorite_novels:
                st.write(f"• {novel}")

        else:
            st.caption("None provided.")


        # =================================================
        # CHARACTER
        # =================================================

        st.markdown("#### Characters You Like")

        liked_characters = st.session_state.get(
            "liked_characters",
            []
        )

        if liked_characters:
            st.write(", ".join(liked_characters))
        else:
            st.caption("None selected.")


        st.markdown("#### Characters You Don't Like")

        disliked_characters = st.session_state.get(
            "disliked_characters",
            []
        )

        if disliked_characters:
            st.write(", ".join(disliked_characters))
        else:
            st.caption("None selected.")


        # =================================================
        # STORY
        # =================================================

        st.markdown("#### Story Elements You Like")

        liked_stories = st.session_state.get(
            "liked_stories",
            []
        )

        if liked_stories:
            st.write(", ".join(liked_stories))
        else:
            st.caption("None selected.")


        st.markdown("#### Story Elements You Don't Like")

        disliked_stories = st.session_state.get(
            "disliked_stories",
            []
        )

        if disliked_stories:
            st.write(", ".join(disliked_stories))
        else:
            st.caption("None selected.")


        st.divider()


        # =================================================
        # BUTTONS
        # =================================================

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "← Back",
                use_container_width=True
            ):
                st.switch_page(
                    "pages/novel.py"
                )


        with col2:

            if st.button(
                "Continue →",
                type="primary",
                use_container_width=True
            ):
                st.switch_page(
                    "pages/chat.py"
                )