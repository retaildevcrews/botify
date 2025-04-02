import json
import logging
import os
from typing import Dict, Any, Optional, AsyncGenerator

from app.messages import GENERIC_ERROR_MESSAGE
from app.settings import AppSettings
from botify_langchain.runnable_factory import RunnableFactory
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

retries_limit = AppSettings().invoke_retry_count


async def invoke_wrapper(input_data, config_data, runnable_factory: RunnableFactory, retry_count=0):
    error_response = GENERIC_ERROR_MESSAGE
    try:
        runnable = runnable_factory.get_runnable()
        result = await runnable.ainvoke(input_data, config_data)
        return result
    except Exception as e:
        logger.exception(f"Error invoking runnable: {e}")
        if not isinstance(e, ValueError):
            result = (
                await invoke_wrapper(input_data, config_data, runnable_factory, retry_count + 1)
                if retry_count < retries_limit
                else error_response
            )
            return result
        return error_response


async def stream_response(input_data, config_data, runnable_factory: RunnableFactory) -> AsyncGenerator[str, None]:
    """Stream the response from the LLM using the Azure OpenAI client directly"""
    try:
        logger.info("Starting direct Azure OpenAI streaming response")
        app_settings = AppSettings()
        
        # Debug what we're receiving
        logger.debug(f"Full input_data: {json.dumps(input_data)}")
        
        # Extract messages from the input
        messages = []
        for msg in input_data.get("messages", []):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Convert to OpenAI message format
            messages.append({"role": role, "content": content})

        logger.debug(f"Formatted messages for OpenAI: {messages}")
        
        # Get credentials from environment
        api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
        azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
            
        # Initialize Azure OpenAI client directly
        try:
            client = AsyncAzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=azure_endpoint
            )
            
            # Better credential validation
            if not api_key or not azure_endpoint:
                logger.error("Azure OpenAI credentials not properly configured")
                yield f"data: {json.dumps({'error': 'Azure OpenAI credentials not properly configured'})}\n\n"
                yield f"data: [DONE]\n\n"
                return
                
            # Request model information
            logger.debug(f"Using model: {app_settings.environment_config.openai_deployment_name}")
            
            # Stream directly with Azure OpenAI
            logger.debug("Starting streaming request to OpenAI")
            response = await client.chat.completions.create(
                model=app_settings.environment_config.openai_deployment_name,
                messages=messages,
                temperature=app_settings.model_config.temperature,
                max_tokens=app_settings.model_config.max_tokens,
                stream=True
            )
            logger.debug("Received streaming response from OpenAI")
            
            # For accumulating the full response
            full_response = ""
            sent_anything = False
            
            # Process the streaming response
            async for chunk in response:
                logger.debug(f"Received chunk: {chunk}")
                
                # Check if chunk has choices and isn't empty
                if not hasattr(chunk, "choices") or not chunk.choices:
                    logger.warning("Received chunk without choices")
                    continue
                    
                # Safe access pattern for the delta content
                try:
                    if hasattr(chunk.choices[0], "delta") and hasattr(chunk.choices[0].delta, "content"):
                        content = chunk.choices[0].delta.content
                        if content:  # Make sure content isn't None or empty
                            logger.debug(f"Extracted content chunk: {content}")
                            full_response += content
                            sent_anything = True
                            # Send the content chunk
                            yield f"data: {json.dumps({'content': content})}\n\n"
                except (AttributeError, IndexError) as e:
                    logger.warning(f"Error accessing chunk content: {e}")
                    continue
            
            # If nothing was sent, send a default response
            if not sent_anything:
                default_response = "I'm here to help you. What would you like to know?"
                logger.warning(f"No content was streamed, sending default response: {default_response}")
                yield f"data: {json.dumps({'content': default_response})}\n\n"
            
            # Send end message
            logger.info("Streaming completed, sending DONE signal")
            logger.debug(f"Full response was: {full_response}")
            yield f"data: [DONE]\n\n"
            
        except Exception as e:
            logger.exception(f"Error initializing OpenAI client or during streaming: {e}")
            yield f"data: {json.dumps({'error': f'OpenAI client error: {str(e)}'})}\n\n"
            yield f"data: [DONE]\n\n"
            
    except Exception as e:
        logger.exception(f"Error in stream_response: {e}")
        yield f"data: {json.dumps({'error': f'Streaming error: {str(e)}'})}\n\n"
        yield f"data: [DONE]\n\n"


def format_partial_json(text: str) -> str:
    """
    Attempt to format partial JSON content in a way that maintains valid JSON structure.
    This is used for streaming JSON responses.
    """
    try:
        # Try to parse as complete JSON
        data = json.loads(text)
        return json.dumps(data)
    except json.JSONDecodeError:
        # If it's not valid JSON yet, return as-is
        return text
