# Red Teaming with Azure AI Foundry

This document outlines how to run a local Red Teaming scan against the Botify agent using the Azure AI Foundry Python SDK.

For more information on running Red Teaming scans locally, visit the [Azure docs](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/run-scans-ai-red-teaming-agent).

## Infrastructure Setup

To run a redTeaming scan, you can do so locally or in the cloud. However, when this document was written, running redTeaming scans in the cloud (Azure AI Foundry instance) only supported Azure OpenAI model deployments in your Azure AI Foundry project as a target, and not custom endpoints.

In this guide, we'll run the red team scan locally against a botify endpoint and upload the results to Azure AI Foundry. You can also access the test results locally, via the script's output artifacts such as the `.scan_Bot_Red_Team_Scan_*` directory and `bot-redteam-scan.json` file.

If you would like to host these scan results on Azure AI Foundry, you'll need these following resources:

1. Azure AI Foundry
2. Project within Azure AI Foundry
3. Blob Storage Account
4. Connection between Azure AI Foundry and Blob Storage Account (**Note**: Use Entra ID only, Account Key Auth does NOT work!)

### Login and create resources

``` bash
# get your Tenant ID from Azure Portal
az login --tenant <YOUR-TENANT-ID>

az account set -s <SUBSCRIPTION-NAME>

```

Create a Resource Group where all the assets will be deployed.

```bash
export RESOURCE_GROUP="rg-botify"

# List of Azure AI Foundry regions can be found at:
# https://learn.microsoft.com/en-us/azure/ai-foundry/reference/region-support
export RESOURCE_GROUP_LOCATION="eastus2"

# Optional: Run the following if you haven't setup botify before
# az group create --name $RESOURCE_GROUP --location $RESOURCE_GROUP_LOCATION

```

Run the Bicep script

```bash
# only use a-z and 0-9 - do not include punctuation or uppercase characters
# must be between 5 and 16 characters long
# must start with a-z (only lowercase)
export AI_FOUNDRY_NAME="your-foundry-name"

cd spikes/red-teaming-agent # assumes you are at the root of the project

az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file redteam-setup.bicep \
  --parameters aiFoundryName=$AI_FOUNDRY_NAME location=$RESOURCE_GROUP_LOCATION

```

## Running Red Teaming Scan

Run the Red Teaming Scan against Botify. This guide assumes that Botify is currently running as a docker container locally after following the [quick run steps](../../docs/developer_experience/quick_run_local.md).

```bash

cd spikes/red-teaming-agent # assumes you are at the root of the project

# Copy over enviornment variables
cat <<EOF > "./credentials.env"
AZURE_AI_FOUNDRY_ENDPOINT="https://$AI_FOUNDRY_NAME.services.ai.azure.com/api/projects/$AI_FOUNDRY_NAME-proj"
TARGET_ENDPOINT="http://localhost:8080/invoke"
TARGET_API_KEY=
EOF

# Install dependencies
poetry install

# Run red team scan
poetry run python ai-foundry-redteam-agent.py

# View local scan results in the latest`.scan_Bot_Red_Team_Scan_*` directory and `bot-redteam-scan.json` file.

```
