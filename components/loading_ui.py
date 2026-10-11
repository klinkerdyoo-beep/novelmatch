import streamlit as st

STEPS = [
    {
        "title": "Understanding You",
        "description": "Reading your preferences and favorite genres...",
    },
    {
        "title": "Exploring the Novel",
        "description": "Analyzing the book's details and characteristics...",
    },
    {
        "title": "Comparing & Matching",
        "description": "Comparing the story with your preferences...",
    },
    {
        "title": "Preparing Your Results",
        "description": "Preparing your personalized match analysis...",
    },
]


def render_loading_header():
    st.markdown(
        """
        <div class="loading-brand">
            <div class="loading-brand-name">
                Novel<span>Match</span>
            </div>
            <div class="loading-brand-caption">
                YOUR PERSONALIZED READING GUIDE
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="loading-hero">
            <h1>Finding Your Novel Match...</h1>
            <p>
                Every story is different. Let's find the one
                that feels right for you.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_loading_steps(current_step, progress, message):
    with st.container(border=True):
        for index, step in enumerate(STEPS):
            if index < current_step:
                icon = "✓"
                status = "Done"
            elif index == current_step:
                icon = "↻"
                status = "Working"
            else:
                icon = "○"
                status = "Pending"

            col1, col2, col3 = st.columns([0.12, 0.68, 0.20])

            with col1:
                if index < current_step:
                    st.markdown(f"### :green[{icon}]")
                elif index == current_step:
                    st.markdown(f"### :green[{icon}]")
                else:
                    st.markdown(f"### :gray[{icon}]")

            with col2:
                st.markdown(f"**{step['title']}**")
                st.caption(step["description"])

            with col3:
                st.caption(status)

            if index < len(STEPS) - 1:
                st.divider()

        st.progress(
            max(0, min(100, progress)) / 100,
            text=f"{message} {progress}%",
        )

    st.caption(
        "✦ This may take a little while. "
        "We're putting the pieces together."
    )