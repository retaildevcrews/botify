# pyrit-demo

Red teaming and Prompt attack demos with PyRIT

## Infrastructure Setup

TODO

## Login with your desired tenant and subscription

``` bash
# get your Tenant ID from Azure Portal
az login --tenant <YOUR-TENANT-ID>

az account set -s <SUBSCRIPTION-NAME>

```

## Setup and Running

```bash

cd spikes/red-teaming-agent # assumes you are at the root of the project

# Copy over required enviornment variables
cp sample_env.txt credentials.env

# Install dependencies
poetry install

# Run red team scan
poetry run python ai-foundry-redteam-agent.py

```

## Troubleshooting

If you encounter this error with the AI Foundry Red Team examples:

```sh
Exception: Failed to connect to your Azure AI project. Please check if the project scope is configured correctly, and make sure you have the necessary access permissions. Status code: 400.
```

You need to:

1. Make sure you have created an Azure AI Foundry project
2. Set the correct environment variables in your .env file
3. Log in to Azure using `az login` if you're using DefaultAzureCredential
4. Check if your region is supported (currently only East US2, Sweden Central, France Central, Switzerland West)

