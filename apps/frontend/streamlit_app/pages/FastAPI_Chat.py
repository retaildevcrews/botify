import streamlit as st
from helpers.json_helpers import generate_display_and_audio_response
from helpers.streamlit_helpers import (
    configure_page,
    consume_api,
    display_chat_history,
    get_logger,
    get_or_create_ids,
    initialize_chat_history,
)
from langchain_core.messages import AIMessage, HumanMessage
from streamlit_app import api_url, model_name

# Configure the Streamlit page
configure_page("FastAPI Chat Bot", "🤖")
logger = get_logger(__name__)
logger.info("Page configured with title 'FastAPI Chat Bot'.")

# Initialize session and user IDs
session_id, user_id = get_or_create_ids()

# Initialize chat history
initialize_chat_history(model_name)

# Display chat history
display_chat_history()
logger.debug("Chat history displayed.")

# User input for chat
user_query = st.chat_input("Type your message here...")


def write_payload(payload):
    result = ""
    container = st.empty()
    answer = payload.json()
    if "invoke" in api_url:
        result = generate_display_and_audio_response(answer["output"], False)
        container.markdown(result)
        return result
    else:
        for chunk in payload:
            result += chunk
            container.markdown(result)
        return result


if user_query:
    logger.debug(f"User query received: {user_query}")
    st.session_state.chat_history.append(HumanMessage(content=user_query))

    with st.chat_message("Human"):
        st.markdown(user_query)
        logger.info("User query added to chat history and displayed.")

    with st.chat_message("AI"):
        try:
            ai_response = write_payload(payload=consume_api(api_url, user_query, session_id, user_id))
            logger.info("AI response received and written to stream.")
        except Exception as e:
            logger.error(f"Error consuming API: {e}")
            st.error("Failed to get a response from the AI.")
            ai_response = None

    if ai_response:
        st.session_state.chat_history.append(AIMessage(content=ai_response))
        logger.info("AI response added to chat history.")
