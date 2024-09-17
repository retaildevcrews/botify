import os
import json
import pandas as pd
from langchain_openai import AzureOpenAIEmbeddings
from dotenv import load_dotenv
import requests
from utils import print_response_status, get_headers_and_params

load_dotenv("../apps/credentials.env")

def validate_environment_vars():
    required_vars = [
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_API_VERSION",
        "AZURE_SEARCH_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "EMBEDDING_DEPLOYMENT_NAME",
        "AZURE_SEARCH_INDEX_NAME",
        "AZURE_SEARCH_API_VERSION",
        "AZURE_SEARCH_KEY"
    ]
    for var in required_vars:
        if var not in os.environ:
            raise ValueError(f"Missing required environment variable: {var}")
    print("All environment variables are set")



def load_json_data():
    #load data from jsonl file
    data_file='data.jsonl'
    data = pd.read_json(data_file, lines=True)

    embedder = AzureOpenAIEmbeddings(deployment=os.environ["EMBEDDING_DEPLOYMENT_NAME"], chunk_size=1)
    headers, params = get_headers_and_params()
    index_name= os.environ["AZURE_SEARCH_INDEX_NAME"]

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
            r = requests.post(os.environ['AZURE_SEARCH_ENDPOINT'] + "/indexes/" + index_name + "/docs/index",
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
    validate_environment_vars()
    load_json_data()
