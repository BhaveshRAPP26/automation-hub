import streamlit as st
from ollama import chat

st.set_page_config(
    page_title="Automation Hub AI",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Automation Hub AI")
st.caption("Ask the Automation Hub what you want to accomplish.")

# Model
MODEL = "gemma4:26b"

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("What would you like to do?"):

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    # Send to Ollama
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):

            response = chat(
                model=MODEL,
                messages=st.session_state.messages
            )

            answer = response.message.content

        st.markdown(answer)

    # Save response
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })