# Create Backend Bot Service Infrastructure using CLI

The intent of your document to guide users in deploying the necessary Azure resources for hosting the backend application service. These resources include:

1- App Service Plan
2- App Service
3- Azure Bot

## Login with your desired tenant and subscription

``` bash
# get your Tenant ID from Azure Portal
az login --tenant <YOUR-TENANT-ID>
az account set -s <SUBSCRIPTION-NAME>
```

## Set env variables for Azure bot host resources deployment

From `botify` root folder source existing `credentials.env` file.

```bash
source ./apps/credentials.env
```

Set env variables.

```bash

export BTF_DEPLOYMENT_NAME="botify-bot-backend-app-service" # ('Required. Deployment name.).

export BTF_DEPLOYMENT_SUFFIX="botify" # ('Required. Deployment suffix identifier for AppServicePlan and Bot names. eg. 'dev', 'test', 'botify' ')

export BTF_APP_ID="ENTER YOUR VALUE" # ('Required. Active Directory App ID.')

export BTF_APP_PASSWORD="ENTER YOUR VALUE" # ('Required. Active Directory App Secret Value.')

export BTF_BLOB_SAS_TOKEN=$BLOB_SAS_TOKEN # ('Required. The SAS token for the blob hosting your data.')

# Note: The created resources will default to current resource group utilizing 'resourceGroup().name' command internally.
export BTF_RESOURCE_GROUP_SEARCH="ENTER YOUR VALUE" # ('Required. The name of the resource group where the resources (Azure Search etc.) where deployed previously.')

export BTF_AZURE_SEARCH_NAME=$COG_SERVICES_NAME # ('Required. The name of the Azure Search service deployed previously. e.g. cog-search-wh64vuky5w7ms')

export BTF_AZURE_SEARCH_INDEX_NAME=$AZURE_SEARCH_INDEX_NAME # ('Required. The name of the Azure Search index name to use. e.g. cogsrch-index-intelligent-coffee')

# Optional: Defaults to '2024-05-01-preview'
export BTF_AZURE_SEARCH_API_VERSION=$AZURE_SEARCH_API_VERSION # ('Optional. The API version for the Azure Search service.')

export BTF_AZURE_OPEN_AI_NAME="ENTER YOUR VALUE" # ('Required. The name of the Azure OpenAI resource deployed previously. e.g if your endpoint is https://gpt4-website.openai.azure.com, you must only enter "gpt4-website"')

export BTF_AZURE_OPEN_AI_API_KEY=$AZURE_OPENAI_API_KEY  # ('Required. The API key of the Azure OpenAI resource deployed previously.')

# Optional: Defaults to 'gpt-35-turbo-1106'
export BTF_AZURE_OPEN_AI_MODEL_NAME=$AZURE_OPENAI_MODEL_NAME # ('Optional. The model name for the Azure OpenAI service.')

# Optional: Defaults to '2024-08-01-preview'
export BTF_AZURE_OPEN_AI_API_VERSION=$AZURE_OPENAI_API_VERSION # ('Optional. The API version for the Azure OpenAI service.')

export BTF_COSMOSDB_ACCOUNT_NAME="ENTER YOUR VALUE" # ('Required. The name of the Azure CosmosDB. e.g cosmosdb-account-wh64vuky5w7ms')

export BTF_COSMOSDB_CONTAINER_NAME=$AZURE_COSMOSDB_CONTAINER_NAME # ('Required. The name of the Azure CosmosDB container. e.g. aibotify')

export BTF_AZURE_CONTAINER_REGISTRY_NAME="ENTER YOUR VALUE" # ('Required. The name of the existing Azure Container Registry where Docker images are stored.')

export BTF_LOG_ANALYTICS_WORKSPACE_NAME="ENTER YOUR VALUE" # ('Required. The name of the Log Analytics Workspace for diagnostic settings.')

# Optional defaults to unique and immutable bot ID. e.g 'BotId-${uniqueString(resourceGroup().id)}-${deploymentSuffix}'
# export BTF_BOT_ID="ENTER YOUR VALUE" # ('Optional. The globally unique and immutable bot ID. Also used to configure the displayName of the bot, which is mutable.')

# Optional: Defaults 'F0'
# export BTF_BOT_SKU="ENTER YOUR VALUE"  # ('Optional, defaults to F0. The pricing tier of the Bot Service Registration. Acceptable values are F0 and S1.'),  allowed values ['F0','S1']

# Optional: Defaults the name of the new App Service Plan.  e.g  'AppServicePlan-Backend-${uniqueString(resourceGroup().id)}-${deploymentSuffix}'
# export BTF_APP_SERVICE_PLAN_NAME="ENTER YOUR VALUE"  # ('Optional. The name of the new App Service Plan.')

# Optional: Defaults to 'S3'
# export BTF_APP_SERVICE_PLAN_SKU="ENTER YOUR VALUE" # ('Optional, defaults to S3. The SKU of the App Service Plan. Acceptable values are B3, S3 and P2v3.'),  allowed values [ 'B3', 'S3', 'P2v3']

# Optional: Defaults to current resource group location
# export BTF_LOCATION="ENTER YOUR VALUE" # ('Optional, defaults to resource group location. The location of the resources.')

```

## Verify values

Run the `echo command` to verify all variables were set.

``` bash
echo -e "\n  BTF_DEPLOYMENT_NAME: ${BTF_DEPLOYMENT_NAME} \n \
 BTF_RESOURCE_GROUP_SEARCH: ${BTF_RESOURCE_GROUP_SEARCH} \n \
 BTF_DEPLOYMENT_SUFFIX: ${BTF_DEPLOYMENT_SUFFIX} \n \
 BTF_APP_ID: ${BTF_APP_ID}  \n \
 BTF_APP_PASSWORD: ${BTF_APP_PASSWORD} \n \
 BTF_BLOB_SAS_TOKEN: ${BTF_BLOB_SAS_TOKEN} \n \
 BTF_AZURE_SEARCH_NAME: ${BTF_AZURE_SEARCH_NAME} \n \
 BTF_AZURE_SEARCH_INDEX_NAME: ${BTF_AZURE_SEARCH_INDEX_NAME} \n \
 BTF_AZURE_SEARCH_API_VERSION: ${BTF_AZURE_SEARCH_API_VERSION} \n \
 BTF_AZURE_OPEN_AI_NAME: ${BTF_AZURE_OPEN_AI_NAME} \n \
 BTF_AZURE_OPEN_AI_API_KEY: ${BTF_AZURE_OPEN_AI_API_KEY} \n \
 BTF_AZURE_OPEN_AI_MODEL_NAME: ${BTF_AZURE_OPEN_AI_MODEL_NAME} \n \
 BTF_AZURE_OPEN_AI_API_VERSION: ${BTF_AZURE_OPEN_AI_API_VERSION} \n \
 BTF_COSMOSDB_ACCOUNT_NAME ${BTF_COSMOSDB_ACCOUNT_NAME} \n \
 BTF_COSMOSDB_CONTAINER_NAME: ${BTF_COSMOSDB_CONTAINER_NAME} \n \
 BTF_AZURE_CONTAINER_REGISTRY_NAME: ${BTF_AZURE_CONTAINER_REGISTRY_NAME} \n \
 BTF_LOG_ANALYTICS_WORKSPACE_NAME: ${BTF_LOG_ANALYTICS_WORKSPACE_NAME} \n"

```

## Create azure resources

Run the following `az cli command` to deploy the infrastructure.

``` bash
az deployment group create \
  -n $BTF_DEPLOYMENT_NAME \
  -g $BTF_RESOURCE_GROUP_SEARCH \
  -f apps/bot-service/infra/azuredeploy-backend.bicep \
  -p deploymentSuffix=${BTF_DEPLOYMENT_SUFFIX} \
     appId=${BTF_APP_ID} \
     appPassword=${BTF_APP_PASSWORD} \
     blobSASToken=${BTF_BLOB_SAS_TOKEN} \
     azureSearchName=${BTF_AZURE_SEARCH_NAME} \
     azureSearchIndexName=${BTF_AZURE_SEARCH_INDEX_NAME} \
     azureSearchAPIVersion=${BTF_AZURE_SEARCH_API_VERSION} \
     azureOpenAIName=${BTF_AZURE_OPEN_AI_NAME} \
     azureOpenAIAPIKey=${BTF_AZURE_OPEN_AI_API_KEY} \
     azureOpenAIModelName=${BTF_AZURE_OPEN_AI_MODEL_NAME} \
     azureOpenAIAPIVersion=${BTF_AZURE_OPEN_AI_API_VERSION} \
     cosmosDBAccountName=${BTF_COSMOSDB_ACCOUNT_NAME} \
     cosmosDBContainerName=${BTF_COSMOSDB_CONTAINER_NAME} \
     acrName=${BTF_AZURE_CONTAINER_REGISTRY_NAME} \
     logAnalyticsWorkspaceName=${BTF_LOG_ANALYTICS_WORKSPACE_NAME} \
     appServicePlanSKU='B3' \
  -c

```
