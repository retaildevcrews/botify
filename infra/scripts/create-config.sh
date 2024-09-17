#!/bin/bash

# Set the resource group and deployment name
RESOURCE_GROUP="botify-hack-ira"
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
SEARCH_ENDPOINT=$(echo "$OUTPUT" | jq -r '.properties.outputs.azureSearchEndpoint.value')
SEARCH_KEY=$(echo "$OUTPUT" | jq -r '.properties.outputs.azureSearchKey.value')
COG_NAME=$(echo "$OUTPUT" | jq -r '.properties.outputs.cognitiveServiceName.value')
COG_KEY=$(echo "$OUTPUT" | jq -r '.properties.outputs.cognitiveServiceKey.value')

# Set the secrets into key value pairs
SECRETS=(
  "AZURE_SEARCH_ENDPOINT" "$SEARCH_ENDPOINT"
  "AZURE_SEARCH_KEY" "$SEARCH_KEY"
  "COG_SERVICES_NAME" "$COG_NAME"
  "COG_SERVICES_KEY" "$COG_KEY"
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

    # Set the secret in the Key Vault replacing underscores with dashes in the name
    _=$(az keyvault secret set \
      --vault-name "$KEYVAULT_NAME" \
      --name "${KEY//_/-}" \
      --value "$VALUE")
done

# Clear the old file
: > "$ENV_FILE"

# Write the updated key-value pairs back to the .env file
for KEY in "${!ENV_VARS[@]}"; do
    echo "$KEY=${ENV_VARS[$KEY]}" >> "$ENV_FILE"
done
