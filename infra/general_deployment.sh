#!/bin/bash

RESOURCE_GROUP_NAME="rg-botify"
LOCATION="eastus2"
DEPLOYMENT_NAME="botify-dev"

SUB_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv | tr -d '\r')

echo "--------------------------"
echo -e "Creating resources in group: ${RESOURCE_GROUP_NAME}"
echo "--------------------------"

az deployment sub create -n $DEPLOYMENT_NAME -f azuredeploy.bicep -c -p main.parameters.json  --parameters objectId=$SUB_OBJECT_ID --location $LOCATION

echo "--------------------------"
echo -e "Resources created in resource group: ${RESOURCE_GROUP_NAME}"
echo "--------------------------"

az keyvault set-policy --name kv-la7pegqx4rdwk --object-id $SUB_OBJECT_ID --secret-permissions get list set delete recover backup restore purge

APPLICATIONINSIGHTS_CONNECTION_STRING=$(az keyvault secret show --vault-name kv-la7pegqx4rdwk --name appInsightsConnectionStringSecret --query value -o tsv)

export APPLICATIONINSIGHTS_CONNECTION_STRING

echo $APPLICATIONINSIGHTS_CONNECTION_STRING

cat <<EOF > ../apps/credentials.env
APPLICATIONINSIGHTS_CONNECTION_STRING="${APPLICATIONINSIGHTS_CONNECTION_STRING}"
EOF

cd ..

cd apps

docker compose up
