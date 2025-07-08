#!/bin/bash

# Function to list roles and permissions for a given resource
list_roles_permissions() {
  local resource_id=$1
  echo "Roles and permissions for resource: $resource_id"
  az role assignment list --scope "$resource_id" --output json --query '[].{principalName:principalName, roleDefinitionName:roleDefinitionName, scope:scope}'
}

# Main script
resourceGroupName=$1

# Get all AI Foundry resources in the specified resource group
foundry_resources=$(az resource list --resource-group "$resourceGroupName" --resource-type "Microsoft.CognitiveServices/accounts" --query "[].id" -o tsv)

# Get all Storage Accounts in the specified resource group
storage_resources=$(az storage account list --resource-group "$resourceGroupName" --query "[].id" -o tsv)

# List roles and permissions for each AI Foundry resource
for resource_id in $foundry_resources; do
  list_roles_permissions "$resource_id"
done

# List roles and permissions for each Storage Account
for resource_id in $storage_resources; do
  list_roles_permissions "$resource_id"
done

