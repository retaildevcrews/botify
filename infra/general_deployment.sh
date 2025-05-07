#!/bin/bash

RESOURCE_GROUP_NAME="rg-botify"
LOCATION="eastus2"
DEPLOYMENT_NAME="botify-dev"
SUBSCRIPTION_ID="/subscriptions/$(az account show --query id -o tsv | tr -d '\r')"

set -x
echo "--------------------------"
echo -e "Creating service principal for botify-dev"
echo "--------------------------"

SERVICE_PRINCIPAL_CREDENTIALS=$(az ad sp create-for-rbac --name botify-dev --role Contributor --scopes $SUBSCRIPTION_ID --query "{appId: appId, password: password, tenant: tenant}" -o json)

SERVICE_PRINCIPAL_APP_ID=$(echo "$SERVICE_PRINCIPAL_CREDENTIALS" | jq -r '.appId')
SERVICE_PRINCIPAL_TENANT_ID=$(echo "$SERVICE_PRINCIPAL_CREDENTIALS" | jq -r '.tenant')
SERVICE_PRINCIPAL_PASSWORD=$(echo "$SERVICE_PRINCIPAL_CREDENTIALS" | jq -r '.password')

APP_OBJECT_ID=$(az ad app list --app-id $SERVICE_PRINCIPAL_APP_ID --query [].id -o tsv)

echo "--------------------------"
echo "Object ID created for the service principal: $APP_OBJECT_ID"
echo "--------------------------"

# Check if there is an open session in Azure CLI
if az account show > /dev/null 2>&1; then
    echo "An active Azure CLI session was detected. Logging out..."
    az logout
else
    echo "No active Azure CLI session detected."
fi

echo "--------------------------"
echo -e "Logging in to Azure CLI using the service principal"
echo "--------------------------"

# Log in to Azure CLI using the service principal
az login --service-principal --username $SERVICE_PRINCIPAL_APP_ID --password ${SERVICE_PRINCIPAL_PASSWORD} --tenant ${SERVICE_PRINCIPAL_TENANT_ID}

# Create required resources
az deployment sub create -n $DEPLOYMENT_NAME -f azuredeploy.bicep -c -p main.parameters.json  --parameters objectId=$APP_OBJECT_ID --location $LOCATION

echo "--------------------------"
echo -e "Resources created in resource group: ${RESOURCE_GROUP_NAME}"
echo "--------------------------"

