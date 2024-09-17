import os
import json
import base64
import pandas as pd
from langchain_openai import AzureOpenAIEmbeddings
from dotenv import load_dotenv
import requests
from utils import text_to_base64, print_response_status, get_headers_and_params

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

def create_index_payload():
    # Set the ENV variables that Langchain needs to connect to Azure OpenAI
    os.environ["OPENAI_API_VERSION"] = os.environ["AZURE_OPENAI_API_VERSION"]

    index_name= os.environ["AZURE_SEARCH_INDEX_NAME"]
    print("Index name: ", index_name)

    headers, params = get_headers_and_params()

    index_payload = {
        "name": index_name,
        "vectorSearch": {
            "algorithms": [  # We are showing here 3 types of search algorithms configurations that you can do
                {
                    "name": "my-hnsw-config-1",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                },
                {
                    "name": "my-hnsw-config-2",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "m": 8,
                        "efConstruction": 800,
                        "efSearch": 800,
                        "metric": "cosine"
                    }
                },
                {
                    "name": "my-eknn-config",
                    "kind": "exhaustiveKnn",
                    "exhaustiveKnnParameters": {
                        "metric": "cosine"
                    }
                }
            ],
            "vectorizers": [
                {
                    "name": "openai",
                    "kind": "azureOpenAI",
                    "azureOpenAIParameters":
                    {
                        "resourceUri" : os.environ['AZURE_OPENAI_ENDPOINT'],
                        "apiKey" : os.environ['AZURE_OPENAI_API_KEY'],
                        "deploymentId" : "text-embedding-ada-002",
                        "modelName": "text-embedding-ada-002"
                    }
                }
            ],
            "profiles": [  # profiles is the diferent kind of combinations of algos and vectorizers
                {
                "name": "my-vector-profile-1",
                "algorithm": "my-hnsw-config-1",
                "vectorizer":"openai"
                },
                {
                "name": "my-vector-profile-2",
                "algorithm": "my-hnsw-config-2",
                "vectorizer":"openai"
                },
                {
                "name": "my-vector-profile-3",
                "algorithm": "my-eknn-config",
                "vectorizer":"openai"
                }
            ]
        },
        "semantic": {
            "configurations": [
                {
                    "name": "my-semantic-config",
                    "prioritizedFields": {
                        "titleField": {
                            "fieldName": "title"
                        },
                        "prioritizedContentFields": [
                            {
                                "fieldName": "chunk"
                            }
                        ],
                        "prioritizedKeywordsFields": []
                    }
                }
            ]
        },
        "fields": [
            {"name": "id", "type": "Edm.String", "key": "true", "filterable": "true" },
            {"name": "title","type": "Edm.String","searchable": "true","retrievable": "true"},
            {"name": "chunk","type": "Edm.String","searchable": "true","retrievable": "true", "sortable": "false", "filterable": "false", "facetable": "false"},
            {"name": "location", "type": "Edm.String", "searchable": "false", "retrievable": "true", "sortable": "false", "filterable": "false", "facetable": "false"},
            {
                "name": "chunkVector",
                "type": "Collection(Edm.Single)",
                "dimensions": 1536,
                "vectorSearchProfile": "my-vector-profile-3", # we picked profile 3 to show that this index uses eKNN vs HNSW (on prior notebooks)
                "searchable": "true",
                "retrievable": "true",
                "filterable": "false",
                "sortable": "false",
                "facetable": "false"
            }

        ],
    }
    url=f"{os.environ['AZURE_SEARCH_ENDPOINT']}/indexes/{index_name}"

    r = requests.put(url,
                    data=json.dumps(index_payload), headers=headers, params=params)
    print_response_status(r, "Index")

    if (r.status_code < 300):
        return True

    return False

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
    #if create_index_payload() == False:
    #    exit(1)
    load_json_data()
