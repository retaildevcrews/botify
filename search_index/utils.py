import os
import base64
import pandas as pd
from langchain_openai import AzureOpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv("../apps/credentials.env")

def get_headers_and_params():
    headers = {'Content-Type': 'application/json', 'api-key': os.environ['AZURE_SEARCH_KEY']}
    params = {'api-version': os.environ['AZURE_SEARCH_API_VERSION']}
    return headers, params

def text_to_base64(text):
    # Convert text to bytes using UTF-8 encoding
    bytes_data = text.encode('utf-8')

    # Perform Base64 encoding
    base64_encoded = base64.b64encode(bytes_data)

    # Convert the result back to a UTF-8 string representation
    base64_text = base64_encoded.decode('utf-8')

    return base64_text

def print_response_status(response, item_type):
    if (response.status_code < 300):
            if response.status_code == 201:
                print(f"{item_type} created successfully")
            elif response.status_code == 204:
                print(f"{item_type} already exists")
            return True

    print(f"ERROR - creating {item_type}")
    print(response.text)
    print(response.status_code)

def load_environment_variables():
    # load the environment variables

    # Get the current directory of the script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the absolute path to the .env file
    env_path = os.path.join(current_dir, ".." , "apps", "credentials.env")

    load_dotenv(env_path)
