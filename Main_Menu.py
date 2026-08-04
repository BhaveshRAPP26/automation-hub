import streamlit as st
import subprocess

subprocess.run(["playwright", "install"], check=True)

st.set_page_config(
    page_title="Hello",
    page_icon="👋",
)

st.write("# Welcome to the Automation Hub!")


st.markdown(
    """
    Please select a program that you want to execute, from the sidebar.
"""
)