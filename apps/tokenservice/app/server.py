import logging
import threading
import time

import _additional_version_info
import toml
from api import (
    allowed_origins,
    api_scope,
    credential,
    log_level,
    speech_endpoint,
    speech_resource_id,
    speech_service_scope,
    url_prefix,
)
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# Set root logger level before other imports
logging.getLogger().setLevel(log_level)
logger = logging.getLogger(__name__)

# Load the pyproject.toml file
pyproject = toml.load("pyproject.toml")

# Extract the version, short_sha, and build_timestamp
version = pyproject.get("tool", {}).get("poetry", {}).get("version", "Version not found")

if _additional_version_info.__short_sha__ and _additional_version_info.__build_timestamp__:
    version = (
        version
        + "-"
        + _additional_version_info.__short_sha__
        + "-"
        + _additional_version_info.__build_timestamp__
    )

app = FastAPI(
    root_path=url_prefix,
    title="Gen AI Rag Example Token Service",
    version=version,
    description="""A token service for public clients to obtain access tokens for
                   the Gen AI Rag Example API and Speech Service.""",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Get the app version
@app.get("/version")
def get_version():
    return {"version": app.version}


# Global variables
speech_token = None  # Speech token


# Refresh the speech token every 9 minutes
def refreshSpeechToken() -> None:
    global speech_token
    while True:
        try:
            token = credential.get_token(speech_service_scope)
            speech_token = f"aad#{speech_resource_id}#{token.token}"
        except Exception:
            logger.error("Failed to refresh speech token")
        finally:
            logger.info("Sleeping for 9 minutes...")
            time.sleep(60 * 9)


# Default route -> leads to the OpenAPI Swagger definition
@app.get("/", include_in_schema=False)
async def redirect_root_to_docs():
    return RedirectResponse(f"{url_prefix}/docs")


@app.post("/speech")
def get_speech_token(response: Response):
    if speech_token is None:
        raise HTTPException(status_code=500, detail="Failed to get speech token")
    response.headers["SpeechEndpoint"] = speech_endpoint
    return {"speech_token": speech_token}


@app.post("/api")
def get_api_token():
    try:
        token = credential.get_token(api_scope)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to get API token")
    return {"access_token": token.token, "expires_on": token.expires_on}


# Start the speech token refresh thread
speechTokenRefereshThread = threading.Thread(target=refreshSpeechToken)
speechTokenRefereshThread.daemon = True
logger.debug("Starting speech token refresh thread")
speechTokenRefereshThread.start()
