# pyrit-demo

Red teaming and Prompt attack demos with PyRIT

## Setup env

First time setup:

```bash
# Create a new virtual env
python3 -m venv .venv
# Activate virtual env
source .venv/bin/activate
# Install packages
pip install pyrit dotenv pyyaml "azure-ai-evaluation[redteam]" azure-identity
```

Use terminal or VSCode launcher (F5) to run one of the python files:

- [ai-foundry-redteam-agent.py](./ai-foundry-redteam-agent.py) - Azure AI Foundry Red Teaming Agent example (requires Azure AI Foundry project)

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

For a simpler example without Azure AI Foundry requirements, use the `simplified-redteam.py` script which uses PyRIT directly.

## Environment Variables

For the standard PyRIT examples:

```sh
TARGET_ENDPOINT=your_target_endpoint
TARGET_API_KEY=your_target_api_key
OPENAI_CHAT_ENDPOINT=your_openai_endpoint
OPENAI_CHAT_KEY=your_openai_api_key
OPENAI_CHAT_API_VERSION=2025-01-01-preview
```

For the AI Foundry Red Team Agent example:

Option 1: Using Azure Foundry endpoint and key (preferred if you have them):

```sh
AZURE_FOUNDRY_ENDPOINT=https://your-foundry-instance.azurewebsites.net/api/projects/your-project
AZURE_FOUNDRY_KEY=your_foundry_api_key

TARGET_ENDPOINT=your_target_endpoint
TARGET_API_KEY=your_target_api_key
```

Option 2: Using Azure subscription details with DefaultAzureCredential:

```sh
AZURE_SUBSCRIPTION_ID=your_subscription_id
AZURE_RESOURCE_GROUP=your_resource_group
AZURE_PROJECT_NAME=your_project_name
# Or alternatively, use the project URL format:
# AZURE_AI_PROJECT=https://your-account.services.ai.azure.com/api/projects/your-project

TARGET_ENDPOINT=your_target_endpoint
TARGET_API_KEY=your_target_api_key
```
