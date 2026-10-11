
import streamlit as st
import base64

from components.navbar import navbar
from components.popup.novel_not_found_popup import (
    novel_not_found_popup
)


# =========================================================
# Page Config
# =========================================================

st.set_page_config(
    page_title="Test Novel Popup | Novel Match",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

css_files = [
    "style/global.css",
    "style/navbar.css",
    "style/form.css",
    "style/popup.css",
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
            background-image:
                url("data:image/png;base64,{hero_bg}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# Test Page
# =========================================================

with st.container(key="novel-content"):

    st.title("Novel Popup Testing")

    st.markdown(
        """
        Use this page to preview and test the
        Novel Not Found popup before integrating it
        into the main novel form.
        """
    )

    st.divider()

    st.markdown("### Test Scenario")

    test_novel_title = st.text_input(
        "Novel Title",
        value="Example Novel",
        placeholder="Enter a novel title...",
        key="test-novel-title",
    )

    st.caption(
        "Simulate a case where the novel cannot be found "
        "in the available sources."
    )

    if st.button(
        "Preview Novel Not Found Popup",
        type="primary",
        use_container_width=True,
        key="preview-novel-popup",
    ):
        st.session_state["test_novel_popup_title"] = (
            test_novel_title.strip()
        )
        st.session_state["show_test_novel_popup"] = True

    if st.button(
        "Reset Test",
        use_container_width=True,
        key="reset-novel-popup-test",
    ):
        st.session_state["show_test_novel_popup"] = False
        st.session_state["test_novel_popup_title"] = ""
        st.rerun()


# =========================================================
# Show Popup
# =========================================================

if st.session_state.get("show_test_novel_popup", False):

    novel_not_found_popup(
        novel_title=st.session_state.get(
            "test_novel_popup_title",
            ""
        )
    )
