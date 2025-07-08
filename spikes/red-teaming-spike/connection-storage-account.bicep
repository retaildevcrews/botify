/*
Connections enable your AI applications to access tools and objects managed elsewhere in or outside of Azure.

This example demonstrates how to add an Azure Storage connection.
*/
param aiFoundryName string = 'foundry-botify'
param connectedResourceName string = 'foundrybstorage318e1686c'
param location string = 'eastus2'

// Whether to create a new Azure AI Search resource
@allowed([
  'new'
  'existing'
])
param newOrExisting string = 'new'

// Refers your existing Azure AI Foundry resource
resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: aiFoundryName
  scope: resourceGroup()
}

// Conditionally refers your existing Azure Storage account
resource existingStorage 'Microsoft.Storage/storageAccounts@2024-01-01' existing = if (newOrExisting == 'existing') {
  name: connectedResourceName
}

// Creates the Azure Foundry connection to your Azure Storage account
resource connection 'Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview' = {
  name: '${aiFoundryName}-storage'
  parent: aiFoundry
  properties: {
    category: 'AzureStorageAccount'
    target: existingStorage.id
    authType: 'AccountKey'
    isSharedToAll: true
    credentials: {
      key: string(existingStorage.listKeys().keys)
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: existingStorage.id
    }
  }
}
