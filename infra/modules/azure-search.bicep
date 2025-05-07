param azureSearchName string
param location string 
param azureSearchSKU string
param azureSearchReplicaCount int
param azureSearchPartitionCount int
param azureSearchHostingMode string = 'default'

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

output azureSearchAdminKey string = azureSearch.listAdminKeys().primaryKey
output azureSearchEndpoint string = 'https://${azureSearchName}.search.windows.net'
