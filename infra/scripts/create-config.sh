#!/bin/bash
set -euo pipefail

RESOURCE_GROUP=${1:-""}
KEY_VAULT_CONFIG=${2:-false}

if [ -z "$RESOURCE_GROUP" ]; then
    echo "Usage: create-config.sh RG=<resource-group> [VAULT=<boolean key-vault-config>]"
    exit 1
fi

# Set the resource group and deployment name
DEPLOYMENT_NAME="botify-dev"

# Specify the .env file you want to write to
ENV_FILE="../../apps/credentials.env"
TEMPLATE_ENV_FILE="../../sample_dotenv_file"

# Get the signed-in user's ID
USER_ID=$(az ad signed-in-user show --query id -o tsv)

# Deploy the Bicep template
OUTPUT=$(az deployment group create \
  -n $DEPLOYMENT_NAME \
  -g $RESOURCE_GROUP \
  -f ../azuredeploy.bicep \
  -p principalId="$USER_ID")

# Extract the name of the Key Vault
KEYVAULT_NAME=$(echo "$OUTPUT" | jq -r '.properties.outputs.configKeyVaultName.value')

# Extract the secrets from the deployment output
COG_NAME=$(echo "$OUTPUT" | jq -r '.properties.outputs.cognitiveServiceName.value')
AZURE_COSMOSDB_NAME=$(echo "$OUTPUT" | jq -r '.properties.outputs.cosmosDBAccountName.value')
AZURE_COSMOSDB_CONTAINER_NAME=$(echo "$OUTPUT" | jq -r '.properties.outputs.cosmosDBContainerName.value')
OPENAI_NAME=$(echo "$OUTPUT" | jq -r '.properties.outputs.openAIAccountName.value')

SEARCH_ENDPOINT=$(echo "$OUTPUT" | jq -r '.properties.outputs.azureSearchEndpoint.value')
SEARCH_KEY=$(echo "$OUTPUT" | jq -r '.properties.outputs.azureSearchKey.value')
COG_KEY=$(echo "$OUTPUT" | jq -r '.properties.outputs.cognitiveServiceKey.value')
AZURE_COSMOSDB_CONNECTION_STRING=$(echo "$OUTPUT" | jq -r '.properties.outputs.cosmosDBConnectionString.value')
AZURE_BLOB_STORAGE_CONNECTION_STRING=$(echo "$OUTPUT" | jq -r '.properties.outputs.blobConnectionString.value')
AZURE_OPENAI_API_KEY=$(echo "$OUTPUT" | jq -r '.properties.outputs.openAIKey.value')
AZURE_OPENAI_API_KEY=$(echo "$OUTPUT" | jq -r '.properties.outputs.openAIKey.value')
AZURE_OPENAI_MODEL_NAME=$(echo "$OUTPUT" | jq -r '.properties.outputs.gpt4DeploymentName.value')

# Set the secrets into key value pairs
SECRETS=(
  "AZURE_SEARCH_ENDPOINT" "$SEARCH_ENDPOINT"
  "AZURE_SEARCH_KEY" "$SEARCH_KEY"
  "COG_SERVICES_NAME" "$COG_NAME"
  "COG_SERVICES_KEY" "$COG_KEY"
  "AZURE_COSMOSDB_NAME" "$AZURE_COSMOSDB_NAME"
  "AZURE_COSMOSDB_CONTAINER_NAME" "$AZURE_COSMOSDB_CONTAINER_NAME"
  "AZURE_COSMOSDB_ENDPOINT" "https://$AZURE_COSMOSDB_NAME.documents.azure.com:443/"
  "AZURE_COSMOSDB_CONNECTION_STRING" "$AZURE_COSMOSDB_CONNECTION_STRING"
  "AZURE_KEY_VAULT_URL" "https://$KEYVAULT_NAME.vault.azure.net/"
  "AZURE_OPENAI_ENDPOINT" "https://$OPENAI_NAME.openai.azure.com/"
  "AZURE_OPENAI_CLASSIFICATION_ENDPOINT" "https://$OPENAI_NAME.openai.azure.com/"
  "AZURE_BLOB_STORAGE_CONNECTION_STRING" "$AZURE_BLOB_STORAGE_CONNECTION_STRING"
  "AZURE_OPENAI_API_KEY" "$AZURE_OPENAI_API_KEY"
  "AZURE_OPENAI_MODEL_NAME" "$AZURE_OPENAI_MODEL_NAME"
  "AZURE_OPENAI_CLASSIFIER_MODEL_NAME" "$AZURE_OPENAI_MODEL_NAME"
  "AZURE_OPENAI_WHISPER_MODEL_NAME" "$AZURE_OPENAI_MODEL_NAME"
  "AZURE_OPENAI_TTS_MODEL_NAME" "$AZURE_OPENAI_MODEL_NAME"
)

# Create a backup of the existing .env file
cp "$ENV_FILE" "${ENV_FILE}.bak" || true

# Read the existing .env file and store its content
declare -A ENV_VARS
while IFS='=' read -r key value; do
    # Trim any leading and trailing whitespace
    key=$(echo "$key" | xargs -0)
    value=$(echo "$value" | xargs -0)

    # Check if the key is non-empty and valid
    if [[ -n "$key" && "$key" != *=* ]]; then
        ENV_VARS["$key"]="$value"
    fi
done < "$TEMPLATE_ENV_FILE"

# Iterate over the secrets
for ((i=0; i<${#SECRETS[@]}; i+=2)); do
    KEY="${SECRETS[i]}"
    VALUE="${SECRETS[i+1]}"

    # Update the key-value pair in the existing .env file
    ENV_VARS["$KEY"]="\"$VALUE\""

    if [ "$KEY_VAULT_CONFIG" = true ]; then
        # Set the secret in the Key Vault replacing underscores with dashes in the name
        _=$(az keyvault secret set \
          --vault-name "$KEYVAULT_NAME" \
          --name "${KEY//_/-}" \
          --value "$VALUE")
    fi
done

if [ "$KEY_VAULT_CONFIG" = true ]; then
    ENV_VARS["CONFIG_SOURCE"]="\"KEY_VAULT\""
else
    ENV_VARS["CONFIG_SOURCE"]="\"ENV_VAR\""
fi

# Clear the old file
: > "$ENV_FILE"

# Write the updated key-value pairs back to the .env file
for KEY in "${!ENV_VARS[@]}"; do
    echo "$KEY=${ENV_VARS[$KEY]}" >> "$ENV_FILE"
done
