# Deploy Private Network Infrastructure (short version)

## Example deployment

The example in this folder is used to deploy the full private infrastructure to the rg-Aus-chatbots resource group. The .bicepparam files are preconfigured with appropriate values.
See the full [README](../README.md) for complete details.

### Set environment variables

``` bash

export RESOURCE_GROUP="rg-Aus-chatbots"
export DEPLOYMENT_PREFIX="botify-private"
export CONTENT_SAFETY_KEY="<your content safety key here>"

```

### Deploy networking

``` bash

# change directory
cd infra/examples

az deployment group create \
  -n $DEPLOYMENT_PREFIX-net \
  -g $RESOURCE_GROUP \
  -f ../azuredeploy-private.bicep \
  -p botify.bicepparam -c

```

> 🛑  Note: Subsequent deployments of this template may show an error "When updating a shared private link resource, only 'requestMessage' property is allowed to be modified". This is a known issue that does not impact functionality

### Deploy OpenTelemetry collector

``` bash

az deployment group create \
  -n $DEPLOYMENT_PREFIX-collector \
  -g $RESOURCE_GROUP \
  -f ../../apps/collector/infra/azuredeploy-collector-private.bicep \
  -p ../../apps/collector/infra/azuredeploy-collector-private.bicepparam -c

```

### Deploy backend resources

``` bash

az deployment group create \
  -n $DEPLOYMENT_PREFIX-backend \
  -g $RESOURCE_GROUP \
  -f ../../apps/backend/langserve/infra/azuredeploy-backend-private.bicep \
  -p botify-backend.bicepparam -c

```

### Deploy frontend resources

``` bash

az deployment group create \
  -n $DEPLOYMENT_PREFIX-frontend \
  -g $RESOURCE_GROUP \
  -f ../../apps/frontend/azuredeploy-frontend-private.bicep \
  -p botify-frontend.bicepparam -c

```

### Display URLs for deployed endpoints

Backend:

``` bash

az deployment group show \
  -n $DEPLOYMENT_PREFIX-backend \
  -g $RESOURCE_GROUP \
  --query 'properties.outputs.backendUrl.value' \
  --output tsv

```

Frontend:

``` bash

az deployment group show \
  -n $DEPLOYMENT_PREFIX-frontend \
  -g $RESOURCE_GROUP \
  --query 'properties.outputs.frontendUrl.value' \
  --output tsv

```

- If enabling `Entra Auth` on the backend run:

``` bash

export VAULT_NAME="kv-btfy-dev-use2-001"
export FRONT_DOOR_ENDPOINT="backend"
export FRONT_DOOR_NAME="afd-btfy-dev-use2-001"
export TOKEN_SERVICE_IDENTITY="umi-tokenservice-btfy-dev-use2-001"
export FRONT_DOOR_HOSTNAME=$(az afd endpoint show -n $FRONT_DOOR_ENDPOINT --profile-name $FRONT_DOOR_NAME -g $RESOURCE_GROUP --query hostName -o tsv)
# create an app registration for a single tenant with a specific web redirect URI and ID tokens option enabled
export APP_REGISTRATION_ID=$(az ad app create --display-name "app-Auth-$DEPLOYMENT_PREFIX-$FRONT_DOOR_ENDPOINT" \
      --web-redirect-uris "https://${FRONT_DOOR_HOSTNAME}/.auth/login/aad/callback" \
      --sign-in-audience AzureADMyOrg --enable-id-token-issuance true --query appId -o tsv)

export APP_REGISTRATION_CLIENT_SECRET=$(az ad app credential reset --id $APP_REGISTRATION_ID --append --display-name 'AuthClientSecret' --years 2 --query password -o tsv)

# Allow the token service to access the backend
export ALLOWED_APPLICATIONS=$(az identity show -g $RESOURCE_GROUP -n $TOKEN_SERVICE_IDENTITY --query clientId -o tsv)

az deployment group create \
  -n EntraAuthUpdateBackend \
  -g $RESOURCE_GROUP \
  -f ../azuredeploy-entra-auth.bicep \
  -p botify-backend-auth.bicepparam

# Store the AppId in KeyVault. Token service uses this to request tokens scope to the backend
az keyvault secret set --vault-name $VAULT_NAME --name BackendAppId --value $APP_REGISTRATION_ID

```
