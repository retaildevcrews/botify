#!/bin/bash

RESOURCE_GROUP_NAME="rg-botify"
CONTAINER_APPS_ENV_NAME="container-app-env-25ehy3lawfnks"

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
    az containerapp up --name ${service} --resource-group ${RESOURCE_GROUP_NAME} --environment ${CONTAINER_APPS_ENV_NAME} --image acr25ehy3lawfnks.azurecr.io/${service}:latest --target-port 80 --ingress external
  else
    az containerapp up --name ${service} --resource-group ${RESOURCE_GROUP_NAME} --environment ${CONTAINER_APPS_ENV_NAME} --image acr25ehy3lawfnks.azurecr.io/${service}:latest
  fi
done

