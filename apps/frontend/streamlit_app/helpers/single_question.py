import ast  # Remove this import as it is no longer needed
import json
from typing import List

from streamlit_app import api_url
from streamlit_app.helpers.response_parser import parse_response
from streamlit_app.helpers.streamlit_helpers import consume_api, get_logger

logger = get_logger(__name__)


def process_input(question, session_id, user_id):
    response = consume_api(api_url, question, session_id, user_id)
    logger.error(f"Response: {str(response.json())}")
    parsed_response = parse_response(response)
    return parsed_response
