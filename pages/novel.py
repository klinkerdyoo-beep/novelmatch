import streamlit as st
import base64

from components.navbar import navbar



# =========================================================
# Page Config
# =========================================================

st.set_page_config(
    page_title="Tell Us About the Novel",
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

if "novel_title" not in st.session_state:
    st.session_state.novel_title = ""

if "novel_author" not in st.session_state:
    st.session_state.novel_author = ""

if "novel_synopsis" not in st.session_state:
    st.session_state.novel_synopsis = ""


# =========================================================
# Main Layout
# =========================================================

with st.container(key="novel-content"):

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
                Tell Us<br>
                About the Novel
            </h1>

            <div class="novel-description">
                Tell us which novel you're interested in so we can
                evaluate how well it matches your reading preferences.
            </div>

            <div class="novel-step">
                2/3 Step
            </div>
            """,
            unsafe_allow_html=True
        )


    # =====================================================
    # Right - Novel Form
    # =====================================================

    with col2:

        with st.container(
            border=True,
            key="novel-card"
        ):

            st.markdown(
                '<p class="preferences-eyebrow">LET\'S FIND YOUR NEXT READ</p>',
                unsafe_allow_html=True
            )

            st.markdown("### Tell Us About the Novel")
            st.markdown(
                "Enter a novel you're interested in, and we'll explore "
                "how well it matches your reading preferences."
            )

            st.markdown("---")

            # =================================================
            # Novel Title
            # =================================================

            st.markdown("### Novel Title")
            st.caption("Enter the title of the novel you want to evaluate.")

            novel_title = st.text_input(
                "Novel Title",
                value=st.session_state.novel_title,
                placeholder="Enter novel title...",
                label_visibility="collapsed",
                key="novel_title_input",
            )

            st.session_state.novel_title = novel_title


            # =================================================
            # Author
            # =================================================

            st.markdown("### Author")
            st.caption("Enter the name of the novel's author.")

            novel_author = st.text_input(
                "Author",
                value=st.session_state.novel_author,
                placeholder="Enter author name...",
                label_visibility="collapsed",
                key="novel_author_input",
            )

            st.session_state.novel_author = novel_author


            # =================================================
            # Synopsis (Optional)
            # =================================================

            st.markdown("### Synopsis (Optional)")
            st.caption(
                "Add a brief summary to help us identify the correct novel. "
                "You can leave this field blank if you don't have one."
            )

            novel_synopsis = st.text_area(
                "Novel Synopsis",
                value=st.session_state.novel_synopsis,
                placeholder="Enter a brief synopsis...",
                height=120,
                label_visibility="collapsed",
                key="novel_synopsis_input",
            )

            st.session_state.novel_synopsis = novel_synopsis


            # =================================================
            # Navigation
            # =================================================

            st.divider()

            back_col, next_col = st.columns(2)

            with back_col:

                back_clicked = st.button(
                    "← Back to Preferences",
                    use_container_width=True,
                    key="back_preferences",
                )

            with next_col:

                next_clicked = st.button(
                    "Next →",
                    type="primary",
                    use_container_width=True,
                    key="novel_next",
                )


            # =================================================
            # Navigation Actions
            # =================================================

            if back_clicked:
                st.switch_page("pages/preferences.py")

            if next_clicked:

                if not novel_title.strip():
                    st.warning("Please enter the novel title.")

                elif not novel_author.strip():
                    st.warning("Please enter the author's name.")

                else:
                    st.session_state.novel_completed = True

                    st.switch_page("pages/preview.py")