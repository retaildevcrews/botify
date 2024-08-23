import os
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()

# Helper function to get environment variables with validation
def get_env_var(var_name, default_value=None, required=True):
    value = os.getenv(var_name, default_value)
    if required and value is None:
        raise EnvironmentError(f"Environment variable '{var_name}' is not set.")
    return value

# Valid log levels
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

# Log level
log_level = get_env_var("LOG_LEVEL", default_value="INFO", required=False).upper()

# Validate log level
if log_level not in VALID_LOG_LEVELS:
    raise ValueError(f"Invalid log level: '{log_level}'. Valid log levels are: {', '.join(VALID_LOG_LEVELS)}")

# Add prefix if required
url_prefix = get_env_var("URL_PREFIX", default_value="", required=False)

# CORS origins
allowed_origins = get_env_var("ALLOWED_ORIGINS", default_value="*", required=False)

# Entra ID environment variables
api_app_id = get_env_var("API_APP_ID", required=True)
api_scope = get_env_var("API_SCOPE", default_value=f"{api_app_id}/.default",required=False)

# Speech environment variables
speech_service_scope = get_env_var("SPEECH_SERVICE_SCOPE", default_value="https://cognitiveservices.azure.com/.default",required=False)
speech_endpoint = get_env_var("SPEECH_ENDPOINT", required=True) # https://<custom sub-domain>.cognitiveservices.azure.com/
speech_resource_id = get_env_var("SPEECH_RESOURCE_ID", required=True)
