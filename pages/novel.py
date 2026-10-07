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

if "novel_synopsi " not in st.session_state:
    st.session_state.novel_synopsis = ""


# =========================================================
# Main Layout
# =========================================================

with st.container(key="novel-content"):

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
                    About the Novel
                </h1>

                <div class="novel-description">
                    Enter the title and author of the novel
                    you're interested in.
                </div>

                <div class="novel-step">
                    2/2 Step
                </div>
            """,
            unsafe_allow_html=True
        )


    # =====================================================
    # Right - Preference Form
    # =====================================================
    with col2:
        with st.container(
            border=True,
            key="novel-card"
        ):


            st.markdown("### Novel Title")
            novel_title = st.text_input(
                "Novel Title",
                value=st.session_state.novel_title,
                placeholder="Enter novel title...",
                key="novel_title_input",
                label_visibility="collapsed"
            )

            st.session_state.novel_title = novel_title


            st.markdown("### Author")
            novel_author = st.text_input(
                "Author",
                value=st.session_state.novel_author,
                placeholder="Enter author name...",
                key="novel_author_input",
                label_visibility="collapsed"
            )

            st.session_state.novel_author = novel_author

            st.markdown("### Synopsis (Optional)")
            novel_synopsis = st.text_area(
                "synosis",
                value=st.session_state.novel_synopsis,
                placeholder="Enter sysnosi....",
                key="novel_synopsis_input",
                label_visibility="collapsed"
            )

            st.session_state.novel_synopsis = novel_synopsis


            # =================================================
            # Next
            # =================================================

            st.divider()

            col1, col2 = st.columns(2)

            with col1:

                back_clicked = st.button(
                    "← Back to Preferences",
                    use_container_width=True,
                    key="back_preferences",
                )


            with col2:

                next_clicked = st.button(
                    "Next →",
                    type="primary",
                    use_container_width=True,
                    key="novel_next",
                )

            if back_clicked:
                st.switch_page(
                    "pages/preferences.py"
                )

            if next_clicked:

                if not novel_title.strip():
                    st.warning("Please enter the novel title.")

                elif not novel_author.strip():
                    st.warning("Please enter the author.")

                else:

                    st.session_state.novel_completed = True

                    st.switch_page(
                        "pages/preview.py"
                    )