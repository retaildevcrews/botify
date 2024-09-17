import os
import json
import base64
import pandas as pd
from langchain_openai import AzureOpenAIEmbeddings
from dotenv import load_dotenv
import requests
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from utils import print_response_status, get_headers_and_params, load_environment_variables

index_name= os.environ["AZURE_SEARCH_INDEX_NAME"]
skillset_name = index_name + "skillset"
datasource_name = index_name + "datasource"
indexer_name = index_name + "indexer"
blob_container_name = "docconvodocs"

# Set the ENV variables that Langchain needs to connect to Azure OpenAI
os.environ["OPENAI_API_VERSION"] = os.environ["AZURE_OPENAI_API_VERSION"]

def validate_environment_vars():
    required_vars = [
        "AZURE_SEARCH_KEY",
        "AZURE_SEARCH_API_VERSION",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "EMBEDDING_DEPLOYMENT_NAME",
        "COG_SERVICES_NAME",
        "COG_SERVICES_KEY",
        "AZURE_BLOB_STORAGE_CONNECTION_STRING"
    ]

    for var in required_vars:
        if var not in os.environ:
            raise ValueError(f"Environment variable {var} is not set")
    print("All environment variables are set")

def create_index():
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
                        "deploymentId" : os.environ['EMBEDDING_DEPLOYMENT_NAME'],
                        "modelName" : os.environ['EMBEDDING_DEPLOYMENT_NAME'],

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
            {"name": "id", "type": "Edm.String", "key": "true", "analyzer": "keyword", "searchable": "true", "retrievable": "true", "sortable": "false", "filterable": "false","facetable": "false"},
            {"name": "ParentKey", "type": "Edm.String", "searchable": "true", "retrievable": "true", "facetable": "false", "filterable": "true", "sortable": "false"},
            {"name": "title", "type": "Edm.String", "searchable": "true", "retrievable": "true", "facetable": "false", "filterable": "true", "sortable": "false"},
            {"name": "name", "type": "Edm.String", "searchable": "true", "retrievable": "true", "sortable": "false", "filterable": "false", "facetable": "false"},
            {"name": "location", "type": "Edm.String", "searchable": "true", "retrievable": "true", "sortable": "false", "filterable": "false", "facetable": "false"},
            {"name": "chunk","type": "Edm.String", "searchable": "true", "retrievable": "true", "sortable": "false", "filterable": "false", "facetable": "false"},
            {
                "name": "chunkVector",
                "type": "Collection(Edm.Single)",
                "dimensions": 1536, # IMPORTANT: Make sure these dimmensions match your embedding model name
                "vectorSearchProfile": "my-vector-profile-3",
                "searchable": "true",
                "retrievable": "true",
                "filterable": "false",
                "sortable": "false",
                "facetable": "false"
            }
        ]
    }
    url=f"{os.environ['AZURE_SEARCH_ENDPOINT']}/indexes/{index_name}"
    r = requests.put(url,
                    data=json.dumps(index_payload), headers=headers, params=params)
    print_response_status(r, "Index")

    if (r.status_code < 300):
        return True

    return False

def create_skillset():
    print("Skillset name: ", skillset_name)

    # Create a skillset
    skillset_payload = {
        "name": skillset_name,
        "description": "e2e Skillset for RAG - Files",
        "skills":
        [
            {
                "@odata.type": "#Microsoft.Skills.Vision.OcrSkill",
                "description": "Extract text (plain and structured) from image.",
                "context": "/document/normalized_images/*",
                "defaultLanguageCode": "en",
                "detectOrientation": True,
                "inputs": [
                    {
                    "name": "image",
                    "source": "/document/normalized_images/*"
                    }
                ],
                    "outputs": [
                    {
                    "name": "text",
                    "targetName" : "images_text"
                    }
                ]
            },
            {
                "@odata.type": "#Microsoft.Skills.Text.MergeSkill",
                "description": "Create merged_text, which includes all the textual representation of each image inserted at the right location in the content field. This is useful for PDF and other file formats that supported embedded images.",
                "context": "/document",
                "insertPreTag": " ",
                "insertPostTag": " ",
                "inputs": [
                    {
                    "name":"text", "source": "/document/content"
                    },
                    {
                    "name": "itemsToInsert", "source": "/document/normalized_images/*/images_text"
                    },
                    {
                    "name":"offsets", "source": "/document/normalized_images/*/contentOffset"
                    }
                ],
                "outputs": [
                    {
                    "name": "mergedText",
                    "targetName" : "merged_text"
                    }
                ]
            },
            {
                "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
                "context": "/document",
                "textSplitMode": "pages",  # although it says "pages" it actally means chunks, not actual pages
                "maximumPageLength": 5000, # 5000 characters is default and a good choice
                "pageOverlapLength": 750,  # 15% overlap among chunks
                "defaultLanguageCode": "en",
                "inputs": [
                    {
                        "name": "text",
                        "source": "/document/merged_text"
                    }
                ],
                "outputs": [
                    {
                        "name": "textItems",
                        "targetName": "chunks"
                    }
                ]
            },
            {
                "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                "description": "Azure OpenAI Embedding Skill",
                "context": "/document/chunks/*",
                "resourceUri": os.environ['AZURE_OPENAI_ENDPOINT'],
                "apiKey": os.environ['AZURE_OPENAI_API_KEY'],
                "deploymentId": os.environ['EMBEDDING_DEPLOYMENT_NAME'],
                "modelName": os.environ['EMBEDDING_DEPLOYMENT_NAME'],
                "inputs": [
                    {
                        "name": "text",
                        "source": "/document/chunks/*"
                    }
                ],
                "outputs": [
                    {
                        "name": "embedding",
                        "targetName": "vector"
                    }
                ]
            }
        ],
        "indexProjections": {
            "selectors": [
                {
                    "targetIndexName": index_name,
                    "parentKeyFieldName": "ParentKey",
                    "sourceContext": "/document/chunks/*",
                    "mappings": [
                        {
                            "name": "title",
                            "source": "/document/title"
                        },
                        {
                            "name": "name",
                            "source": "/document/name"
                        },
                        {
                            "name": "location",
                            "source": "/document/location"
                        },
                        {
                            "name": "chunk",
                            "source": "/document/chunks/*"
                        },
                        {
                            "name": "chunkVector",
                            "source": "/document/chunks/*/vector"
                        }
                    ]
                }
            ],
            "parameters": {
                "projectionMode": "skipIndexingParentDocuments"
            }
        },
        "cognitiveServices": {
            "@odata.type": "#Microsoft.Azure.Search.CognitiveServicesByKey",
            "description": os.environ['COG_SERVICES_NAME'],
            "key": os.environ['COG_SERVICES_KEY']
        }
    }

    headers, params = get_headers_and_params()

    r = requests.put(os.environ['AZURE_SEARCH_ENDPOINT'] + "/skillsets/" + skillset_name,
                    data=json.dumps(skillset_payload), headers=headers, params=params)

    print_response_status(r, "Skillset")

    if (r.status_code < 300):
        return True

    return False


def create_blob_container_datasource():

    connect_str = os.environ["AZURE_BLOB_STORAGE_CONNECTION_STRING"]
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)

    try:
        container_client = blob_service_client.create_container(name=blob_container_name)
    except ResourceExistsError:
        print(f"A container with name [{datasource_name}] already exists. Continuing with the existing container.")

    datasource_payload = {
        "name": datasource_name,
        "description": "Demo files to demonstrate cognitive search capabilities.",
        "type": "azureblob",
        "credentials": {
            "connectionString": os.environ['AZURE_BLOB_STORAGE_CONNECTION_STRING']
        },
        "dataDeletionDetectionPolicy" : {
            "@odata.type" :"#Microsoft.Azure.Search.SoftDeleteColumnDeletionDetectionPolicy",
            "softDeleteColumnName" : "IsDeleted",
            "softDeleteMarkerValue" : "true"
        },
        "container": {
            "name": blob_container_name
        }
    }

    print("Datasource name: ", datasource_name)
    print("Container name: ", blob_container_name)

    headers, params = get_headers_and_params()
    r = requests.put(os.environ['AZURE_SEARCH_ENDPOINT'] + "/datasources/" + datasource_name,
                    data=json.dumps(datasource_payload), headers=headers, params=params)
    print_response_status(r, "Datasource")

    if (r.status_code < 300):
        return True

    return False

def create_indexer():
    print("Indexer name: ", indexer_name)

    # Create an indexer
    indexer_payload = {
        "name": indexer_name,
        "dataSourceName": datasource_name,
        "targetIndexName": index_name,
        "skillsetName": skillset_name,
        "schedule" : { "interval" : "PT30M"}, # How often do you want to check for new content in the data source
        "fieldMappings": [
            {
            "sourceFieldName" : "metadata_title",
            "targetFieldName" : "title"
            },
            {
            "sourceFieldName" : "metadata_storage_name",
            "targetFieldName" : "name"
            },
            {
            "sourceFieldName" : "metadata_storage_path",
            "targetFieldName" : "location"
            }
        ],
        "outputFieldMappings":[],
        "parameters":
        {
            "maxFailedItems": -1,
            "maxFailedItemsPerBatch": -1,
            "configuration":
            {
                "dataToExtract": "contentAndMetadata",
                "imageAction": "generateNormalizedImages"
            }
        }
    }

    headers, params = get_headers_and_params()
    r = requests.put(os.environ['AZURE_SEARCH_ENDPOINT'] + "/indexers/" + indexer_name,
                    data=json.dumps(indexer_payload), headers=headers, params=params)
    print_response_status(r, "Indexer")

    if (r.status_code < 300):
        return True

    return False


if __name__ == "__main__":
    load_environment_variables()
    validate_environment_vars()
    if create_index() == False:
        exit(1)
    if (create_skillset() == False):
        exit(1)
    if (create_blob_container_datasource() == False):
        exit(1)
    if (create_indexer() == False):
        exit(1)
