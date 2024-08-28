import json

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from helpers.speech_helpers import (
    handle_audio_response
)

def get_logger(name):
    from streamlit.logger import get_logger
    return get_logger(name)

logger = get_logger(__name__)

def generate_display_and_audio_response(json_str,play_voice_summary):
    # Load the JSON string into a Python dictionary
    data = json.loads(json_str)

    logger.debug(json_str)

    # Initialize the result string
    result = ""

    if play_voice_summary:
        voice_summary = data['voiceSummary']
        handle_audio_response(voice_summary)

    # Add the display response
    result += f"{data['displayResponse']}\n\n"

    return result
