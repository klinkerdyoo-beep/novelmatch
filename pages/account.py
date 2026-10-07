
import streamlit as st
import base64

from components.navbar import navbar


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

username = st.session_state.get(
    "username",
    "User"
)

user_email = st.session_state.get(
    "user_email",
    ""
)


# =========================================================
# Page Content
# =========================================================

with st.container(key="preferences-content"):
    

    # =====================================================
    # Page Header
    # =====================================================

    st.markdown(
        f"""
        <h1>My<br>Account</h1>

        <div class="preferences-description">
            Manage your account and view your reading preferences.
        </div>
        """,
        unsafe_allow_html=True
    )


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


        # =================================================
        # Reading Preferences
        # =================================================

        st.markdown("### Reading Preferences")

        favorite_genres = st.session_state.get(
            "favorite_genres",
            []
        )

        disliked_genres = st.session_state.get(
            "disliked_genres",
            []
        )

        liked_characters = st.session_state.get(
            "liked_characters",
            []
        )

        disliked_characters = st.session_state.get(
            "disliked_characters",
            []
        )

        liked_stories = st.session_state.get(
            "liked_stories",
            []
        )

        disliked_stories = st.session_state.get(
            "disliked_stories",
            []
        )


        # =================================================
        # Genres
        # =================================================

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Genres You Enjoy**")

            if favorite_genres:
                st.write(", ".join(favorite_genres))
            else:
                st.caption("None selected.")

        with col2:
            st.markdown("**Genres You Don't Like**")

            if disliked_genres:
                st.write(", ".join(disliked_genres))
            else:
                st.caption("None selected.")


        # =================================================
        # Character Preferences
        # =================================================

        st.markdown("### Character Preferences")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Characters You Like**")

            if liked_characters:
                st.write(", ".join(liked_characters))
            else:
                st.caption("None selected.")

        with col2:
            st.markdown("**Characters You Don't Like**")

            if disliked_characters:
                st.write(", ".join(disliked_characters))
            else:
                st.caption("None selected.")


        # =================================================
        # Story Preferences
        # =================================================

        st.markdown("### Story Preferences")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Story Elements You Like**")

            if liked_stories:
                st.write(", ".join(liked_stories))
            else:
                st.caption("None selected.")

        with col2:
            st.markdown("**Story Elements You Don't Like**")

            if disliked_stories:
                st.write(", ".join(disliked_stories))
            else:
                st.caption("None selected.")


        # =================================================
        # Favorite Novels
        # =================================================

        st.markdown("### Favorite Novels")

        favorite_novels = st.session_state.get(
            "favorite_novels",
            []
        )

        favorite_novels = [
            novel
            for novel in favorite_novels
            if novel.get("title", "").strip()
        ]

        if favorite_novels:

            for i, novel in enumerate(
                favorite_novels,
                start=1
            ):

                title = novel.get(
                    "title",
                    ""
                ).strip()

                author = novel.get(
                    "author",
                    ""
                ).strip()

                synopsis = novel.get(
                    "synopsis",
                    ""
                ).strip()

                st.markdown(
                    f"**{i}. {title}**"
                )

                if author:
                    st.caption(
                        f"Author: {author}"
                    )

                if synopsis:
                    st.write(
                        synopsis
                    )

                st.divider()

        else:
            st.caption(
                "No favorite novels added yet."
            )


        # =================================================
        # Actions
        # =================================================

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "Edit Preferences",
                use_container_width=True,
                key="account-edit-preferences"
            ):
                st.switch_page(
                    "pages/preferences.py"
                )

        with col2:
            if st.button(
                "Back to Home",
                use_container_width=True,
                key="account-back-home"
            ):
                st.switch_page(
                    "main.py"
                )
