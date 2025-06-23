#!/bin/bash

RESOURCE_GROUP_NAME="rg-botify"
CONTAINER_APPS_ENV_NAME="container-app-env-c4gsjupt4nyue"

cd ..

cd apps

servicesList=("bot-service" "collector" "frontend" "tokenservice")

az acr login --name acr25ehy3lawfnks

az acr show --name acr25ehy3lawfnks --query loginServer --output tsv

for service in "${servicesList[@]}"; do 
  cd ${service}
  docker build -t acr25ehy3lawfnks.azurecr.io/${service}:latest .
  docker push acr25ehy3lawfnks.azurecr.io/${service}:latest
  if [ "${service}" = "frontend" ]; then
    az containerapp up --name ${service} --resource-group ${RESOURCE_GROUP_NAME} --environment ${CONTAINER_APPS_ENV_NAME}  --target-port 8000 --ingress external --source .
  else
    az containerapp up --name ${service} --resource-group ${RESOURCE_GROUP_NAME} --environment ${CONTAINER_APPS_ENV_NAME} --source .
  fi
done

