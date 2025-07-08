# Azure AI Foundry Red Teaming Example

This spike demonstrates how to use Azure AI Foundry for AI red teaming to evaluate the safety and robustness of AI systems.

## Setup

1. Install Poetry (if not already installed):

   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. Install dependencies:

   ```bash
   poetry install
   ```

3. Configure environment variables in `.env`:
   - `AZURE_AI_PROJECT_CONNECTION_STRING`: Your Azure AI Project connection string
   - `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint
   - `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
   - `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`: Your GPT model deployment name
   - `TARGET_ENDPOINT`: The endpoint of the AI system you want to test
   - `TARGET_API_KEY`: API key for the target system

4. Run the example:

   ```bash
   poetry run python red_teaming_example.py
   ```

## What it does

- Sets up adversarial simulation scenarios
- Tests target AI systems for potential vulnerabilities
- Evaluates safety and provides risk assessments
- Generates reports for review

## Note

This is a simplified example. In production, you would:

- Implement proper target system integration
- Configure more comprehensive scenarios
- Set up detailed logging and reporting
- Integrate with Azure AI Content Safety for evaluation
