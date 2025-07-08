"""
Configuration models for Azure Red Teaming Agent.
Provides abstraction for payload formatting and response extraction.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import json
import os
from pathlib import Path


class PayloadTemplate(BaseModel):
    """Template for formatting request payloads to target API."""

    input_structure: Dict[str, Any] = Field(default_factory=dict)
    config_structure: Dict[str, Any] = Field(default_factory=dict)


class ResponseExtraction(BaseModel):
    """Configuration for extracting responses from target API."""

    primary_path: str = "messages.-1.content"
    fallback_paths: List[str] = Field(default_factory=list)
    json_field: Optional[str] = "displayResponse"
    error_response_template: str = "Error {status_code}: {error_text}"


class TargetConfig(BaseModel):
    """Configuration for target API endpoint."""

    endpoint_url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    timeout: float = 120.0
    method: str = "POST"


class RedTeamConfig(BaseModel):
    """Main configuration class for Red Team Agent."""

    target: TargetConfig
    payload_template: PayloadTemplate
    response_extraction: ResponseExtraction

    @classmethod
    def from_file(cls, config_path: str) -> "RedTeamConfig":
        """Load configuration from JSON file with environment variable substitution."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            config_data = json.load(f)

        # Perform environment variable substitution
        config_data = cls._substitute_env_vars(config_data)

        return cls(**config_data)

    @staticmethod
    def _substitute_env_vars(data: Any) -> Any:
        """Recursively substitute environment variables in configuration data."""
        if isinstance(data, dict):
            return {key: RedTeamConfig._substitute_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [RedTeamConfig._substitute_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            env_var = data[2:-1]
            return os.getenv(env_var, data)  # Return original if env var not found
        else:
            return data


def get_nested_value(data: Dict[str, Any], path: str) -> Any:
    """
    Get nested value using dot notation (e.g., 'messages.-1.content').
    Supports negative indices for arrays.
    """
    keys = path.split(".")
    current = data

    for key in keys:
        if key.lstrip("-").isdigit():  # Handle array indices
            current = current[int(key)]
        else:
            current = current[key]

    return current


def process_content(content: Any, json_field: Optional[str]) -> str:
    """
    Process content, extracting JSON field if specified.
    Handles nested JSON strings that contain the specified field.
    """
    if isinstance(content, str) and json_field:
        try:
            if content.startswith('{"') and json_field in content:
                parsed = json.loads(content)
                return str(parsed.get(json_field, content))
        except json.JSONDecodeError:
            pass

    return str(content) if content else "No response available"


def extract_response_content(response_data: Dict[str, Any], extraction_config: ResponseExtraction) -> str:
    """Extract response content based on configuration."""
    print(f"DEBUG: Extracting response with primary path: {extraction_config.primary_path}")

    # Try primary path first
    try:
        content = get_nested_value(response_data, extraction_config.primary_path)
        if content:
            processed = process_content(content, extraction_config.json_field)
            print(f"DEBUG: Primary path successful: {processed[:100]}...")
            return processed
    except (KeyError, IndexError, TypeError) as e:
        print(f"DEBUG: Primary path failed: {e}")

    # Try fallback paths
    for fallback_path in extraction_config.fallback_paths:
        print(f"DEBUG: Trying fallback path: {fallback_path}")
        try:
            content = get_nested_value(response_data, fallback_path)
            if content:
                processed = process_content(content, extraction_config.json_field)
                print(f"DEBUG: Fallback path successful: {processed[:100]}...")
                return processed
        except (KeyError, IndexError, TypeError) as e:
            print(f"DEBUG: Fallback path failed: {e}")
            continue

    # Final fallback
    fallback_response = str(response_data)
    print(f"DEBUG: Using final fallback: {fallback_response[:100]}...")
    return fallback_response


def format_payload(query: str, session_id: str, user_id: str, template: PayloadTemplate) -> Dict[str, Any]:
    """Format payload using the configured template."""

    def substitute_placeholders(obj: Any) -> Any:
        """Recursively substitute placeholders in the template."""
        if isinstance(obj, dict):
            return {key: substitute_placeholders(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [substitute_placeholders(item) for item in obj]
        elif isinstance(obj, str):
            return obj.format(query=query, session_id=session_id, user_id=user_id)
        else:
            return obj

    payload = {
        "input": substitute_placeholders(template.input_structure),
        "config": substitute_placeholders(template.config_structure),
    }

    return payload
