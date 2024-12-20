import json
import uuid

import streamlit as st
from helpers.single_question import process_input
from helpers.streamlit_helpers import configure_page, get_logger
from streamlit_app import api_url

configure_page("Q&A Search", "🔍")
logger = get_logger(__name__)
logger.info("Page configured with title 'FastAPI Chat Bot'.")

session_id = str(uuid.uuid4())
user_id = str(uuid.uuid4())

# Input fields
question = st.text_input(
    "Type your message here...",
)

# Button to process input
if question:
    with st.spinner("Processing..."):
        response = process_input(question, session_id, user_id)
        with st.container(height=200):
            st.write(response["answer"])  # Input fields
        with st.container(border=False):
            st.write("Search Results:")
            documents = response["search_documents"]
            for document in documents:
                output = f"""
                [{document["page_content"]["short_description"]}]({document["page_content"]["link"]})\n
                {document["page_content"]["@search.captions"][0]["text"]}\n
                \n
                """
                st.write(output)
