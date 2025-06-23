#!/bin/bash

RESOURCE_GROUP_NAME="rg-botify"
CONTAINER_APPS_ENV_NAME="container-app-env-c4gsjupt4nyue"
AZURE_CONTAINER_REGISTRY_NAME="caec8ebe2830acr"

cd ..

cd apps

servicesList=("bot-service" "collector" "frontend" "tokenservice")

az acr login --name $AZURE_CONTAINER_REGISTRY_NAME --username $AZURE_CONTAINER_REGISTRY_NAME --password iV61OFMJU/IjaSYBzj20nNqTyiyNV1RHfZ21twRy2S+ACRBJ7UYG

az acr show --name $AZURE_CONTAINER_REGISTRY_NAME --query loginServer --output tsv

# Frontend service
cd frontend
docker build -t $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/frontend:latest .
docker push $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/frontend:latest

az containerapp up --name frontend --resource-group $RESOURCE_GROUP_NAME --environment $CONTAINER_APPS_ENV_NAME --image $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/frontend:latest --target-port 8000 --ingress external

# Bot Service
cd bot-service
docker build -t $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/bot-service:latest .
docker push $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/bot-service:latest

az containerapp up --name bot-service --resource-group $RESOURCE_GROUP_NAME --environment $CONTAINER_APPS_ENV_NAME --image $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/bot-service:latest

# Collector Service
cd collector
docker build -t $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/collector:latest .
docker push $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/collector:latest

az containerapp up --name collector --resource-group $RESOURCE_GROUP_NAME --environment $CONTAINER_APPS_ENV_NAME --image $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/collector:latest

# Token Service
cd tokenservice
docker build -t $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/tokenservice:latest .
docker push $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/tokenservice:latest

az containerapp up --name tokenservice --resource-group $RESOURCE_GROUP_NAME --environment $CONTAINER_APPS_ENV_NAME --image $AZURE_CONTAINER_REGISTRY_NAME.azurecr.io/tokenservice:latest


