# Token Service - FastAPI

A service implemented in FastAPI that provides tokens for a protected API and Azure Speech Service resources to public clients.

## Use case

This service provides a mechanism for public clients, such as Javascript apps running in the browser, to retrieve time-limited tokens for accessing a protected API and the Azure Speech Service. Confidential clients such as mobile devices and web applications running on a server can safely embed such secrets and do not need this service.

### Benefits

- No need to embed long-lived secrets in public clients
- Enables use of token protection provided by Entra ID
- Can use CORS policy and HTTP-only cookies for additional protection provided by clients

### Limitations

- Does not authenticate users. All users share the identity of the service
- Token lifetime is not configurable
- Limited ability to restrict token requests

While the token lifetime is not configurable, the client may examine the expiration date of the token if they want to enforce a shorter lifetime.

## Configuration

The following configuration values are required and should be provided as environment variables:

- API_APP_ID - The Entra ID Application ID for the protected API. Access tokens scoped to this API will be provided
- SPEECH_ENDPOINT - The URL for the private Azure Speech Service endpoint. Ex: "https://{custom sub-domain}.cognitiveservices.azure.com/"
- SPEECH_RESOURCE_ID - The Azure Resource ID for the Speech Service. Ex: "/subscriptions/{sub id}/resourceGroups/{rg name}/providers/Microsoft.CognitiveServices/accounts/{speech service name}"

The following optional values enable more control over the token configuration and application security settings:

- ALLOWED_ORIGINS - Used to specify the allowed origins for the CORS policy. Default is '*'
- API_SCOPE - Identifies the target API scope used for the token. Default is '{api_app_id}/.default'
- SPEECH_SERVICE_SCOPE = Default is 'cognitiveservices.azure.com/.default'

During local development when a managed identity is not available, the following variables can be used.

- AZURE_CLIENT_ID
- AZURE_TENANT_ID
- AZURE_CLIENT_SECRET

The service principal identified by these values needs to be assigned *Cognitive Services Speech User* role.

## Endpoints

The service exposes two endpoints. Each endpoint uses the DefaultAzureCredential from the Azure Identity library to request an access token for a single resource.

1. **/speech**

    **Description:** This endpoint uses the SPEECH_SERVICE_SCOPE and SPEECH_RESOURCE_ID to request an access token for the Speech Service. A background thread is used to refresh this token every 9 minutes.
    The required format for this token is documented on [MS Learn](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-configure-azure-ad-auth?tabs=portal&pivots=programming-language-python#create-the-speech-sdk-configuration-object)

    **Returns:** {'speech_token':'aad#/subscriptions/.../#eyJ0...9dqyg'}

2. **/api**

    **Description:** This endpoint uses the API_APP_ID to request an access token for the backend API. Tokens are refreshed automatically by the Azure Identity library

    **Returns:** {'access_token':'eyJ0e...', 'expires_on':'1711203454'}

## Run on App Service with Managed Identity

1. Get the required configuration values described above from your deployed API and Speech Service resources
2. Build the container image and push to an accessible registry
3. Deploy the container to Azure App Service, specifying the required configuration values
4. Create a Managed Identity and assign it to the deployed app

    ```bash
    export RESOURCE_GROUP="testrg"
    export WEB_APP_NAME="token-service"
    export IDENTITY_NAME="umi-token-service"

    az identity create -n $IDENTITY_NAME -g $RESOURCE_GROUP
    export IDENTITY_RID="$(az identity show -n $IDENTITY_NAME -g $RESOURCE_GROUP --query id -o tsv)"
    az webapp identity assign -g $RESOURCE_GROUP -n $WEB_APP_NAME -identities $IDENTITY_RID

    ```

5. Assign the requried RBAC role

    ```bash
    az role assignment create --assignee $IDENTITY_NAME --role "Cognitive Services Speech User" --scope $SPEECH_RESOURCE_ID

    ```

### Configure the protected API

The protected API must be configured to validate tokens provided by this service. The following Azure CLI commands can be used to configure the protected API to allow tokens issued by itself and the managed identiy used by the token service.

```bash
export PROTECTED_API="backend-api"
$PROTECTED_API_APPID=$(az webapp auth show -g $RESOURCE_GROUP -n $PROTECTED_API --query properties.identityProviders.azureActiveDirectory.registration.clientId -o tsv)
$TOKEN_SERVICE_APPID=$(az identity show -g $RESOURCE_GROUP -n $IDENTITY_NAME --query clientId -o tsv)

$ALLOWED_APPS="[$PROTECTED_API_APPID,$TOKEN_SERVICE_APPID]"
az webapp auth update -g $RESOURCE_GROUP -n $PROTECTED_API --set identityProviders.azureActiveDirectory.validation.defaultAuthorizationPolicy.allowedApplications=$ALLOWED_APPS

```

### Example Client implementation

```python

import os
import requests
import azure.cognitiveservices.speech as speechsdk

token_service_url = os.environ.get('TOKEN_SERVICE_URL','https://localhost:8000/speech')
speech_region = os.environ.get('SPEECH_REGION','eastus2')

def retrieve_token():
    url = token_service_url
    response = requests.post(url)
    token = response.json()['speech_token']
    return token

def from_mic():
    speech_config = speechsdk.SpeechConfig(auth_token=retrieve_token(), region=speech_region)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)

    print("Speak into your microphone.")
    result = speech_recognizer.recognize_once_async().get()
    print(result.text)

from_mic()

```
