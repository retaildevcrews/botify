import ast  # Remove this import as it is no longer needed
import json
from typing import List

from streamlit_app import api_url
from streamlit_app.helpers.streamlit_helpers import consume_api, get_logger

logger = get_logger(__name__)


def parse_document_string(document_string):
    document_list = []
    try:
        # Remove the surrounding brackets and split the string into individual document strings
        document_string.strip("[]")
        document_entries = document_string.split("Document(")[1:]
        for entry in document_entries:
            entry = "Document(" + entry
            # Extract metadata and page_content
            metadata_str = entry.split("metadata=")[1].split(", page_content=")[0].strip()
            page_content_str = entry.split("page_content=")[1].rsplit(")", 1)[0].strip()
            # Convert the strings to dictionaries
            metadata = json.loads(metadata_str)
            # Value in lanchain response is a string that has to be converted to a dictionary
            # this required two ast.literal_eval calls
            page_content = ast.literal_eval(page_content_str)
            page_content = ast.literal_eval(page_content)
            # Create Document object and append to list
            document = {"metadata": metadata, "page_content": page_content}
            document_list.append(document)
    except Exception as e:
        logger.error(f"Error parsing document string: {e}")
    return document_list


def extract_intermediate_steps(messages):

    document_list = []
    called_tools = []
    for message in messages:
        if message["type"] == "tool" and "Document" in message["content"]:
            logger.info(f"Tooooool message: {message}")
            try:
                document_list_str = message["content"]
                document_list = parse_document_string(document_list_str)
            except Exception as e:
                logger.error(f"Failed to parse document: {e}")
        if "tool_calls" in message:
            try:
                tool_calls = message["tool_calls"]
                for call in tool_calls:
                    print(f"call: {call}")
                    tool_call = {"name": call["name"], "args": call["args"]}
                    called_tools.append(tool_call)
            except Exception as e:
                logger.error(f"Failed to parse document: {e}")
    return {"documents": document_list, "tool_calls": called_tools}


def parse_response(response):
    logger.error(f"WAAAAAAAT: {str(response.json())}")
    messages = response["messages"]
    intermediate_steps = extract_intermediate_steps(messages)
    parsed_response = {"answer": None, "called_tools": [], "search_documents": [], "question": None}
    answer = messages[-1]["content"]
    parsed_response["answer"] = answer
    question = messages[0]["content"]
    parsed_response["question"] = question
    parsed_response["search_documents"] = intermediate_steps["documents"]
    parsed_response["called_tools"] = intermediate_steps["tool_calls"]
    return parsed_response


def process_input(question, session_id, user_id):
    response = consume_api(api_url, question, session_id, user_id)
    logger.error(f"Response: {str(response)}")
    parsed_response = parse_response(response)
    return parsed_response
