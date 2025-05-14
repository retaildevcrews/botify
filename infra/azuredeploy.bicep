targetScope = 'subscription'

@description('The name of the resource group to create.')
param resourceGroupName string

@description('Optional, defaults to resource group location. The location of the resources.')
param location string = 'eastus2'

@description('The objectId of the user, group, or service principal to grant access.')
param objectId string

@description('Optional. The name of our application. It has to be unique. Type a name followed by your resource group name. (<name>-<resourceGroupName>)')
param cognitiveServiceName string = 'cognitive-service-${uniqueString(subscription().id)}'

@description('The name of the Azure Open AI service')
param openaiServiceAccountName string = 'openai-${uniqueString(subscription().id)}'

@description('The model being deployed')
param model string = 'gpt-4'

@description('Version of the model being deployed')
param modelversion string = 'turbo-2024-04-09'

@description('Capacity for specific model used')
param capacity int = 8

@description('Optional. Cosmos DB account name, max length 44 characters, lowercase')
param cosmosDBAccountName string = 'cosmosdb-account-${uniqueString(subscription().id)}'

@description('Optional. The name for the CosmosDB database')
param cosmosDBDatabaseName string = 'cosmosdb-db-${uniqueString(subscription().id)}'

@description('Optional. The name for the CosmosDB database container')
param cosmosDBContainerName string = 'cosmosdb-container-${uniqueString(subscription().id)}'

@description('Optional. The name of the Blob Storage account')
param blobStorageAccountName string = 'blobstorage${uniqueString(subscription().id)}'

@description('Optional. Service name must only contain lowercase letters, digits or dashes, cannot use dash as the first two or last one characters, cannot contain consecutive dashes, and is limited between 2 and 60 characters in length.')
@minLength(2)
@maxLength(60)
param azureSearchName string = 'cog-search-${uniqueString(subscription().id)}'

@description('Optional, defaults to standard. The pricing tier of the search service you want to create (for example, basic or standard).')
@allowed([
  'free'
  'basic'
  'standard'
  'standard2'
  'standard3'
  'storage_optimized_l1'
  'storage_optimized_l2'
])
param azureSearchSKU string = 'standard'

@description('Optional, defaults to 1. Replicas distribute search workloads across the service. You need at least two replicas to support high availability of query workloads (not applicable to the free tier). Must be between 1 and 12.')
@minValue(1)
@maxValue(12)
param azureSearchReplicaCount int = 1

@description('Optional, defaults to 1. Partitions allow for scaling of document count as well as faster indexing by sharding your index over multiple search units. Allowed values: 1, 2, 3, 4, 6, 12.')
@allowed([
  1
  2
  3
  4
  6
  12
])
param azureSearchPartitionCount int = 1

@description('Optional, defaults to default. Applicable only for SKUs set to standard3. You can set this property to enable a single, high density partition that allows up to 1000 indexes, which is much higher than the maximum indexes allowed for any other SKU.')
@allowed([
  'default'
  'highDensity'
])
param azureSearchHostingMode string = 'default'

@description('Name of the Azure Open AI deployment')
@allowed([
  'gpt-4o-mini'
  'gpt-4o'
  'o1-mini'
])
param modeldeploymentname string = 'gpt-4o'

param appPlanName string = 'asp-${uniqueString(subscription().id)}'
param logAnalyticsWorkspace string = 'la-${uniqueString(subscription().id)}'
param keyvaultName string = 'kv-${uniqueString(subscription().id)}'

var cognitiveServiceSKU = 'S0'
var appPlanSkuName = 'S1'

// Resource group creation
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
}

// Modules creation
module keyVault 'modules/key-vault.bicep' = {
  name: 'keyVaultModule'
  scope: resourceGroup
  params: {
    kvName: keyvaultName
    location: location
    kvTenantId: subscription().tenantId
    objectId: objectId
    blobStorageAccountNameSecret: blobStorageAccountName
    blobConnectionStringSecret: blobStorageModule.outputs.blobStorageAccountString
    azureOpenAIModelNameSecret: model
    azureOpenAIEndpointSecret: openAIServiceModule.outputs.azureOpenAIEndpoint
    azureOpenAIAccountNameSecret: openaiServiceAccountName
    azureSearchAdminKeySecret: azureSearch.outputs.azureSearchAdminKey
    cognitiveServiceNameSecret: cognitiveServiceName
    cognitiveServiceKeySecret: cognitiveServiceModule.outputs.cognitiveServiceKey
    contentSafetyEndpointSecret: openAIServiceModule.outputs.azureOpenAIEndpoint
    contentSafetyKeySecret: openAIServiceModule.outputs.contentSafetyKey
    cosmosDBAccountNameSecret: cosmosDBModule.outputs.cosmosDBAccountName
    cosmosDBContainerNameSecret: cosmosDBModule.outputs.cosmosDBContainerName
    cosmosDBConnectionStringSecret: cosmosDBModule.outputs.cosmosDBConnectionString
    azureSearchEndpointSecret: azureSearch.outputs.azureSearchEndpoint
    appPlanNameSecret: appPlanModule.outputs.appServicePlanName
    logAnalyticsWorkspaceNameSecret: appInsights.outputs.workspaceName
    appInsightsConnectionStringSecret: appInsights.outputs.connectionString
    cosmosDBDatabaseNameSecret: cosmosDBDatabaseName
    cosmosDBAccountEndpointSecret: cosmosDBModule.outputs.cosmosDBAccountEndpoint
  }
}

module appInsights 'modules/app-insights.bicep' = {
  name: 'appInsightsModule'
  scope: resourceGroup
  params: {
    location: location
    appInsightsName: 'app-insights-${uniqueString(subscription().id)}'
    logAnalyticsName: logAnalyticsWorkspace
  }
}

module appPlanModule 'modules/app-service.bicep' = {
  name: 'appServicePlanModule'
  scope: resourceGroup
  params: {
    appPlanName: appPlanName
    location: location
    appPlanSkuName: appPlanSkuName
    logAnalyticsId: appInsights.outputs.workspaceId
  }
}

module azureSearch 'modules/azure-search.bicep' = {
  name: 'azureSearchModule'
  scope: resourceGroup
  params: {
    azureSearchName: azureSearchName
    location: location
    azureSearchSKU: azureSearchSKU
    azureSearchReplicaCount: azureSearchReplicaCount
    azureSearchPartitionCount: azureSearchPartitionCount
    azureSearchHostingMode: azureSearchHostingMode
  }
}

module cognitiveServiceModule 'modules/cognitive-services.bicep' = {
  name: 'cognitiveServiceModule'
  scope: resourceGroup
  params: {
    cognitiveServiceName: cognitiveServiceName
    location: location
    cognitiveServiceSKU: cognitiveServiceSKU
  }
}

module openAIServiceModule 'modules/open-ai.bicep' = {
  name: 'openAIServiceModule'
  scope: resourceGroup
  params: {
    openaiServiceAccountName: openaiServiceAccountName
    location: location
    cognitiveServiceSKU: cognitiveServiceSKU
    modeldeploymentname: modeldeploymentname
    model: model
    modelversion: modelversion
    capacity: capacity
  }
}

module cosmosDBModule 'modules/cosmos-db.bicep' = {
  name: 'cosmosDBModule'
  scope: resourceGroup
  params: {
    cosmosDBAccountName: cosmosDBAccountName
    location: location
    cosmosDBDatabaseName: cosmosDBDatabaseName
    cosmosDBContainerName: cosmosDBContainerName
  }
}

module blobStorageModule 'modules/blob-storage.bicep' = {
  name: 'blobStorageModule'
  scope: resourceGroup
  params: {
    blobStorageAccountName: blobStorageAccountName
    location: location
  }
}
