# AI Red Teaming with Azure AI Foundry

This document outlines how to run a AI Red Teaming scan against the Botify agent using the Azure AI Foundry Python SDK.

For more information on running Red Teaming scans locally, visit the [Azure docs](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/run-scans-ai-red-teaming-agent).

## Overview

Red Teaming is a security practice that simulates adversarial attacks on either a model or application to determine any safety risks or vulnerabilities. Typically, red teaming has been conducted manually after the application has been fully deployed, which can be a time and resource intensive process. Through AI Red Teaming Agent, teams can now run automated red teaming scans in a repeatable manner, accelerating the overall testing timeline. Therefore, the team can also incorporate the AI red teaming agent in their CI/CD builds to ensure their app meets necessary safety guidelines long before it gets released.

AI Red Teaming leverages the [PyRIT](https://azure.github.io/PyRIT/) framework and conducts attacks based on combinations of `risk categories` per `attack strategies`. [Risk Categories](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/ai-red-teaming-agent#supported-risk-categories) range from `Hateful/Unfair`, `Sexual`, `Violent` and `Self Harm`, while [Attack Strategies](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/ai-red-teaming-agent#supported-attack-strategies) such as flipping characters, encoding in base64 and more are brought over from PyRIT. The AI Red Teaming agent also provides an unfiltered adversarial LLM that users can provide custom seed prompts and prompt suffixes to kick-start custom attacks.

### Comparison with PyRIT

Here's a list of observations (during the time of writing) that we find notable when comparing Azure AI Red Teaming over PyRIT.

- AI Red Teaming provides access to an unfiltered adversarial model (though this is abstracted away where PyRIT lets you specify an LLM endpoint + system prompt to create your own adversarial model)
- Scans are relatively easy to setup in AI Red Teaming
- AI Red Teaming is not very customizable (preset default attack surface for converters + default datasets). You can pass in some suffix or seed prompt options but there is a lot more configurability in PyRIT.
- No Multi-turn support for text-based LLM interactions in AI Red Teaming.
- Dependency on several Azure resources to run an AI Red Teaming scan, even if running locally.

## Infrastructure Setup

To run a red teaming scan, you can do so locally or in the cloud. However, when this document was written, running redTeaming scans in the cloud (Azure AI Foundry instance) only supported Azure OpenAI model deployments in your Azure AI Foundry project as a target, and not custom endpoints.

In this guide, we'll run the red team scan locally against the botify endpoint and upload the results to Azure AI Foundry. You can also access the test results locally, via the script's output artifacts such as the `.scan_Bot_Red_Team_Scan_*` directory and `bot-redteam-scan.json` file.

To get started, you'll need these following resources:

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

# List of Azure Red Teaming supported regions can be found at:
# https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/develop/run-scans-ai-red-teaming-agent#region-support
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

## Custom Attack Strategies

### Why Use Custom Attack Strategies?

While Azure AI Foundry provides built-in attack strategies (like `SuffixAppend`, `PrefixAppend`, `SystemPromptInjection`, etc.), these have limitations:

1. **Limited Customization**: Built-in strategies use predefined text patterns and cannot be customized with arbitrary custom text
2. **Fixed Attack Patterns**: You cannot modify the specific prompts or suffixes used in the attacks
3. **No Domain-Specific Tests**: Built-in strategies may not cover specific vulnerabilities relevant to your application

Custom attack strategies allow you to:

- Test specific vulnerabilities unique to your AI application
- Use domain-specific prompt injection techniques
- Implement advanced attack patterns not covered by built-in strategies
- Test for system prompt extraction with custom suffixes
- Validate specific security controls and guardrails

### Running Custom Attack Tests

This repository includes a standalone custom suffix attack script that demonstrates how to implement and run custom attack strategies independently of the main Azure AI Foundry scan.

```bash
cd spikes/red-teaming-agent

# Install dependencies (if not already done)
poetry install

# Run custom suffix attack tests
poetry run python custom-attack-strategy-test.py

```

### Custom Attack Strategy Limitations

**Important**: Custom attack strategies cannot be uploaded to Azure AI Foundry for the following reasons:

1. **Azure AI Foundry Integration**: The Azure AI Foundry SDK only accepts results from its built-in attack strategies
2. **Result Format Compatibility**: Custom attack results use different schemas than Azure AI Foundry expects
3. **Validation Requirements**: Azure AI Foundry validates that results come from recognized attack strategy types

### Recommended Workflow

For comprehensive red teaming:

1. **Run the main scan** (`ai-foundry-redteam-agent.py`) to test built-in attack strategies and upload results to Azure AI Foundry
2. **Run custom attack tests** (`custom-attack-strategy-test.py`) to test application-specific vulnerabilities
3. **Combine insights** from both approaches to get complete security coverage

This hybrid approach ensures you get both the standardized testing capabilities of Azure AI Foundry and the flexibility to test custom attack scenarios specific to your application.
