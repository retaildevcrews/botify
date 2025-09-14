#!/bin/bash

# Prompt for user input with defaults
read -p "Enter resource group name [default: 'rg-botify']: " RESOURCE_GROUP_NAME
RESOURCE_GROUP_NAME=${RESOURCE_GROUP_NAME:-rg-botify}

read -p "Enter location [default: 'eastus2']: " LOCATION
LOCATION=${LOCATION:-eastus2}

read -p "Enter deployment name [default: 'botify-dev']: " DEPLOYMENT_NAME
DEPLOYMENT_NAME=${DEPLOYMENT_NAME:-botify-dev}

read -p "Do you want to deploy container app endpoint? (y/n) [default: 'n']: " DEPLOY_CONTAINER_APP
DEPLOY_CONTAINER_APP=${DEPLOY_CONTAINER_APP:-n}

# Check if resource group exists and create if it doesn't
if [ $(az group exists --name $RESOURCE_GROUP_NAME) = true ]; then
    echo -e "\nResource group '${RESOURCE_GROUP_NAME}' already exists."
    read -p "Do you want to continue with the deployment? (y/n): " CONTINUE_DEPLOYMENT
    if [[ ! $CONTINUE_DEPLOYMENT =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
    echo "--------------------------"
    echo -e "Using existing resource group: ${RESOURCE_GROUP_NAME} in location: ${LOCATION}"
    echo "--------------------------"
else
    # Create the resource group
    az group create --name $RESOURCE_GROUP_NAME --location $LOCATION
    echo "--------------------------"
    echo -e "Creating resource group: ${RESOURCE_GROUP_NAME} in location: ${LOCATION}"
    echo "--------------------------"
fi

# Convert user input to boolean for Bicep
if [[ $DEPLOY_CONTAINER_APP =~ ^[Yy]$ ]]; then
    DEPLOY_ENDPOINT_PARAM="true"
else
    DEPLOY_ENDPOINT_PARAM="false"
fi

# Create required resources
az deployment group create -n $DEPLOYMENT_NAME -g $RESOURCE_GROUP_NAME -f azuredeploy.bicep -c -p main.parameters.json -p deployEndpoint=$DEPLOY_ENDPOINT_PARAM

echo "--------------------------"
echo -e "Resources created in resource group: ${RESOURCE_GROUP_NAME}"
echo "--------------------------"

# Get the outputs and create an environment file
echo "--------------------------"
echo -e "Creating environment file with the outputs of the deployment"
echo "--------------------------"

AZURE_STORAGE_ACCOUNT_NAME=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.blobStorageAccountName.value" -o tsv | tr -d '\r\n')
AZURE_BLOB_STORAGE_CONNECTION_STRING=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.blobConnectionString.value" -o tsv | tr -d '\r\n')
STORAGE_ACCOUNT_KEY=$(az storage account keys list --account-name "${AZURE_STORAGE_ACCOUNT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "[0].value" -o tsv | tr -d '\r\n')
BLOB_SAS_TOKEN=$(az storage account generate-sas --account-name "$AZURE_STORAGE_ACCOUNT_NAME" --services b --account-key "$STORAGE_ACCOUNT_KEY" --resource-types sco --expiry "$(date -u -d "7 days" '+%Y-%m-%dT%H:%MZ')" --permissions rwdl --output tsv | tr -d '\r\n')
AZURE_OPENAI_MODEL_NAME=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.azureOpenAIModelName.value" -o tsv | tr -d '\r\n')
AZURE_OPENAI_EMBEDDING_MODEL_NAME=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.azureOpenAIEmbeddingModelName.value" -o tsv | tr -d '\r\n')
AZURE_OPENAI_ENDPOINT=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.azureOpenAIEndpoint.value" -o tsv | tr -d '\r\n')
AZURE_OPENAI_ACCOUNT_NAME=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.azureOpenAIAccountName.value" -o tsv | tr -d '\r\n')
AZURE_OPENAI_API_KEY=$(az cognitiveservices account keys list --name "${AZURE_OPENAI_ACCOUNT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" -o json | jq -r '.key1' | tr -d '\r\n')
AZURE_SEARCH_ENDPOINT=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.azureSearchEndpoint.value" -o tsv | tr -d '\r\n')
AZURE_SEARCH_KEY=$(az deployment group show --resource-group "${RESOURCE_GROUP_NAME}" --name "${DEPLOYMENT_NAME}" --query "properties.outputs.azureSearchAdminKey.value" -o tsv | tr -d '\r\n')
COGNITIVE_SERVICES_NAME=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.cognitiveServiceName.value" -o tsv | tr -d '\r\n')
COGNITIVE_SERVICES_KEY=$(az cognitiveservices account keys list --name "${COGNITIVE_SERVICES_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" -o json | jq -r '.key1' | tr -d '\r\n')
AZURE_COSMOSDB_NAME=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.cosmosDBAccountName.value" -o tsv | tr -d '\r\n')
AZURE_COSMOSDB_CONTAINER_NAME=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.cosmosDBContainerName.value" -o tsv | tr -d '\r\n')
AZURE_COSMOSDB_CONNECTION_STRING=$(az cosmosdb keys list -n $AZURE_COSMOSDB_NAME -g $RESOURCE_GROUP_NAME --query primaryReadonlyMasterKey -o tsv)
CONTENT_SAFETY_ENDPOINT=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.contentSafetyEndpoint.value" -o tsv | tr -d '\r\n')
CONTENT_SAFETY_KEY=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.contentSafetyKey.value" -o tsv | tr -d '\r\n')
APPLICATIONINSIGHTS_CONNECTION_STRING=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.appInsightsConnectionString.value" -o tsv | tr -d '\r\n')

# Only get container app related outputs if user chose to deploy them
if [[ $DEPLOY_CONTAINER_APP =~ ^[Yy]$ ]]; then
    CONTAINER_APPS_ENV_NAME=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.containerAppEnvName.value" -o tsv | tr -d '\r\n')
    CONTAINER_REGISTRY_NAME=$(az deployment group show --name "${DEPLOYMENT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" --query "properties.outputs.containerRegistryName.value" -o tsv | tr -d '\r\n')
    AZURE_CONTAINER_REGISTRY_KEY=$(az acr credential show --name "${CONTAINER_REGISTRY_NAME}" --query "passwords[0].value" -o tsv | tr -d '\r\n')
fi

cat <<EOF > ../apps/credentials.env
# Don't mess with this unless you really know what you are doing
AZURE_SEARCH_API_VERSION="2024-05-01-preview"
AZURE_OPENAI_API_VERSION="2024-08-01-preview"
FAST_API_SERVER="http://bot-service:8080"

SPEECH_ENGINE="azure"

# Demo Data (edit with your own if you want to use your own data)
AZURE_BLOB_STORAGE_CONNECTION_STRING="${AZURE_BLOB_STORAGE_CONNECTION_STRING}"
BLOB_CONNECTION_STRING="${AZURE_BLOB_STORAGE_CONNECTION_STRING}"
BLOB_SAS_TOKEN="${BLOB_SAS_TOKEN}"

# Edit with your own azure services values
AZURE_OPENAI_MODEL_NAME="${AZURE_OPENAI_MODEL_NAME}"
AZURE_OPENAI_CLASSIFIER_MODEL_NAME="${AZURE_OPENAI_MODEL_NAME}"
AZURE_OPENAI_WHISPER_MODEL_NAME="<model deployment name>"
AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT}"
AZURE_OPENAI_EMBEDDING_MODEL_NAME="${AZURE_OPENAI_EMBEDDING_MODEL_NAME}"
AZURE_OPENAI_CLASSIFICATION_ENDPOINT="https://<az-oai-resource>.openai.azure.com/"
AZURE_OPENAI_API_KEY="${AZURE_OPENAI_API_KEY}"
AZURE_SEARCH_ENDPOINT="${AZURE_SEARCH_ENDPOINT}"
AZURE_SEARCH_KEY="${AZURE_SEARCH_KEY}"
AZURE_SEARCH_INDEX_NAME="<Azure search index name>"
COG_SERVICES_NAME="${COGNITIVE_SERVICES_NAME}"
COG_SERVICES_KEY="${COGNITIVE_SERVICES_KEY}"
AZURE_COSMOSDB_ENDPOINT="https://${AZURE_COSMOSDB_NAME}.documents.azure.com:443/"
AZURE_COSMOSDB_NAME="${AZURE_COSMOSDB_NAME}"
AZURE_COSMOSDB_CONTAINER_NAME="${AZURE_COSMOSDB_CONTAINER_NAME}"
AZURE_COSMOSDB_CONNECTION_STRING="${AZURE_COSMOSDB_CONNECTION_STRING}"
AZURE_SPEECH_KEY="<key for speech service>"
AZURE_SPEECH_REGION="<region where speech service is deployed>"
LOG_LEVEL=INFO

CONTENT_SAFETY_ENDPOINT="${CONTENT_SAFETY_ENDPOINT}"
CONTENT_SAFETY_KEY="${CONTENT_SAFETY_KEY}"
APPLICATIONINSIGHTS_CONNECTION_STRING="${APPLICATIONINSIGHTS_CONNECTION_STRING}"
OPEN_TELEMETRY_COLLECTOR_ENDPOINT="<collector endpoint with port>" # Telemetry disabled if not set. Set to "http://otelcol:4318" for local telemetry with docker compose
CONFIG_SOURCE='<ENV_VAR|KEY_VAULT>' # Options are: '<ENV_VAR|KEY_VAULT>'  Determines if pulling the configuration from the environment or from Azure KeyVault. Default is ENV

# Only needed if CONFIG_SOURCE is set to KEY_VAULT
AZURE_KEY_VAULT_URL='<Azure Keyvault URL>'
LOCAL_MODE="true"

# Only set these when not using Managed Identity for KeyVault access
AZURE_TENANT_ID='<Tenant ID>'
AZURE_CLIENT_ID='<App Registration ID>'
AZURE_CLIENT_SECRET='<App Registration Client Secret>'

# Set these to publish evaluation runs
RESOURCE_GROUP='<resource group name where ai studio project resource is located>'
SUBSCRIPTION_ID='<subscription name where ai studio project resource is located>'
PROJECT_NAME='<ai studio project name>'

AZURE_MANAGED_IDENTITY_CLIENT_ID="$UAMI_CLIENT_ID"
AZURE_MANAGED_IDENTITY_RESOURCE_ID="$UAMI_RESOURCE_ID"
EOF

echo "--------------------------"
echo -e "Environment file created with the outputs of the deployment"
echo "--------------------------"

if [[ $DEPLOY_CONTAINER_APP =~ ^[Yy]$ ]]; then
    echo "--------------------------"
    echo -e "Now you can deploy the services using the infra/services_deployment.sh script with the following parameters:"
    echo -e "bash infra/services_deployment.sh <RESOURCE_GROUP_NAME> <CONTAINER_APPS_ENV_NAME> <AZURE_CONTAINER_REGISTRY_NAME>"
    echo -e "You can use this values:"
    echo -e "RESOURCE_GROUP_NAME: ${RESOURCE_GROUP_NAME}"
    echo -e "CONTAINER_APPS_ENV_NAME: ${CONTAINER_APPS_ENV_NAME}"
    echo -e "AZURE_CONTAINER_REGISTRY_NAME: ${CONTAINER_REGISTRY_NAME}"
    ECHO -E "AZURE_CONTAINER_REGISTRY_KEY: ${AZURE_CONTAINER_REGISTRY_KEY}"
    echo -e "Example: bash infra/services_deployment.sh ${RESOURCE_GROUP_NAME} ${CONTAINER_APPS_ENV_NAME} ${CONTAINER_REGISTRY_NAME} ${AZURE_CONTAINER_REGISTRY_KEY}"
    echo "--------------------------"
else
    echo "--------------------------"
    echo -e "Container app deployment skipped as requested."
    echo "--------------------------"
fi
