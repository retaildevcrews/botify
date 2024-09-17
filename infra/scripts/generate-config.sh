#!/bin/bash

# Set the resource group and deployment name
RESOURCE_GROUP="botify-hack-ira"
DEPLOYMENT_NAME="botify-dev"

# Specify the .env file you want to write to
ENV_FILE="../../apps/credentials2.env"

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

# Clear the file if it exists, or create it
: > "$ENV_FILE"

# Iterate over the secrets and set them in the Key Vault
for ((i=0; i<${#SECRETS[@]}; i+=2)); do
    KEY="${SECRETS[i]}"
    VALUE="${SECRETS[i+1]}"

    # Write the key-value pair to the .env file in KEY=VALUE format
    echo "$KEY=\"$VALUE\"" >> "$ENV_FILE"

    # Set the secret in the Key Vault replacing underscores with dashes in the name
    _=$(az keyvault secret set \
      --vault-name "$KEYVAULT_NAME" \
      --name "${KEY//_/-}" \
      --value "$VALUE")
done
