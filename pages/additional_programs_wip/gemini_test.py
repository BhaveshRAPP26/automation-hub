import os
import streamlit as st
from google import genai
from google.genai import types

# 1. Page Configuration
st.set_page_config(page_title="Gemini AI Chatbot", page_icon="💬", layout="centered")
st.title("💬 Chat with Gemini 2.0")
st.caption("A clean, conversational chat interface powered by Google Gemini and Streamlit.")

# 2. Initialize Gemini Client safely using Environment Variables
# The SDK automatically pulls from the GEMINI_API_KEY environment variable.

client = genai.Client(api_key="YOUR_GEMINI_API_KEY")  # Replace with your actual API key or ensure it's set in your environment variables.

# 3. Initialize Conversation History in Streamlit Session State
# This prevents the app from resetting the conversation on every rerun.
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. Display Existing Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Handle User Input
if user_prompt := st.chat_input("Ask Gemini anything..."):
    
    # Display user's message instantly
    with st.chat_message("user"):
        st.markdown(user_prompt)
    
    # Append user message to local history logs
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # Prepare historical context formatted specifically for the Gemini Client API
    formatted_contents = []
    for msg in st.session_state.messages:
        role_mapping = "user" if msg["role"] == "user" else "model"
        formatted_contents.append(
            types.Content(
                role=role_mapping,
                parts=[types.Part.from_text(text=msg["content"])]
            )
        )

    # 6. Generate Response from Gemini
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # Using the fast, efficient gemini-2.0-flash model with streaming active
            response_stream = client.models.generate_content_stream(
                model='gemini-3.6-flash',
                contents=formatted_contents,
            )
            
            # Stream the response chunk by chunk for a dynamic feel
            for chunk in response_stream:
                full_response += chunk.text
                response_placeholder.markdown(full_response + "▌")
                
            response_placeholder.markdown(full_response)
            
            # Save the final model response to the session history
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"An error occurred while communicating with Gemini: {e}")