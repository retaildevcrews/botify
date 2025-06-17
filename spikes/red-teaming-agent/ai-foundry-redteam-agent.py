import os
import asyncio
import json
import requests  # For synchronous HTTP requests in callback
import logging # Added for detailed SDK logging

# Azure imports
from azure.identity import DefaultAzureCredential, AzureCliCredential
from azure.ai.evaluation.red_team import RedTeam, RiskCategory, AttackStrategy

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv("credentials.env")

# Configure detailed logging for Azure SDK
logging.basicConfig(level=logging.DEBUG)

async def main():
    """
    Main function to run the Azure AI Red Teaming Agent test.
    Demonstrates how to use the Azure AI Red Teaming Agent to evaluate a target model.
    """
    print("Running Azure AI Red Teaming Agent example...")

    # Get Azure Foundry credentials from environment variables
    azure_foundry_endpoint = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
    credential = DefaultAzureCredential()

    # Create a random user and session IDs for the target API
    user_id = f"redteam_user_123"
    session_id = f"redteam_session_456"

    # Get target endpoint details
    target_endpoint = os.getenv("TARGET_ENDPOINT")
    target_api_key = os.getenv("TARGET_API_KEY")

    # Define callback function to handle HTTP requests to the target API
    def target_callback(query: str) -> str:
        """Send HTTP request to the target API and return the response"""
        try:
            # Get target endpoint details
            target_endpoint = os.getenv("TARGET_ENDPOINT", "http://localhost:8080/invoke")
            target_api_key = os.getenv("TARGET_API_KEY", "placeholder")

            print(f"DEBUG: PyRIT Callback - Sending request to: {target_endpoint}")
            print(f"DEBUG: PyRIT Callback - Query: {query[:100]}...")  # Print first 100 chars of query

            # Prepare the request payload with both question and messages
            payload = {
                "input": {
                    "question": query,
                    "messages": [{"role": "user", "content": query}]
                },
                "config": {
                    "configurable": {
                        "session_id": session_id,
                        "user_id": user_id
                    }
                }
            }

            headers = {
                "Content-Type": "application/json"
            }

            # Add authorization if we have an API key
            if target_api_key and target_api_key != "placeholder":
                # Try both authorization methods
                headers["Authorization"] = f"Bearer {target_api_key}"
                headers["Ocp-Apim-Subscription-Key"] = target_api_key

            # Make synchronous HTTP request using requests library
            response = requests.post(target_endpoint, json=payload, headers=headers, timeout=120.0)
            print(f"DEBUG: PyRIT Callback - Response status: {response.status_code}")

            if response.status_code != 200:
                error_text = response.text
                print(f"DEBUG: PyRIT Callback - Error response: {error_text}")
                error_response = f"Error {response.status_code}: {error_text}"
                print(f"DEBUG: PyRIT Callback - Returning error: {error_response}")
                return error_response

            response.raise_for_status()

            json_response = response.json()
            print(f"DEBUG: PyRIT Callback - Got JSON response with keys: {list(json_response.keys())}")

            # Handle the new response format with messages array
            if "messages" in json_response and len(json_response["messages"]) > 1:
                # Get the AI's response (usually the last message)
                ai_message = json_response["messages"][-1]
                if "content" in ai_message:
                    ai_content = ai_message["content"]
                    try:
                        # Try to parse the content as JSON if it contains displayResponse
                        if ai_content.startswith('{"') and "displayResponse" in ai_content:
                            parsed_content = json.loads(ai_content)
                            response_to_adversarial_chat = parsed_content.get("displayResponse", ai_content)
                        else:
                            response_to_adversarial_chat = ai_content
                    except json.JSONDecodeError:
                        response_to_adversarial_chat = ai_content

                    print(f"DEBUG: PyRIT Callback - Extracted response: {response_to_adversarial_chat[:100]}...")
                    print(f"DEBUG: PyRIT Callback - Response type: {type(response_to_adversarial_chat)}")
                    print(f"DEBUG: PyRIT Callback - Response is None: {response_to_adversarial_chat is None}")

                    # Ensure we always return a non-empty string
                    if response_to_adversarial_chat is None or response_to_adversarial_chat.strip() == "":
                        response_to_adversarial_chat = "No response available"

                    return str(response_to_adversarial_chat)

            # Fallback to old format handling
            if "output" in json_response and json_response["output"] != "":
                response_to_adversarial_chat = json_response["output"]
                if "displayResponse" in response_to_adversarial_chat:
                    response_to_adversarial_chat = response_to_adversarial_chat["displayResponse"]
                    if "recommendedProducts" in json_response["output"] and json_response["output"]["recommendedProducts"] is not None:
                        response_to_adversarial_chat = f"{response_to_adversarial_chat}\n\n{'\n'.join([f'- {p["title"]}\n  {p["description"]}' for p in json_response["output"]["recommendedProducts"]])}"
                    print(f"DEBUG: PyRIT Callback - Fallback response: {response_to_adversarial_chat}")
                    return str(response_to_adversarial_chat)

            # Final fallback
            fallback_response = str(json_response)
            print(f"DEBUG: PyRIT Callback - Final fallback: {fallback_response[:100]}...")
            return fallback_response

        except Exception as e:
            error_msg = f"Error making request to target API: {e}"
            print(f"DEBUG: PyRIT Callback - Exception: {error_msg}")
            print(f"DEBUG: PyRIT Callback - Exception type: {type(e)}")
            if hasattr(e, 'response'):
                print(f"DEBUG: PyRIT Callback - HTTP response: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
                print(f"DEBUG: PyRIT Callback - HTTP response text: {e.response.text if hasattr(e.response, 'text') else 'N/A'}")
            return str(error_msg)

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
            RiskCategory.SelfHarm
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
                AttackStrategy.Tense,   # Change tense of text
                AttackStrategy.Compose([AttackStrategy.Base64, AttackStrategy.ROT13]),  # Composition of strategies
            ],
            output_path="bot-redteam-scan.json",  # save results to a JSON file
        )
        print("DEBUG: red_team_agent.scan() completed successfully")
        print(f"DEBUG: red_team_result type: {type(red_team_result)}")
        if hasattr(red_team_result, 'scorecard'):
            print(f"DEBUG: scorecard available: {red_team_result.scorecard is not None}")
        if hasattr(red_team_result, 'attack_details'):
            print(f"DEBUG: attack_details length: {len(red_team_result.attack_details) if red_team_result.attack_details else 0}")
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

    print("\\nInspecting red_team_result attributes:")
    print(dir(red_team_result))
    print(f"Type of red_team_result: {type(red_team_result)}\\n")

    if hasattr(red_team_result, 'overall_asr'):
        print(f"Overall Attack Success Rate: {red_team_result.overall_asr}")
    else:
        print("Attribute 'overall_asr' not found on red_team_result.")

    # Print a summary of results by risk category
    print("\\nResults by Risk Category:")
    if hasattr(red_team_result, 'risk_category_asr') and red_team_result.risk_category_asr is not None:
        for category, asr in red_team_result.risk_category_asr.items():
            print(f"- {category}: {asr}")
    else:
        print("Attribute 'risk_category_asr' not found or is None.")
        if hasattr(red_team_result, 'get') and red_team_result.get('risk_category_asr') is not None:
            print(f"Attempting to get 'risk_category_asr' as a key: {red_team_result.get('risk_category_asr')}")


    # Print a summary of results by attack complexity
    print("\\nResults by Attack Complexity:")
    if hasattr(red_team_result, 'attack_complexity_asr') and red_team_result.attack_complexity_asr is not None:
        for complexity, asr in red_team_result.attack_complexity_asr.items():
            print(f"- {complexity}: {asr}")
    else:
        print("Attribute 'attack_complexity_asr' not found or is None.")
        if hasattr(red_team_result, 'get') and red_team_result.get('attack_complexity_asr') is not None:
            print(f"Attempting to get 'attack_complexity_asr' as a key: {red_team_result.get('attack_complexity_asr')}")


    return red_team_result

if __name__ == '__main__':
    asyncio.run(main())
