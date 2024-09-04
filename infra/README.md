# Create botify Infrastructure using CLI

The intent of your document to guide users in deploying the necessary Azure resources for hosting the backend application service. These resources include:

1. Azure AI Search
2. Cognitive Services
3. CosmosDB
4. Storage account

Note: (Pre-requisite) You need to have an Azure OpenAI service already created

## Login with your desired tenant and subscription

``` bash
# get your Tenant ID from Azure Portal
az login --tenant <YOUR-TENANT-ID>
az account set -s <SUBSCRIPTION-NAME>
```

Steps to setup the `botify` infrastructure

1. In Azure OpenAI studio, deploy these models (older models than the ones stated below won't work):
   - "gpt-35-turbo-1106 (or newer)"
   - "gpt-4-turbo-1106  (or newer)"
   - "gpt-4o"
   - "gpt-4o-mini"
   - "text-embedding-ada-002 (or newer)"
2. Create a Resource Group where all the assets of this botify project are going to be. Azure OpenAI can be in different RG or a different Subscription.

    ```bash
    export RESOURCE_GROUP="rg-botify"

    export RESOURCE_GROUP_LOCATION="eastus2" #Please use desired region

    az group create --name $RESOURCE_GROUP --location $RESOURCE_GROUP_LOCATION

    ```

3. Run the following instructions to deploy the infrastructure to create all the Azure Infrastructure needed. (Azure AI Search, Cognitive Services, etc).

    **Note**: If you have never created a `Azure AI Services Multi-Service account` before, please create one manually in the azure portal to read and accept the Responsible AI terms. Once this is deployed, delete this and then use the above deployment button.

Set env variables they are preset to default values. (All are optionals bicep file will set default values)

```bash

export DEPLOYMENT_NAME="botify-dev" # ('Required. Deployment name.)

# 'Optional. defaults to 'cog-search-${uniqueString(resourceGroup().id)}'
export  AZURE_SEARCH_NAME="ENTER YOUR VALUE"  # ('Optional. Service name must only contain lowercase letters, digits or dashes, cannot use dash as the first two or last one characters, cannot contain consecutive dashes, and is limited between 2 and 60 characters in length.')

# 'Optional. defaults to 'standard'
export  AZURE_SEARCH_SKU="ENTER YOUR VALUE"  # ('Optional, defaults to standard. The pricing tier of the search service you want to create (for example, basic or standard).'),  allowed ('free', 'basic', 'standard', 'standard2', 'standard3', 'storage_optimized_l1', 'storage_optimized_l2')

# 'Optional. defaults to '1'
export  AZURE_SEARCH_REPLICA_COUNT="ENTER YOUR VALUE"  # ('Optional, defaults to 1. Replicas distribute search workloads across the service. You need at least two replicas to support high availability of query workloads (not applicable to the free tier). Must be between 1 and 12.')

# 'Optional. defaults to '1'
export  AZURE_SEARCH_PARTITION_COUNT="ENTER YOUR VALUE"  # ('Optional, defaults to 1. Partitions allow for scaling of document count as well as faster indexing by sharding your index over multiple search units. Allowed values: 1, 2, 3, 4, 6, 12.')

# 'Optional. defaults to 'default'
export  AZURE_SEARCH_HOSTING_MODE="ENTER YOUR VALUE"  # ('Optional, defaults to default. Applicable only for SKUs set to standard3. You can set this property to enable a single, high density partition that allows up to 1000 indexes, which is much higher than the maximum indexes allowed for any other SKU.') allowed('default', 'highDensity')

# 'Optional. defaults to 'cognitive-service-${uniqueString(resourceGroup().id)}'
export  COGNITIVE_SERVICE_NAME="ENTER YOUR VALUE"  # ('Optional. The name of our application. It has to be unique. Type a name followed by your resource group name. (<name>-<resourceGroupName>)')

# 'Optional. defaults to 'cosmosdb-account-${uniqueString(resourceGroup().id)}'
export  COSMOSDB_ACCOUNT_NAME="ENTER YOUR VALUE"  # ('Optional. Cosmos DB account name, max length 44 characters, lowercase')

# 'Optional. defaults to 'cosmosdb-db-${uniqueString(resourceGroup().id)}'
export  COSMOSDB_DATABASE_NAME="ENTER YOUR VALUE"  # ('Optional. The name for the CosmosDB database')

# 'Optional. defaults to 'cosmosdb-container-${uniqueString(resourceGroup().id)}'
export  COSMOSDB_CONTAINER_NAME="ENTER YOUR VALUE"  # ('Optional. The name for the CosmosDB database container')

# 'Optional. defaults to 'blobstorage${uniqueString(resourceGroup().id)}'
export  BLOB_STORAGE_ACCOUNT_NAME="ENTER YOUR VALUE"  # ('Optional. The name of the Blob Storage account')

# 'Optional. defaults to 'resourceGroup().location'
export  LOCATION="ENTER YOUR VALUE" # ('Optional, defaults to resource group location. The location of the resources.')

```

## Verify values

Run the `echo command` to verify all variables were set.

``` bash

echo -e "\n DEPLOYMENT_NAME: ${DEPLOYMENT_NAME} \n \
RESOURCE_GROUP: ${RESOURCE_GROUP}\n \
AZURE_SEARCH_NAME: ${AZURE_SEARCH_NAME} \n \
AZURE_SEARCH_SKU: ${AZURE_SEARCH_SKU} \n \
AZURE_SEARCH_REPLICA_COUNT: ${AZURE_SEARCH_REPLICA_COUNT} \n \
AZURE_SEARCH_PARTITION_COUNT: ${AZURE_SEARCH_PARTITION_COUNT} \n \
AZURE_SEARCH_HOSTING_MODE: ${AZURE_SEARCH_HOSTING_MODE} \n \
COGNITIVE_SERVICE_NAME: ${COGNITIVE_SERVICE_NAME} \n \
COSMOSDB_ACCOUNT_NAME: ${COSMOSDB_ACCOUNT_NAME} \n \
COSMOSDB_DATABASE_NAME: ${COSMOSDB_DATABASE_NAME} \n \
COSMOSDB_CONTAINER_NAME: ${COSMOSDB_CONTAINER_NAME} \n \
BLOB_STORAGE_ACCOUNT_NAME: ${BLOB_STORAGE_ACCOUNT_NAME} \n \
LOCATION: ${LOCATION} \n"
```

## Create azure resources

Run the following `az cli command` to deploy the infrastructure.

``` bash

az deployment group create \
  -n $DEPLOYMENT_NAME \
  -g $RESOURCE_GROUP \
  -f infra/azuredeploy.bicep -c

  # Note: add the following parameters if they are different from default.

  # \ -p azureSearchName=${AZURE_SEARCH_NAME} \
  #   azureSearchSKU=${AZURE_SEARCH_SKU} \
  #   azureSearchReplicaCount=${AZURE_SEARCH_REPLICA_COUNT} \
  #   azureSearchPartitionCount=${AZURE_SEARCH_PARTITION_COUNT} \
  #   azureSearchHostingMode=${AZURE_SEARCH_HOSTING_MODE} \
  #   cognitiveServiceName=${COGNITIVE_SERVICE_NAME} \
  #   cosmosDBAccountName=${COSMOSDB_ACCOUNT_NAME} \
  #   cosmosDBDatabaseName=${COSMOSDB_DATABASE_NAME} \
  #   cosmosDBContainerName=${COSMOSDB_CONTAINER_NAME} \
  #   blobStorageAccountName=${BLOB_STORAGE_ACCOUNT_NAME} \
  #   location==${LOCATION}
```

## Create azure resources for private networking

Set the following environment variable to prevent name duplication when deploying resources. The recommended pattern for this value is:
workload-environment-region

- *workload* should describe the application being deployed (botify, or btfy for short)
- *environment* is generally one of 'dev','test','prod'
- *region* represents the target Azure region

This follows the general guidance for naming resources on [MS learn](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming)

### Deploy Private Network Infrastructure

The private networking resources are managed using 4 template files in order to keep the templates within the size limit. They should be deployed in the following order:

1. infra/azuredeploy-private.bicep - Deploys VirtualNetwork and required PaaS services (OpenAI, AI Search, KeyVault, Cosmos, etc)
2. apps/collector/azuredeploy-collector-private.bicep - Deploys an OpenTelemetry Collector to App Service
3. apps/bot-service/infra/azuredeploy-backend-private.bicep - Deploys the backend API to App Service
4. apps/frontend/azuredeploy-frontend-private.bicep - Deploys the frontend to App Service

Each template has an associated .bicepparam file with example configuration values.

🛑 In the initial phase, it is imperative to designate the required values in each parameter file.
[azuredeploy-private.bicepparam](./azuredeploy-private.bicepparam)
[azuredeploy-collector-private.bicepparam](../apps/collector/infra/azuredeploy-collector-private.bicepparam)
[azuredeploy-backend-private.bicepparam](../apps/bot-service/infra/azuredeploy-backend-private.bicepparam)
[azuredeploy-frontend-private.bicepparam](../apps/frontend/azuredeploy-frontend-private.bicepparam)

- `resourceNameSuffix` Resource name pattern

Environment variable values will be used to create and set KeyVault secrets if assigned, otherwise, they can be set directly in the Key Vault after deployment.

The following optional parameters may also be set

- `keyVaultAdminPrincipal` A valid EntraID group or user id should be specified as keyvault administrator, so that secrets can be set before deploying resources that depend on them.
- `apiContainerImage` = The container image reference for the API in the format "repository/image:tag". Ex: retaildevcrews/botify-api:latest

🛑 Review the `vaultSecrets` and `apiConfigurationValues` parameters. These will use environment variables to set KeyVault secrets, application configuration variables, and the password for the jumpbox admin user. If these environment variables are not set at deployment time, the secrets can be updated later.

Run the following `az cli command` to deploy the infrastructure.

> Note: This should be run once with defaults to create the vnet, keyvault, and private dns zones. Once complete, secrets must be created in the deployed keyvault for the `jumpbox` admin password and `App Service`.

🛑 The deployment of Azure API Management service will take approximately 45 minutes to complete for the first time, given that the `apimEnabled` parameter is set to true by default.

🛑 The deployment of Azure Cosmos Database service will take approximately 5 minutes to complete for the first time, given that the `cosmosEnabled` parameter is set to true by default.

``` bash
az deployment group create \
  -n $DEPLOYMENT_NAME \
  -g $RESOURCE_GROUP \
  -f infra/azuredeploy-private.bicep \
  -p infra/azuredeploy-private.bicepparam -c
  # Note: add the following parameters if they are different from default.
  #   location==${LOCATION}
```

### To ensure the successful operation of the App Service post-deployment, two primary actions are necessary

1. Ensuring the configuration values and secrets are correct
2. Ensuring a container image exists in the registry.

if required, after ensuring that configuration values and secrets are correct, and the image has been pushed to the registry, set the following parameter in azuredeploy-private.bicepparam and run the deployment again to update the appservice:

- `apimEnabled: false`
- `cosmosEnabled: false`

> 🛑  Note: Since we do not intent to update Azure API Management service or Cosmos Database then, set `apimEnabled` and `cosmosEnabled` to false.

``` bash

az deployment group create \
  -n $DEPLOYMENT_NAME \
  -g $RESOURCE_GROUP \
  -f infra/azuredeploy-private.bicep \
  -p infra/azuredeploy-private.bicepparam -c
  # Note: add the following parameters if they are different from default.
  #   location==${LOCATION}
```

### Deploy OpenTelemetry resources (optional)

If desired, deploy an OpenTelemetry collector to receive telemetry data from the backend

``` bash

az deployment group create \
  -n $DEPLOYMENT_NAME-collector \
  -g $RESOURCE_GROUP \
  -f apps/collector/infra/azuredeploy-collector-private.bicep \
  -p apps/collector/infra/azuredeploy-collector-private.bicepparam -c
  # Note: add the following parameters if they are different from default.
  #   location==${LOCATION}
```

### Deploy backend resources

``` bash

az deployment group create \
  -n $DEPLOYMENT_NAME-backend \
  -g $RESOURCE_GROUP \
  -f apps/bot-service/infra/azuredeploy-backend-private.bicep \
  -p apps/bot-service/infra/azuredeploy-backend-private.bicepparam -c
  # Note: add the following parameters if they are different from default.
  #   location==${LOCATION}
```

### Deploy frontend resources

``` bash

az deployment group create \
  -n $DEPLOYMENT_NAME-backend \
  -g $RESOURCE_GROUP \
  -f apps/frontend/azuredeploy-frontend-private.bicep \
  -p apps/frontend/azuredeploy-frontend-private.bicepparam -c
  # Note: add the following parameters if they are different from default.
  #   location==${LOCATION}
```

### Deploy Jumpbox (optional)

Set the following parameter in azuredeploy-private.bicepparam and run the deployment again to deploy the jumpbox VM and Bastion:

`jumpboxEnabled: true`

``` bash

az deployment group create \
  -n $DEPLOYMENT_NAME \
  -g $RESOURCE_GROUP \
  -f infra/azuredeploy-private.bicep \
  -p infra/azuredeploy-private.bicepparam -c
  # Note: add the following parameters if they are different from default.
  #   location==${LOCATION}
```

## Configure your App Service to use Microsoft Entra sign-in

Before your application can sign in users, you first need to register your application in Azure AD to get the client ID and secret, then deploy the corresponding Auth and App configuration. You can achieve this by following the subsequent steps.

- To extract the App Service name from the deployment properties you need to get the `FrontEnd UI App Service Deployment name` then get the `FrontEnd UI App Service name`.

``` bash
# Get the cdnProfile Deployment name name
export CDN_PROFILE_DEPLOYMENT_NAME=$(az deployment group list \
  --resource-group $RESOURCE_GROUP \
  --query "[?starts_with(name, 'cdnProfileDeployment-')].name"  -o tsv)

echo "The Cdn Profile Deployment name is: $CDN_PROFILE_DEPLOYMENT_NAME"


# Get the CDN profile name
export CDN_PROFILE_NAME=$(az deployment group show \
  --name $CDN_PROFILE_DEPLOYMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --query 'properties.outputs.name.value' \
  --output tsv)

echo "The Cdn profile name is: $CDN_PROFILE_NAME"

# Get Front Door UI App Service endpoint host
export FRONT_DOOR_UI_END_POINT_HOST_NAME=$(az afd endpoint list --resource-group  $RESOURCE_GROUP \
  --profile-name $CDN_PROFILE_NAME \
  --query "[?starts_with(name, 'frontend')].hostName" -o tsv)

echo "The Front Door UI App Service Endpoint Host name is: $FRONT_DOOR_UI_END_POINT_HOST_NAME"

```

- To create the app registration:

``` bash

# You need to know your Front Door endpoint for the frontend app service.

# create an app registration for a single tenant with a specific web redirect URI and ID tokens option enabled
export APP_REGISTRATION_ID=$(az ad app create --display-name 'app-Auth-fd-'$FRONT_DOOR_UI_END_POINT_HOST_NAME \
      --web-redirect-uris https://${FRONT_DOOR_UI_END_POINT_HOST_NAME}/.auth/login/aad/callback \
      --sign-in-audience AzureADMyOrg --enable-id-token-issuance true --query appId -o tsv)

```

- After creating the app registration, to create a client secret, run:

```bash

export APP_REGISTRATION_CLIENT_SECRET=$(az ad app credential reset --id $APP_REGISTRATION_ID --append --display-name 'AuthClientSecret' --years 2 --query password -o tsv)

```

- Get the FrontEnd UI `App Service name` also referenced in the params file

```bash
export FRONTEND_UI_DEPLOYMENT_NAME=$(az deployment group list --resource-group $RESOURCE_GROUP --query "[?starts_with(name, 'appserviceUIDeployment-')].name"  -o tsv)

echo "The FrontEnd UI Deployment name is: {$FRONTEND_UI_DEPLOYMENT_NAME"

# Get the FrontEnd UI App Service name
export FRONTEND_UI_WEB_APP_NAME=$(az deployment group show \
  --name $FRONTEND_UI_DEPLOYMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --query 'properties.outputs.appServiceName.value' \
  --output tsv)

echo "The FrontEnd UI App Service name is: $FRONTEND_UI_WEB_APP_NAME"

```

- Finally to deploy the `Entra Auth` configuration run:

``` bash
az deployment group create \
  -n EntraAuthUpdate \
  -g $RESOURCE_GROUP \
  -f infra/azuredeploy-entra-auth.bicep \
  -p infra/azuredeploy-entra-auth.bicepparam -c

```
