import os
import json
import pandas as pd
from langchain_openai import AzureOpenAIEmbeddings
from dotenv import load_dotenv
import requests
from utils import get_headers_and_params, load_environment_variables
import argparse
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from configs.environment_config import EnvironmentConfig


def validate_environment_vars(config : EnvironmentConfig):
    required_vars = {
        "AZURE_SEARCH_KEY": config.azure_search_key,
        "AZURE_SEARCH_API_VERSION": config.azure_search_api_version,
        "AZURE_SEARCH_ENDPOINT": config.azure_search_endpoint,
        "AZURE_OPENAI_API_VERSION": config.openai_api_version,
        "AZURE_OPENAI_ENDPOINT": config.openai_endpoint,
        "AZURE_OPENAI_API_KEY": config.openai_api_key,
        "EMBEDDING_DEPLOYMENT_NAME": config.embedding_deployment_name
    }

    for var_name, var_value in required_vars.items():
        if var_value is None:
            raise ValueError(f"Environment variable {var_name} is not set or is empty")

    print("All environment variables are set and non-empty")

def load_json_data(data_file: str):


    data = pd.read_json(data_file, lines=True)

    embedder = AzureOpenAIEmbeddings(deployment= config.embedding_deployment_name, chunk_size=1)
    headers, params = get_headers_and_params()
    index_name= config.doc_index

    #iterarte over dataframe and access each column's value to populate index

    for index, row in data.iterrows():
        title=row['title']
        keywords=row['keywords']
        summary=row['summary']
        content=row['content']
        source_url=row['source_url']
        chunk=f"""
        title: {title}
        keywords: {keywords}
        summary: {summary}
        content: {content}
        source url: {source_url}
        """
        # Create the payload
        payload = {
            "value": [
                {
                    "@search.action": "upload",
                    "id": str(index),
                    "title": title,
                    "chunk": chunk,
                    "location": source_url,
                    "chunkVector": embedder.embed_query(chunk if chunk!="" else "-------")
                }
            ]
        }
        try:
            r = requests.post(config.azure_search_endpoint + "/indexes/" + index_name + "/docs/index",
                        data=json.dumps(payload), headers=headers, params=params)
            print(f"added article {id} to index")
            if r.status_code != 200:
                print(r.status_code)
                print(r.text)
        except Exception as e:
            print("Exception:",e)
            print(chunk)
            continue

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Azure Search Index")
    parser.add_argument("--datafile", required=False, help="Path to the data file. Default is 'search_index/data.jsonl'", default="")

    args = parser.parse_args()

    datafile = args.datafile
    if (datafile is None) or (datafile.strip() == ""):
        #load data from jsonl file
        # Get the current directory of the script
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Construct the absolute path to the .env file
        datafile = os.path.join(current_dir, "data.jsonl")

    print("Data file: ", datafile)
    print()

    config = load_environment_variables()
    validate_environment_vars(config)

    load_json_data(datafile)
