import streamlit as st
import base64

css_files = [
    "style/global.css",
    "style/navbar.css",
    "style/footer.css",
]

for css_file in css_files:
    with open(css_file, encoding="utf-8") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True
        )


def footer():

    

    with open("assets/footer-bg.png", "rb") as f:
        footer_bg = base64.b64encode(f.read()).decode()

    st.html(
        f"""
        <footer
            class="footer"
            style="
                background-image:
                    url('data:image/png;base64,{footer_bg}');
                background-size: cover;
                background-position: center;
            "
        >

            <div class="footer-content">

                <!-- Left -->
                <div class="footer-title">
                    <div class="footer-label">
                        NOVEL MATCH
                    </div>

                    <h1>
                        Project<br>
                        Members
                    </h1>

                    <p>
                        Designed & developed as a
                        NovelMatch project.
                    </p>
                </div>


                <!-- Right -->
                <div class="footer-members">

                    <div class="member">
                        <span class="member-number">01</span>

                        <div>
                            <div class="member-name">
                                Mr. Krittidet Tangwirun
                            </div>

                            <div class="member-id">
                                Student ID: 66070004
                            </div>
                        </div>
                    </div>


                    <div class="member">
                        <span class="member-number">02</span>

                        <div>
                            <div class="member-name">
                                Ms. Khema-apsorn Jantasare
                            </div>

                            <div class="member-id">
                                Student ID: 66070021
                            </div>
                        </div>
                    </div>


                    <div class="member">
                        <span class="member-number">03</span>

                        <div>
                            <div class="member-name">
                                Ms. Yanisa Koetyu
                            </div>

                            <div class="member-id">
                                Student ID: 66070052
                            </div>
                        </div>
                    </div>


                    <div class="member">
                        <span class="member-number">04</span>

                        <div>
                            <div class="member-name">
                                Ms. Klin Kerdyoo
                            </div>

                            <div class="member-id">
                                Student ID: 66070237
                            </div>
                        </div>
                    </div>

                </div>

            </div>


            <div class="footer-bottom">
                <span>NovelMatch</span>
                <span>© 2026</span>
            </div>

        </footer>
        """
    )