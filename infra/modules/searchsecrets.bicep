metadata name = 'Azure AI Search Secrets Module'
metadata description = 'This module retrieves secret values from an existing AI Search Service and stores them in an existing Key Vault.'

@description('The name of the existing AI Search Service.')
param searchServiceName string

@description('The name of the existing Key Vault.')
param vaultName string

resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' existing = {
  name: searchServiceName
}

// Set Vault Secrets from deployed AI Search Service
resource keyVaultResource 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: vaultName

  resource azureSearchKey 'secrets' = {  
    name: 'AzureSearchKey'  
    properties: {
      value: searchService.listAdminKeys().primaryKey
    }
  }
  resource azureSearchEndpoint 'secrets' = {  
    name: 'AzureSearchEndpoint'  
    properties: {
      value: 'https://${searchService.name}.search.windows.net'
    }
  }
}

