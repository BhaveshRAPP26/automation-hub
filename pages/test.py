import streamlit as st

st.sidebar.title("🤖 Automation Hub")

with st.sidebar.expander("📊 Analytics", expanded=True):
    if st.button("Checkem"):
        st.session_state.page = "Checkem"

    if st.button("HTML ID Scraper"):
        st.session_state.page = "id_scraper"

with st.sidebar.expander("🔍 Validation"):
    if st.button("URL Validator"):
        st.session_state.page = "url_validator"

    if st.button("Redirect Checker"):
        st.session_state.page = "redirect_checker"

with st.sidebar.expander("⚙️ Utilities"):
    if st.button("Regex Generator"):
        st.session_state.page = "regex"