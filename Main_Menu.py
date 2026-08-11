import streamlit as st
import subprocess

subprocess.run(["playwright", "install"], check=True)

st.set_page_config(
    page_title="Hello",
    page_icon="👋",
)

st.write("# Welcome to the Automation Hub!")


file = open("README.md", "r")
readme = file.readlines()
file.close()

programs = readme[3:]

for elem in programs:
    st.markdown(elem.strip("\n"))
