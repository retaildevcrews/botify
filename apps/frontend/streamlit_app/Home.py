import streamlit as st
from helpers.streamlit_helpers import set_page_config

set_page_config(title="Botify", icon="☕️")

st.header("Botify")

st.markdown("---")

st.markdown(
    """
    This app uses Azure Cognitive Search and Azure OpenAI to provide answers and suggestions about your next favorite example!

    ### Want to learn more?
    - Check out the [GitHub Repository](https://github.com/retaildevcrews/botify/)
    - Ask a question or submit a [GitHub Issue](https://github.com/retaildevcrews/botify/issues/new)!
    """
)
st.markdown("---")
