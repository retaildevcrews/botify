import os
import json
import pandas as pd
from dotenv import load_dotenv
import requests
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
from utils import print_response_status, get_headers_and_params, load_environment_variables
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
        "EMBEDDING_DEPLOYMENT_NAME": config.embedding_deployment_name,
        "COG_SERVICES_NAME": config.cog_services_name,
        "COG_SERVICES_KEY": config.cog_services_key,
        "AZURE_BLOB_STORAGE_CONNECTION_STRING": config.azure_blob_storage_connection_string
    }

    for var_name, var_value in required_vars.items():
        if var_value is None:
            raise ValueError(f"Environment variable {var_name} is not set or is empty")

    print("All environment variables are set and non-empty")

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
                        "resourceUri" : config.openai_endpoint,
                        "apiKey" : config.openai_api_key.get_secret_value(),
                        "deploymentId" : config.embedding_deployment_name,
                        "modelName" : config.embedding_deployment_name,

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
    url=f"{config.azure_search_endpoint}/indexes/{index_name}"
    r = requests.put(url,
                    data=json.dumps(index_payload), headers=headers, params=params)
    print_response_status(r, "Index")

    if (r.status_code < 300):
        return True

    return False

def create_skillset(chunksize: int, chunkoverlapsize: int):
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
                "maximumPageLength": chunksize, # 5000 characters is default and a good choice
                "pageOverlapLength": chunkoverlapsize,  # 15% overlap among chunks
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
                "resourceUri": config.openai_endpoint,
                "apiKey": config.openai_api_key.get_secret_value(),
                "deploymentId": config.embedding_deployment_name,
                "modelName": config.embedding_deployment_name,
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
            "description": config.cog_services_name,
            "key": config.cog_services_key.get_secret_value()
        }
    }

    headers, params = get_headers_and_params()

    r = requests.put(config.azure_search_endpoint + "/skillsets/" + skillset_name,
                    data=json.dumps(skillset_payload), headers=headers, params=params)

    print_response_status(r, "Skillset")

    if (r.status_code < 300):
        return True

    return False


def create_blob_container_datasource():

    connect_str = config.azure_blob_storage_connection_string.get_secret_value()
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
            "connectionString": config.azure_blob_storage_connection_string.get_secret_value()
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
    r = requests.put(config.azure_search_endpoint + "/datasources/" + datasource_name,
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
    r = requests.put(config.azure_search_endpoint + "/indexers/" + indexer_name,
                    data=json.dumps(indexer_payload), headers=headers, params=params)
    print_response_status(r, "Indexer")

    if (r.status_code < 300):
        return True

    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Azure Search Index")
    parser.add_argument("--chunksize", required=False, type=int, help="Size of the chunks. Default is 5000", default=5000)
    parser.add_argument("--chunkoverlapsize", required=False, type=int, help="Size of the overlap size for chunks. Default is 750", default=750)

    args = parser.parse_args()

    chunksize = args.chunksize
    chunkoverlapsize = args.chunkoverlapsize

    #print("Data file: ", datafile)
    print("Chunk size: ", chunksize)
    print("Chunk overlap size: ", chunkoverlapsize)
    print()

    config = load_environment_variables()
    validate_environment_vars(config)

    index_name= config.doc_index
    skillset_name = index_name + "skillset"
    datasource_name = index_name + "datasource"
    indexer_name = index_name + "indexer"
    blob_container_name = "docconvodocs"

    if create_index() == False:
        exit(1)
    if (create_skillset(chunksize=chunksize, chunkoverlapsize=chunkoverlapsize) == False):
        exit(1)
    if (create_blob_container_datasource() == False):
        exit(1)
    if (create_indexer() == False):
        exit(1)
