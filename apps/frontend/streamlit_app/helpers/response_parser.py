import ast
import json
import logging

from langchain_core.messages import AIMessage, ToolMessage
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Output(BaseModel):
    question: str
    called_tools: list = []
    search_documents: list = []
    answer: str


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
        logger.exception(f"Error parsing document string: {e}")
    return document_list


def extract_intermediate_steps(messages):
    document_list = []
    called_tools = []
    for message in messages:
        if isinstance(message, ToolMessage) and "Document" in message.content:
            try:
                document_list_str = message.content
                document_list = parse_document_string(document_list_str)
            except Exception as e:
                logger.exception(f"Failed to parse document: {e}")
        if isinstance(message, AIMessage) and hasattr(message, "tool_calls"):
            try:
                tool_calls = message.tool_calls
                for call in tool_calls:
                    tool_call = {"name": call["name"], "args": call["args"]}
                    called_tools.append(tool_call)
            except Exception as e:
                logger.exception(f"Failed to parse document: {e}")
    return {"documents": document_list, "tool_calls": called_tools}


def parse_response(response):
    logger.debug(f"Response inside parse response: {response}")
    messages = response["messages"]
    question = messages[0].content
    answer = messages[-1].content
    intermediate_steps = extract_intermediate_steps(messages)
    parsed_response = Output(
        question=question,
        search_documents=intermediate_steps["documents"],
        called_tools=intermediate_steps["tool_calls"],
        answer=answer,
    ).model_dump()
    search_docs = intermediate_steps["documents"]
    searchdict = {}
    for i in range(len(search_docs)):
        search_res = []
        link = search_docs[i]["page_content"]["link"]
        text = search_docs[i]["page_content"]["text"]
        search_res.append(link)
        search_res.append(text)
        searchdict[i + 1] = search_res
    logger.info("Search Results", searchdict)
    return parsed_response
