import uuid

import streamlit as st
from helpers.single_question import process_input
from helpers.streamlit_helpers import configure_page, get_logger

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
            st.write("### Search Results")
            documents = response["search_documents"]
            for document in documents:
                document_title = document["page_content"]["title"]
                if not document_title:
                    continue

                document_chunk_blocks = document["page_content"]["chunk"].split("\n")
                document_summary = document_chunk_blocks[3].strip()[8:]
                document_content = document_chunk_blocks[4].strip()[8:]

                output = f"""
                [{document["page_content"]["title"]}]({document["page_content"]["location"]})\n
                {document_summary}\n
                {document_content}\n
                \n
                """
                st.write(output)
