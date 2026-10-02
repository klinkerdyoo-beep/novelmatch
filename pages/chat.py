import streamlit as st
import base64

from components.navbar import navbar


# =========================================================
# Page Config
# =========================================================

st.set_page_config(
    page_title="Novel Match",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

css_files = [
    "style/global.css",
    "style/navbar.css",
    "style/form.css",
    "style/chat.css",
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
# Get Data
# =========================================================

novel_title = st.session_state.get(
    "novel_title",
    "The Seven Husbands of Evelyn Hugo"
)

novel_author = st.session_state.get(
    "novel_author",
    "Taylor Jenkins Reid"
)

novel_synopsis = st.session_state.get(
    "novel_synopsis",
    ""
)

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


# =========================================================
# Demo Match Result
# =========================================================

match_score = 86


# =========================================================
# Page Header
# =========================================================

with st.container(key="result-content"):

    st.markdown(
        """
        <h1>Novel Match</h1>

        <div class="result-description">
            Here's how well this novel matches your reading preferences.
        </div>
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # Main Layout
    # =====================================================

    col_left, col_right = st.columns(
        [1, 1],
        gap="large"
    )


    # =====================================================
    # LEFT
    # =====================================================

    with col_left:

        # -------------------------------------------------
        # Match Card
        # -------------------------------------------------

        with st.container(
            border=True,
            key="match-card"
        ):

            st.markdown(
                f"""
                <div class="match-title">
                    {novel_title}
                </div>

                <div class="match-author">
                    {novel_author}
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("---")

            st.html(
                f"""
                <div class="match-score-wrapper">

                    <div
                        class="match-score-circle"
                        style="--score: {match_score * 3.6}deg;"
                    >
                        <div class="match-score-inner">

                            <div class="match-score-number">
                                {match_score}
                            </div>

                            <div class="match-score-label">
                                / 100
                            </div>

                        </div>
                    </div>

                    <div class="match-score-text">
                        YOUR MATCH
                    </div>

                </div>
                """
            )

            if match_score >= 80:
                match_status = "Great Match"
            elif match_score >= 60:
                match_status = "Good Match"
            else:
                match_status = "Low Match"

            st.markdown(
                f"""
                <div class="match-status">
                    {match_status}
                </div>
                """,
                unsafe_allow_html=True
            )


        # -------------------------------------------------
        # How Result Was Reached
        # -------------------------------------------------

        with st.container(
            border=True,
            key="source-card"
        ):

            st.markdown("### How We Reached This Result")

            st.write("Novel Information")

            st.write("↗ Google Books")
            st.write("↗ Open Library")
            st.write("↗ Reader Reviews")


    # =====================================================
    # RIGHT
    # =====================================================

    with col_right:

        # -------------------------------------------------
        # Why It Matches
        # -------------------------------------------------

        with st.container(
            border=True,
            key="match-reason-card"
        ):

            st.markdown("### Why It Matches You")

            st.write(
                "✓ Fantasy & Romance matches your favorite genres"
            )

            st.write(
                "✓ Strong Female Lead matches your character preferences"
            )

            st.write(
                "✓ Mysterious atmosphere matches your preferred story mood"
            )


        # -------------------------------------------------
        # Things You May Not Like
        # -------------------------------------------------

        with st.container(
            border=True,
            key="warning-card"
        ):

            st.markdown("### Things You May Not Like")

            st.write(
                "⚠ Slow pacing — some reviews mention "
                "that the story develops slowly."
            )

            st.write(
                "⚠ Loss-related themes — the story contains "
                "themes of loss."
            )


        # -------------------------------------------------
        # Match Breakdown
        # -------------------------------------------------

        with st.container(
            border=True,
            key="breakdown-card"
        ):

            st.markdown("### Match Breakdown")

            chart_data = {
                "Category": [
                    "Genre",
                    "Characters",
                    "Story",
                    "Overall"
                ],
                "Match": [
                    92,
                    88,
                    78,
                    86
                ]
            }

            st.bar_chart(
                chart_data,
                x="Category",
                y="Match",
                height=280
            )


        # -------------------------------------------------
        # Reader Insights
        # -------------------------------------------------

        with st.container(
            border=True,
            key="insight-card"
        ):

            st.markdown("### Reader Insights")

            st.markdown("#### Overall Review Summary")

            st.write(
                "Readers generally praised the characters "
                "and atmosphere, while some mentioned "
                "slower pacing."
            )

            st.markdown("#### Sources")

            st.caption(
                "Google Books · Open Library · Reader Reviews"
            )


# =========================================================
# Footer / Action
# =========================================================

st.divider()

if st.button(
    "← Back to Preview",
    use_container_width=True
):
    st.switch_page(
        "pages/preview.py"
    )