import streamlit as st


@st.dialog("We Couldn't Find Your Novel")
def novel_not_found_popup(novel_title=""):

    st.markdown(
        """
        <div class="login-required-description">
            We couldn't find this novel in our available
            sources. Please provide a synopsis so we can
            better understand the story and analyze its match
            with your reading preferences.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    st.text_input(
        "Novel Title",
        value=novel_title,
        disabled=True,
        key="not-found-novel-title"
    )

    synopsis = st.text_area(
        "Synopsis / Story Description",
        placeholder="Tell us what the story is about...",
        height=150,
        key="not-found-novel-synopsis"
    )

    if st.button(
        "Continue Analysis →",
        type="primary",
        use_container_width=True,
        key="continue-novel-analysis"
    ):
        if not synopsis.strip():
            st.warning("Please provide a synopsis first.")
        else:
            st.session_state["additional_novel_info"] = {
                "title": novel_title,
                "synopsis": synopsis.strip(),
            }

            # TODO: Send synopsis to the backend
            # and continue the novel analysis.

            st.success("Synopsis saved successfully.")