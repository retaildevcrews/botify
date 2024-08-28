import json
import uuid
import re
import requests
import toml
import _additional_version_info
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from app import api_key
from app import api_url_version

def get_logger(name):
    from streamlit.logger import get_logger
    return get_logger(name)

logger = get_logger(__name__)

def configure_page(title, icon):
    """Configure the Streamlit page settings."""
    set_page_config(title, icon)
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 1rem;
                padding-bottom: 0rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

def set_page_config(title, icon):

    frontend_version, backend_version = get_versions()
    st.set_page_config(page_title=title,
                       page_icon=icon,
                       layout="wide",
                       menu_items={
                            'about': f'''**Front-End Version:** {frontend_version}\n\n**Back-End Version:** {backend_version}'''
                        }
    )

def get_versions():
    # Load the pyproject.toml file
    pyproject = toml.load("pyproject.toml")

    # Extract the version, short_sha, and build_timestamp
    version = pyproject.get("tool", {}).get("poetry", {}).get("version", "Version not found")

    if  _additional_version_info.__short_sha__ and _additional_version_info.__build_timestamp__:
        version = version + "-" + _additional_version_info.__short_sha__ + "-" + _additional_version_info.__build_timestamp__


    backend_version = _private_get_api_version(api_url_version)
    return version, backend_version

def get_or_create_ids():
    """Generate or retrieve session and user IDs."""
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
        logger.info("Created new session_id: %s", st.session_state["session_id"])
    else:
        logger.info("Found existing session_id: %s", st.session_state["session_id"])

    if "user_id" not in st.session_state:
        st.session_state["user_id"] = str(uuid.uuid4())
        logger.info("Created new user_id: %s", st.session_state["user_id"])
    else:
        logger.info("Found existing user_id: %s", st.session_state["user_id"])

    return st.session_state["session_id"], st.session_state["user_id"]

def consume_api(url, user_query, session_id, user_id):
    """Send a POST request to the FastAPI backend and handle streaming responses."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Ocp-Apim-Subscription-Key"] = f"{api_key}"
    config = {"configurable": {"session_id": session_id, "user_id": user_id}}
    payload = {"input": {"question": user_query}, "config": config}

    logger.info(
        "Sending API request to %s with session_id: %s and user_id: %s",
        url,
        session_id,
        user_id,
    )
    logger.debug("Payload: %s", payload)

    with requests.post(url, json=payload, headers=headers, stream=True) as response:
        try:
            response.raise_for_status()  # Raises an HTTPError if the response is not 200.
            logger.info("Received streaming response from API.")
            for line in response.iter_lines():
                if line:  # Check if the line is not empty.
                    decoded_line = line.decode("utf-8")
                    logger.debug("Received line: %s", decoded_line)
                    if decoded_line.startswith("data: "):
                        # Extract JSON data following 'data: '.
                        json_data = decoded_line[len("data: ") :]
                        try:
                            data = json.loads(json_data)
                            if "event" in data:
                                event_type = data["event"]
                                logger.debug("Event type: %s", event_type)
                                if event_type == "on_chat_model_stream":
                                    content = data["data"]["chunk"]["content"]
                                    if content:  # Ensure content is not None or empty.
                                        yield content  # Yield content with paragraph breaks.
                                elif event_type == "on_tool_start" or event_type == "on_tool_end":
                                    pass
                            elif "content" in data:
                                # Yield immediate content with added Markdown for line breaks.
                                yield f"{data['content']}\n\n"
                            elif "steps" in data:
                                yield f"{data['steps']}\n\n"
                            elif "output" in data:
                                yield f"{data['output']}\n\n"
                        except json.JSONDecodeError as e:
                            logger.error("JSON decoding error: %s", e)
                            yield f"JSON decoding error: {e}\n\n"
                    # Decoding if using invoke endpoint
                    elif decoded_line.startswith("{\"output\":"):
                        json_data = json.loads(decoded_line)
                        yield f"{json_data['output']['output']}\n\n"
                    elif decoded_line.startswith("event: "):
                        pass
                    elif ": ping" in decoded_line:
                        pass
                    else:
                        yield f"{decoded_line}\n\n"  # Adding line breaks for plain text lines.
        except requests.exceptions.HTTPError as err:
            logger.error("HTTP Error: %s", err)
            yield f"HTTP Error: {err}\n\n"
        except Exception as e:
            logger.error("An error occurred: %s", e)
            yield f"An error occurred: {e}\n\n"


def _private_get_api_version(url):
    """Send a GET request to the API and retrieve the version."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Ocp-Apim-Subscription-Key"] = f"{api_key}"

    logger.info(
        "Sending API request to %s",
        url
    )
    logger.debug("url: %s", url)
    with requests.get(url, headers=headers) as response:
        try:
            response.raise_for_status()  # Raises an HTTPError if the response is not 200.
            logger.info("Received response from API.")
            data = response.json()
            version = data.get("version")
            return version
        except requests.exceptions.HTTPError as err:
            logger.error("HTTP Error while retrieving API version: %s", err)
            return None
        except Exception as e:
            logger.error("An error occurred while retrieving API version: %s", e)
            return None


def initialize_chat_history(model):
    """Initialize the chat history with a welcome message from the AI model."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            AIMessage(
                content=f"Hello, I am a {model} bot using FastAPI Streaming. How can I help you?"
            )
        ]
        logger.info("Chat history initialized with model: %s", model)
    else:
        logger.info("Found existing chat history with model: %s", model)

def display_chat_history():
    """Display the chat history in Streamlit."""
    for message in st.session_state.chat_history:
        if isinstance(message, AIMessage):
            with st.chat_message("AI"):
                st.write(message.content)
            logger.debug("Displayed AI message: %s", message.content)
        elif isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                st.write(message.content)
            logger.debug("Displayed Human message: %s", message.content)

def extract_voice_summary_and_text(input_string):
    # Define the pattern to match the text inside the voice_summary and the rest of the text
    pattern = r'\{\s*"?voice_summary"?\s*:\s*"(.*?)"\s*\}([\s\S]*)'

    # Use regex to find the matches
    match = re.match(pattern, input_string, re.DOTALL)

    if match:
        voice_summary = match.group(1)
        text = match.group(2)
        return voice_summary, text
    else:
        logger.warning("No match found for pattern with input: %s", repr(input_string))
        return None, None
