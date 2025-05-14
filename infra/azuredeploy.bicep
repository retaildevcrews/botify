@description('Optional, defaults to resource group location. The location of the resources.')
param location string = resourceGroup().location

@description('Optional. The name of our application. It has to be unique. Type a name followed by your resource group name. (<name>-<resourceGroupName>)')
param cognitiveServiceName string = 'cognitive-service-${uniqueString(resourceGroup().id)}'

@description('The name of the Azure Open AI service')
param openaiServiceAccountName string = 'openai-${uniqueString(resourceGroup().id)}'

@description('The name of the Content Safety service')
param contentsafetyName string = 'content-safety-${uniqueString(resourceGroup().id)}'

@description('The model being deployed')
param model string = 'gpt-4'

@description('Version of the model being deployed')
param modelversion string = 'turbo-2024-04-09'

@description('Capacity for specific model used')
param capacity int = 8

@description('Optional. Cosmos DB account name, max length 44 characters, lowercase')
param cosmosDBAccountName string = 'cosmosdb-account-${uniqueString(resourceGroup().id)}'

@description('Optional. The name for the CosmosDB database')
param cosmosDBDatabaseName string = 'cosmosdb-db-${uniqueString(resourceGroup().id)}'

@description('Optional. The name for the CosmosDB database container')
param cosmosDBContainerName string = 'cosmosdb-container-${uniqueString(resourceGroup().id)}'

@description('Optional. The name of the Blob Storage account')
param blobStorageAccountName string = 'blobstorage${uniqueString(resourceGroup().id)}'

@description('Optional. Service name must only contain lowercase letters, digits or dashes, cannot use dash as the first two or last one characters, cannot contain consecutive dashes, and is limited between 2 and 60 characters in length.')
@minLength(2)
@maxLength(60)
param azureSearchName string = 'cog-search-${uniqueString(resourceGroup().id)}'

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

param appPlanName string = 'asp-${uniqueString(resourceGroup().id)}'
param logAnalyticsWorkspace string = 'la-${uniqueString(resourceGroup().id)}'

var cognitiveServiceSKU = 'S0'
var appPlanSkuName = 'S1'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspace
  location: location
  properties: {
    sku: {
      name: 'pergb2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'app-insights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource appServicePlan 'Microsoft.Web/serverfarms@2021-03-01' = {
  name: appPlanName
  location: location
  sku: {
    name: appPlanSkuName
    capacity: 1
  }
}

resource diagnosticLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: appServicePlan.name
  scope: appServicePlan
  properties: {
    workspaceId: logAnalytics.id
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
      }
    ]
  }
}

resource azureSearch 'Microsoft.Search/searchServices@2021-04-01-Preview' = {
  name: azureSearchName
  location: location
  sku: {
    name: azureSearchSKU
  }
  properties: {
    replicaCount: azureSearchReplicaCount
    partitionCount: azureSearchPartitionCount
    hostingMode: azureSearchHostingMode
    semanticSearch: 'standard'
  }
}

resource cognitiveService 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: cognitiveServiceName
  location: location
  sku: {
    name: cognitiveServiceSKU
  }
  kind: 'CognitiveServices'
  properties: {
    apiProperties: {
      statisticsEnabled: false
    }
  }
}

resource openAIService 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openaiServiceAccountName
  location: location
  sku: {
    name: cognitiveServiceSKU
  }
  kind: 'AIServices'
  properties: {
    apiProperties: {
      statisticsEnabled: true
    }
  }
}

resource azopenaideployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAIService
  name: modeldeploymentname
  properties: {
      model: {
          format: 'OpenAI'
          name: model
          version: modelversion
      }
  }
  sku: {
    name: 'Standard'
    capacity: capacity
  }
}

resource contentsafetyaccount 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: contentsafetyName
  location: location
  kind: 'ContentSafety'
  sku: {
    name: cognitiveServiceSKU
  }
  properties: {
  }
}

resource cosmosDBAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: cosmosDBAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
      }
    ]
    enableFreeTier: false
    isVirtualNetworkFilterEnabled: false
    publicNetworkAccess: 'Enabled'
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
}

resource cosmosDBDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  parent: cosmosDBAccount
  name: cosmosDBDatabaseName
  location: location
  properties: {
    resource: {
      id: cosmosDBDatabaseName
    }
  }
}

resource cosmosDBContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: cosmosDBDatabase
  name: cosmosDBContainerName
  location: location
  properties: {
    resource: {
      id: cosmosDBContainerName
      partitionKey: {
        paths: [
          '/user_id'
        ]
        kind: 'Hash'
        version: 2
      }
      defaultTtl: 1000
    }
  }
}

resource blobStorageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: blobStorageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
}

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: blobStorageAccount
  name: 'default'
}

resource blobStorageContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [for containerName in ['books', 'cord19', 'mixed'] : {
  parent: blobServices
  name: containerName
}]

output blobStorageAccountName string = blobStorageAccountName
output blobConnectionString string = 'DefaultEndpointsProtocol=https;AccountName=${blobStorageAccountName};AccountKey=${blobStorageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
output azureOpenAIModelName string = azopenaideployment.properties.model.name
output azureOpenAIEndpoint string = openAIService.properties.endpoint

output azureOpenAIAccountName string = openaiServiceAccountName

output azureSearchAdminKey string = azureSearch.listAdminKeys().primaryKey

output cognitiveServiceName string = cognitiveServiceName
output cognitiveServiceKey string = cognitiveService.listKeys().key1

output contentSafetyEndpoint string = contentsafetyaccount.properties.endpoint
output contentSafetyKey string = contentsafetyaccount.listKeys().key1

output cosmosDBAccountName string = cosmosDBAccountName
output cosmosDBContainerName string = cosmosDBContainerName
output cosmosDBConnectionString string = 'AccountEndpoint=${cosmosDBAccount.properties.documentEndpoint};AccountKey=${cosmosDBAccount.listKeys().primaryMasterKey}'
output azureSearchEndpoint string = 'https://${azureSearchName}.search.windows.net'

output appPlanName string = appPlanName
output logAnalyticsWorkspaceName string = logAnalyticsWorkspace
output appInsightsConnectionString string = appInsights.properties.ConnectionString

output cosmosDBDatabaseName string = cosmosDBDatabaseName
output cosmosDBAccountEndpoint string = cosmosDBAccount.properties.documentEndpoint
