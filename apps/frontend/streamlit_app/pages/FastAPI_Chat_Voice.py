import os

import streamlit as st
from audio_recorder_streamlit import audio_recorder
from helpers.json_helpers import generate_display_and_audio_response
from helpers.speech_helpers import handle_audio_response
from helpers.speech_helpers import speech_to_text_from_bytes as speech_to_text
from helpers.streamlit_helpers import (configure_page, consume_api,
                                       display_chat_history, get_logger,
                                       get_or_create_ids,
                                       initialize_chat_history)
from langchain_core.messages import AIMessage, HumanMessage
from streamlit_app import api_url, model_name
from streamlit_float import float_init

# Configure the Streamlit page
configure_page("FastAPI Voice Bot", "🤖")
logger = get_logger(__name__)
logger.info("Page configured with title 'FastAPI Voice Bot'.")

# Initialize session and user IDs
session_id, user_id = get_or_create_ids()

# Initialize floating elements and chat history
float_init()
logger.debug("Floating elements initialized.")
initialize_chat_history(model_name)

# Create footer container for the microphone
footer_container = st.container()
with footer_container:
    audio_bytes = audio_recorder(sample_rate=16000)
    if audio_bytes:
        logger.info("Audio recorded.")

# Display chat history
display_chat_history()
logger.debug("Chat history displayed.")


def write_payload(payload):
    result = ""
    container = st.empty()

    if "invoke" in api_url:
        json = next(iter(payload), None)
        if json:
            result = generate_display_and_audio_response(json, True)
            container.markdown(result)
            return result
    else:
        for chunk in payload:
            result += chunk
            container.markdown(result)
        handle_audio_response(result)
        return result


# Handle audio input and transcription
if audio_bytes:
    with st.spinner("Transcribing..."):
        transcript = speech_to_text(audio_bytes)
        logger.debug(f"Transcript: {transcript}")
        if transcript:
            st.session_state.chat_history.append(
                HumanMessage(content=transcript))
            with st.chat_message("Human"):
                st.write(transcript)
            logger.info("Transcript added to chat history.")

# Generate and display AI response if the last message is not from the AI
if not isinstance(st.session_state.chat_history[-1], AIMessage):
    with st.chat_message("AI"):
        with st.spinner("Thinking🤔..."):
            try:
                ai_response = write_payload(
                    payload=consume_api(
                        api_url,
                        st.session_state.chat_history[-1].content,
                        session_id,
                        user_id,
                    )
                )
                logger.info("AI response received and written to stream.")
            except Exception as e:
                logger.error(f"Error consuming API: {e}")
                st.error("Failed to get a response from the AI.")
                ai_response = None

        if ai_response:
            st.session_state.chat_history.append(
                AIMessage(content=ai_response))

# Ensure the footer container floats at the bottom
footer_container.float("bottom: 0rem;")
