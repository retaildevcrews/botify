# Azure Red Teaming Agent Configuration

This directory contains an Azure AI Red Teaming Agent implementation with configurable payload formatting and response extraction.

## Features

- **Configuration-driven**: Payload and response handling are defined in JSON configuration files
- **Environment variable support**: Configuration supports environment variable substitution
- **Type safety**: Uses Pydantic models for configuration validation
- **Flexible response extraction**: Supports multiple fallback paths for response extraction
- **Reusable**: Easy to create different configurations for different target APIs

## Files

- `ai-foundry-redteam-agent.py` - Main red teaming agent script
- `red_team_config.py` - Configuration models and utility functions
- `red_team_config.json` - Configuration file for payload and response handling
- `sample_credentials.env` - Sample environment variables file

## Quick Start

1. **Copy the sample credentials file:**

   ```bash
   cp sample_credentials.env credentials.env
   ```

2. **Edit credentials.env with your actual values:**

   ```bash
   AZURE_AI_FOUNDRY_ENDPOINT=https://your-foundry-endpoint.cognitiveservices.azure.com/
   TARGET_ENDPOINT=http://localhost:8080/invoke
   TARGET_API_KEY=your-api-key-here
   ```

3. **Run the red teaming agent:**

   ```bash
   python ai-foundry-redteam-agent.py
   ```

## Configuration

The new configuration system abstracts payload formatting and response extraction into external JSON files, eliminating hardcoded logic in Python.

### JSON Configuration File (`red_team_config.json`)

The configuration file has three main sections:

#### Target Configuration

```json
{
  "target": {
    "endpoint_url": "${TARGET_ENDPOINT}",
    "headers": {
      "Content-Type": "application/json"
    },
    "timeout": 120.0,
    "method": "POST"
  }
}
```

#### Payload Template

```json
{
  "payload_template": {
    "input_structure": {
      "question": "{query}",
      "messages": [{"role": "user", "content": "{query}"}]
    },
    "config_structure": {
      "configurable": {
        "session_id": "{session_id}",
        "user_id": "{user_id}"
      }
    }
  }
}
```

#### Response Extraction

```json
{
  "response_extraction": {
    "primary_path": "messages.-1.content",
    "fallback_paths": ["output.displayResponse", "output"],
    "json_field": "displayResponse",
    "error_response_template": "Error {status_code}: {error_text}"
  }
}
```

### Environment Variable Substitution

The configuration supports environment variable substitution using the `${VAR_NAME}` syntax:

- `${TARGET_ENDPOINT}` - Will be replaced with the value of the TARGET_ENDPOINT environment variable
- `${TARGET_API_KEY}` - Will be replaced with the value of the TARGET_API_KEY environment variable

### Customizing for Different APIs

To adapt this for a different target API:

1. **Create a new configuration file** (e.g., `my_api_config.json`)
2. **Modify the payload structure** to match your API's expected format
3. **Update the response extraction paths** to match your API's response format
4. **Update the target callback creation** to use your new config file:

   ```python
   target_callback = create_target_callback("my_api_config.json")
   ```

### Response Path Syntax

The response extraction uses dot notation to navigate nested JSON structures:

- `"messages.-1.content"` - Gets the content field from the last message in the messages array
- `"output.displayResponse"` - Gets the displayResponse field from the output object
- `"data.result.text"` - Gets nested fields using dot notation

Negative indices are supported for arrays (`-1` for last element, `-2` for second-to-last, etc.).

## Example: Adapting to a Different API

If your target API expects a different payload format, create a new configuration:

```json
{
  "target": {
    "endpoint_url": "${TARGET_ENDPOINT}",
    "headers": {
      "Content-Type": "application/json",
      "X-API-Key": "${API_KEY}"
    },
    "timeout": 60.0
  },
  "payload_template": {
    "input_structure": {
      "prompt": "{query}",
      "max_tokens": 1000
    },
    "config_structure": {
      "user": "{user_id}",
      "session": "{session_id}"
    }
  },
  "response_extraction": {
    "primary_path": "choices.0.message.content",
    "fallback_paths": ["text", "response"],
    "json_field": null,
    "error_response_template": "API Error {status_code}: {error_text}"
  }
}
```

This flexibility allows you to test different APIs without modifying the Python code.

---

## Original Azure AI Foundry Red Teaming Documentation

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
