metadata name = 'AI Hub'
metadata description = 'Create an Azure AI Hub'
// Creates an Azure AI resource with proxied endpoints for the Azure AI services provider

@description('Azure region of the deployment')
param location string = resourceGroup().location

@description('Name suffix for all resources in the module')
param resourceNameSuffix string

@description('Name of existing AI Services Account')
param existingCognitiveServicesAccountName string = ''
@description('Name of existing Resource Group containing private resources such as AOAI, APIM')
param existingPrivateResourceGroup string = resourceGroup().name
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}

var mergedTags = {
  ...tags
  module: 'aiHub'
}

module dependencies 'aihub-dependencies.bicep' = {
  name: 'aiHubDependenciesDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    resourceNameSuffix: resourceNameSuffix
    location: location
    createCognitiveServices: existingCognitiveServicesAccountName == '' ? true : false
    tags: mergedTags
  }
}
resource existingCognitiveServicesAccount 'Microsoft.CognitiveServices/accounts@2024-05-01-preview' existing = {
  name: existingCognitiveServicesAccountName != ''
    ? existingCognitiveServicesAccountName
    : dependencies.outputs.cognitiveServicesName
  scope: resourceGroup(existingPrivateResourceGroup)
}

resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: 'mlw-ai-${resourceNameSuffix}-001'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    // organization
    friendlyName: 'Botify AI Hub'
    description: 'The Botify Team'
    managedNetwork: {
      isolationMode: 'AllowInternetOutbound'
    }
    // dependent resources
    keyVault: dependencies.outputs.keyvaultId
    storageAccount: dependencies.outputs.storageId
    applicationInsights: dependencies.outputs.applicationInsightsId
    containerRegistry: dependencies.outputs.containerRegistryId
    publicNetworkAccess: 'Enabled'
    v1LegacyMode: true
  }
  kind: 'hub'
  tags: mergedTags

  resource cognitiveServicesConnection 'connections@2024-01-01-preview' = {
    name: existingCognitiveServicesAccountName != '' ? existingCognitiveServicesAccountName : 'botify-aoai'
    properties: {
      category: 'AzureOpenAI'
      target: existingCognitiveServicesAccountName != ''
        ? existingCognitiveServicesAccount.id
        : dependencies.outputs.cognitiveServicesId
      authType: 'ApiKey'
      isSharedToAll: true
      credentials: {
        key: listKeys(existingCognitiveServicesAccount.id, '2021-10-01').key1
      }
      metadata: {
        ApiType: 'Azure'
        ResourceId: existingCognitiveServicesAccount.id
      }
    }
  }
}
output aiHubID string = aiHub.id
