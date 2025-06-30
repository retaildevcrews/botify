import asyncio
import json
import logging  # Added for detailed SDK logging
import os

import requests  # For synchronous HTTP requests in callback
from azure.ai.evaluation.red_team import AttackStrategy, RedTeam, RiskCategory
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from red_team_config import RedTeamConfig, extract_response_content, format_payload

# Load environment variables from .env file
load_dotenv("credentials.env")

# Configure detailed logging for Azure SDK
logging.basicConfig(level=logging.DEBUG)


def create_target_callback(config_path: str = "red_team_config.json"):
    """Factory function to create a target callback with configuration."""
    config = RedTeamConfig.from_file(config_path)

    def target_callback(query: str) -> str:
        """Send HTTP request to the target API and return the response"""
        try:
            # Get target endpoint details from environment or config
            target_endpoint = os.getenv("TARGET_ENDPOINT") or config.target.endpoint_url
            target_api_key = os.getenv("TARGET_API_KEY", "placeholder")

            print(f"DEBUG:  Callback - Sending request to: {target_endpoint}")
            print(f"DEBUG:  Callback - Query: {query[:100]}...")  # Print first 100 chars of query

            # Create random user and session IDs for this request
            user_id = "redteam_user_123"
            session_id = "redteam_session_456"

            # Format payload using configuration template
            payload = format_payload(query, session_id, user_id, config.payload_template)

            # Setup headers from configuration
            headers = config.target.headers.copy()

            # Add authorization if we have an API key
            if target_api_key and target_api_key != "placeholder":
                headers["Authorization"] = f"Bearer {target_api_key}"
                headers["Ocp-Apim-Subscription-Key"] = target_api_key

            # Make synchronous HTTP request using requests library
            response = requests.post(
                target_endpoint, json=payload, headers=headers, timeout=config.target.timeout
            )
            print(f"DEBUG:  Callback - Response status: {response.status_code}")

            if response.status_code != 200:
                error_text = response.text
                print(f"DEBUG:  Callback - Error response: {error_text}")
                error_response = config.response_extraction.error_response_template.format(
                    status_code=response.status_code, error_text=error_text
                )
                print(f"DEBUG:  Callback - Returning error: {error_response}")
                return error_response

            response.raise_for_status()

            json_response = response.json()
            print(f"DEBUG:  Callback - Got JSON response with keys: {list(json_response.keys())}")

            # Extract response using configuration
            response_content = extract_response_content(json_response, config.response_extraction)

            # Ensure we always return a non-empty string
            if response_content is None or response_content.strip() == "":
                response_content = "No response available"

            return str(response_content)

        except Exception as e:
            error_msg = f"Error making request to target API: {e}"
            print(f"DEBUG: Callback - Exception: {error_msg}")
            return str(error_msg)

    return target_callback


async def main():
    """
    Main function to run the Azure AI Red Teaming Agent test.
    Demonstrates how to use the Azure AI Red Teaming Agent to evaluate a target model.
    """
    print("Running Azure AI Red Teaming Agent example...")

    # Get Azure Foundry credentials from environment variables
    azure_foundry_endpoint = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
    credential = DefaultAzureCredential()

    # Create the target callback using configuration
    target_callback = create_target_callback("red_team_config.json")

    # Test the callback function before running the scan
    print("Testing callback function...")
    test_query = "Hello, how to clean windows?"
    try:
        test_response = target_callback(test_query)
        print(f"DEBUG: Test query: {test_query}")
        print(f"DEBUG: Test response: {test_response[:200]}...")
    except Exception as e:
        print(f"ERROR: Callback test failed: {e}")
        return

    # Instantiate the AI Red Teaming Agent
    red_team_agent = RedTeam(
        azure_ai_project=azure_foundry_endpoint,  # required
        credential=credential,  # use the credential determined above
        risk_categories=[  # optional, defaults to all four risk categories
            RiskCategory.Violence,
            RiskCategory.HateUnfairness,
            RiskCategory.Sexual,
            RiskCategory.SelfHarm,
        ],
        num_objectives=1,  # optional, defaults to 10 (reduced to 1 for debugging purposes)
    )

    # Run the red teaming scan with specific attack strategies
    print("Starting Red Team Agent scan...")
    print("DEBUG: About to call red_team_agent.scan() with target callback")
    try:
        red_team_result = await red_team_agent.scan(
            target=target_callback,  # our callback function
            scan_name="Bot Red Team Scan",  # optional name for the scan
            attack_strategies=[  # optional attack strategies
                AttackStrategy.Base64,  # Encode in Base64
                AttackStrategy.Tense,  # Change tense of text
                AttackStrategy.Compose(
                    [AttackStrategy.Base64, AttackStrategy.ROT13]
                ),  # Composition of strategies
            ],
            output_path="bot-redteam-scan.json",  # save results to a JSON file
        )
        print("DEBUG: red_team_agent.scan() completed successfully")
        print("Scan completed. Results saved to 'bot-redteam-scan.json'")
    except Exception as e:
        print(f"Scan completed but encountered an error during result logging: {e}")
        print("Results should still be saved to 'bot-redteam-scan.json'")

        # Try to load results from the JSON file if it exists
        if os.path.exists("bot-redteam-scan.json"):
            print("Loading results from local JSON file...")
            with open("bot-redteam-scan.json", "r") as f:
                json_data = json.load(f)
                print("Results loaded successfully from JSON file.")

                # Create a simple object to hold the results for display
                class SimpleResult:
                    def __init__(self, data):
                        self.data = data
                        # Extract overall ASR from scorecard if available
                        scorecard = data.get("scorecard", {})
                        risk_summary = scorecard.get("risk_category_summary", [{}])
                        if risk_summary:
                            self.overall_asr = risk_summary[0].get("overall_asr", 0.0)
                        else:
                            self.overall_asr = 0.0

                red_team_result = SimpleResult(json_data)
        else:
            print("No JSON file found. Scan may not have completed successfully.")
            return None

    print("Completed Red Team Agent scan successfully.")
    return red_team_result


if __name__ == "__main__":
    asyncio.run(main())
