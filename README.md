# Botify

![Botify RAG Application Accelerator](./docs/images/banner.jpg)

![License](https://img.shields.io/badge/license-MIT-green.svg)

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fretaildevcrews%2Fbotify%2Fjoaquinrz-azureDeployButton%2Finfra%2Fazure_button%2Fazure_deploy.jsonn)

## Overview

This repository is an implementation of a Generative AI chatbot
that leverages Azure Cloud Services, Microsoft Open-Source, and other Open-Source technologies to create
a question/answer bot.
The bot implements RAG for grounding answers the user's questions.
The project is structured to ensure ease of development, maintenance, and deployment
while also providing examples of desirable features for security, privacy, etc.

## Goals

- Allow users to quickly create a working bot/inference endpoint that has all necessary components that
an enterprise would require to take a product to production with confidence.
- Remove need to evaluate various frameworks and solutions by providing a functional
implemetnation that is composed of pre-selected components.
- Provide opportuinity to expand/replace components if desired/needed.

## Quick Start

- [Run Application Locally](docs/developer_experience/quick_run_local.md)
- [Update System Prompt](docs/solution_overview/prompt_maintenance.md)

## Additional Documentation

- [Solution Overview](docs/solution_overview/README.md)
- [Developer Experience](docs/developer_experience/README.md)
- [Evaluation Approach](evaluation/README.md)

The work leverages examples found in: [The Azure AI Search Azure OpenAI Accelerator](https://github.com/MSUSAzureAccelerators/Azure-Cognitive-Search-Azure-OpenAI-Accelerator)

## Project Goals

Provide an accelerator that:

- Simplifies creation of a chatbot that uses Generative AI to answer questions from documents within a search index.
- Ensures a good development experience so the chatbot can be easily maintained and updated.
- Provides a pattern/approach for evaluating variants of the chatbot.
- Provides examples/patterns for implementing protective functionality like: prompt shielding, content safety, pii anonymization, etc.
- Provides pattern for automated publishing of new versions of the chatbot to any environment, e.g., DEV, TEST, PRODUCTION.

## Accelerator Features

- Dev Container for simplified developer experience (Requires GitHub Codespaces, or local Docker Daemon)
- Docker Compose for easy running of service and frontend
- Streamlit UI for testing bot - voice enabled
- Templating for prompts (Text, or Jinja)
- Starter System Prompt Based on <https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/system-message>
- JSON Output integration (ensure output adheres to schema with a single point configuration)
- PII Identification/Redaction
- Content Safety Protection (MS Service) (PromptShield, Content Safetry)
- Topic Protection - Banned Topics
- Topic Detection - Require Disclaimers
- Retrieval Augmented Generation from Document Index (Azure AI Search)
- OpenTelemetry integraton for observability
- Configuration Management/Identification for bot endpoint
- Evaluation Framework (PromptFlow Evauate Module, Custom Performance Evaluation)
  - Collection of Evaluators
    - CalledToolEvaluator
    - CoherenceEvaluator
    - FluencyEvaluator
    - JsonSchemaValidationEvaluator
    - RAGGroundednessEvaluator
    - RelevanceOptionalContextEvaluator
- Document Index Maintenance (Azure AI Search) Example

## Azure Resource Requirements

[See list of required Azure Resources](docs/solution_overview/azure_resources.md)

## How to file issues and get help

This project uses GitHub Issues to track bugs and feature requests. Please search the existing issues before filing new ones to avoid duplicates. For new issues, file your bug report or feature request as a new issue.

For help and questions about using this project, please open a GitHub issue.

### Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For details, visit <https://cla.opensource.microsoft.com>

When you submit a pull request, a CLA bot will automatically determine whether you need to provide a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

### Trademarks

This project may contain trademarks or logos for projects, products, or services.

Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).

Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.

Any use of third-party trademarks or logos are subject to those third-party's policies.
