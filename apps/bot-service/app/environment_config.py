import os
import re
from dataclasses import field
from typing import Optional

import pydantic
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from pydantic import SecretStr, TypeAdapter


# Helper function to get environment variables with validation
def get_env_var(var_name, default_value=None, required=True):
    value = os.getenv(var_name, default_value)
    if required and value is None:
        raise EnvironmentError(
            f"Environment variable '{
                               var_name}' is not set."
        )
    return value


# Helper function to convert underscores to hyphens


def convert_to_key_vault_format(var_name):
    return re.sub(r"_", "-", var_name)


# Key Vault client


class KeyVaultClient:
    def __init__(self, vault_url):
        credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=vault_url, credential=credential)

    def get_secret(self, secret_name, default_value=None):
        secret_name_converted = convert_to_key_vault_format(secret_name)
        try:
            secret = self.client.get_secret(secret_name_converted)
            return secret.value
        except ResourceNotFoundError:
            if default_value is not None:
                return default_value
            raise


# Determine the configuration source
config_source = get_env_var("CONFIG_SOURCE", default_value="ENV_VAR", required=False).upper()

if config_source not in {"ENV_VAR", "KEY_VAULT"}:
    raise ValueError("Invalid CONFIG_SOURCE. Valid values are: 'ENV_VAR' or 'KEY_VAULT'")

# Initialize Key Vault client if needed
key_vault_client = None
if config_source == "KEY_VAULT":
    vault_url = get_env_var("AZURE_KEY_VAULT_URL", required=True)
    key_vault_client = KeyVaultClient(vault_url)

# Function to get configuration values based on the config source


def get_config_value(var_name, default_value=None, required=True):
    if config_source == "KEY_VAULT":
        try:
            return key_vault_client.get_secret(var_name, default_value)
        except ResourceNotFoundError:
            if required:
                raise EnvironmentError(
                    f"Required configuration variable '{
                                       var_name}' not found in Key Vault."
                )
            elif default_value is not None:
                return default_value
            else:
                return None
    else:
        return get_env_var(var_name, default_value, required)


class Config:
    arbitrary_types_allowed = True


@pydantic.dataclasses.dataclass(config=Config)
class EnvironmentConfig:
    # Open AI environment variables
    openai_api_version: Optional[str] = field(default=None)
    openai_endpoint: Optional[str] = field(default=None)
    openai_api_key: Optional[SecretStr] = field(default=None)
    openai_deployment_name: Optional[str] = field(default=None)
    openai_embedding_deployment_name: Optional[str] = field(default=None)
    openai_classifier_deployment_name: Optional[str] = field(default=None)
    openai_realtime_deployment_name: Optional[str] = field(default=None)
    openai_realtime_voice_choice: Optional[str] = field(default=None)

    # Azure Cosmos DB environment variables
    cosmos_endpoint: Optional[str] = field(default=None)
    cosmos_database: Optional[str] = field(default=None)
    cosmos_container: Optional[str] = field(default=None)
    cosmos_connection_string: Optional[SecretStr] = field(default=None)

    # Azure Search environment variables
    doc_index: str = field(default=None)

    # Content Safety environment variables
    content_safety_endpoint: Optional[str] = field(default=None)
    content_safety_key: Optional[SecretStr] = field(default=None)

    # Azure Search
    azure_search_endpoint: Optional[str] = field(default=None)
    azure_search_key: Optional[SecretStr] = field(default=None)
    azure_search_api_version: Optional[str] = field(default=None)

    # Log level
    # Valid log levels
    VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    log_level: str = get_config_value("LOG_LEVEL", default_value="INFO", required=False)
    if log_level:
        log_level = log_level.upper()
        # Validate log level
        if log_level not in VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log level: '{log_level}'. Valid log levels are: {
                             ', '.join(VALID_LOG_LEVELS)}"
            )

    # Anonymize input
    # Valid anonymizer modes
    VALID_ANONYMIZER_MODES = {"CUSTOM", "ENCRYPT"}
    anonymize_input: Optional[bool] = field(default=None)
    anonymizer_mode: str = get_config_value("ANONYMIZER_MODE", default_value="CUSTOM", required=False)
    # Validating anonymizer mode
    if anonymizer_mode not in VALID_ANONYMIZER_MODES:
        raise ValueError(
            f"""Invalid anonymizer mode: '{anonymizer_mode}'.
            Valid modes are: {', '.join(VALID_ANONYMIZER_MODES)}"""
        )
    anonymizer_crypto_key = SecretStr(
        get_config_value("ANONYMIZER_CRYPTO_KEY", default_value="", required=False)
    )

    def __post_init__(self):
        # Set values from environment variables
        # OpenAI
        self.openai_endpoint = get_config_value("AZURE_OPENAI_ENDPOINT", required=True)
        self.openai_api_key = SecretStr(get_config_value("AZURE_OPENAI_API_KEY", required=True))
        self.openai_deployment_name = get_config_value("AZURE_OPENAI_MODEL_NAME", required=True)
        self.openai_embedding_deployment_name = get_config_value(
            "AZURE_OPENAI_EMBEDDING_MODEL_NAME", required=False
        )
        self.openai_classifier_deployment_name = get_config_value(
            "AZURE_OPENAI_CLASSIFIER_MODEL_NAME", required=True
        )
        self.openai_api_version = get_config_value("AZURE_OPENAI_API_VERSION", required=True)
        if self.openai_api_version:
            os.environ["OPENAI_API_VERSION"] = self.openai_api_version
        self.openai_realtime_deployment_name = get_config_value(
            "AZURE_OPENAI_REALTIME_MODEL_NAME", required=False
        )
        self.openai_realtime_voice_choice = get_config_value(
            "AZURE_OPENAI_REALTIME_VOICE_CHOICE", default_value="coral", required=False
        )

        # Azure Cosmos DB
        self.cosmos_endpoint = get_config_value("AZURE_COSMOSDB_ENDPOINT", required=True)
        self.cosmos_database = get_config_value("AZURE_COSMOSDB_NAME", required=True)
        self.cosmos_container = get_config_value("AZURE_COSMOSDB_CONTAINER_NAME", required=True)
        self.cosmos_connection_string = SecretStr(
            get_config_value("AZURE_COSMOSDB_CONNECTION_STRING", required=False)
        )
        # Azure Search
        self.doc_index = get_config_value("AZURE_SEARCH_INDEX_NAME", required=True)
        self.azure_search_endpoint = get_config_value("AZURE_SEARCH_ENDPOINT", required=True)
        self.azure_search_key = SecretStr(get_config_value("AZURE_SEARCH_KEY", required=True))
        self.azure_search_api_version = get_config_value("AZURE_SEARCH_API_VERSION", required=True)
        # Content Safety
        self.content_safety_endpoint = get_config_value("CONTENT_SAFETY_ENDPOINT", required=True)
        self.content_safety_key = SecretStr(get_config_value("CONTENT_SAFETY_KEY", required=True))
        self.content_safety_api_version = get_config_value(
            "CONTENT_SAFETY_API_VERSION", required=False, default_value="2024-09-01"
        )
        self.log_level = get_config_value("LOG_LEVEL", required=False)
        # Anonymize Questions
        self.anonymize_input = TypeAdapter(bool).validate_python(
            get_config_value("ANONYMIZE_INPUT", required=False, default_value=True)
        )

        # Set the OpenAI API key as an environment variable since it is used by the OpenAI SDK
        if config_source == "KEY_VAULT":
            if self.openai_api_key:
                os.environ["AZURE_OPENAI_API_KEY"] = self.openai_api_key
            if self.openai_endpoint:
                os.environ["AZURE_OPENAI_ENDPOINT"] = self.openai_endpoint
            if self.openai_deployment_name:
                os.environ["AZURE_OPENAI_MODEL_NAME"] = self.openai_deployment_name
