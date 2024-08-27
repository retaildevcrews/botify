metadata name = 'CosmosDB Key Vault Secrets Module'
metadata description = 'This module retrieves secret values from an existing CosmosDB account and stores them in an existing Key Vault.'

@description('The name of the existing CosmosDB account.')
param cosmosDBAccountName string

@description('The name of the existing Key Vault.')
param vaultName string

resource cosmosDBAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' existing = {
  name: cosmosDBAccountName
}

// Set Vault Secrets from deployed cognitiveServicesAccount
resource keyVaultResource 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: vaultName

  resource apiKeySecret 'secrets' = {  
    name: 'AzureCosmosDBConnectionString'  
    properties: {
      value: 'AccountEndpoint=${cosmosDBAccount.properties.documentEndpoint};AccountKey=${cosmosDBAccount.listKeys().primaryMasterKey}'
    }
  }
  resource endpointSecret 'secrets' = {  
    name: 'AzureCosmosDBEndpoint'  
    properties: {
      value: cosmosDBAccount.properties.documentEndpoint
    }
  }
}

