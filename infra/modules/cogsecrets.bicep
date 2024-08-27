metadata name = 'Cognitive Services Key Vault Secrets Module'
metadata description = 'This module retrieves secret values from an existing Cognitive Services account and stores them in an existing Key Vault.'

@description('The name of the existing Cognitive Services account.')
param cognitiveServicesAccountName string

@description('The name of the existing Key Vault.')
param vaultName string

@description('The name of the existing Azure ApiKey Secret associated to the cognitive service.')
param apiKeySecretName string

@description('The name of the existing Azure EndPoint Secret associated to the cognitive service.')
param endPointSecretName string

resource cognitiveServicesAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: cognitiveServicesAccountName
}

// Set Vault Secrets from deployed cognitiveServicesAccount
resource keyVaultResource 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: vaultName

  resource apiKeySecret 'secrets' = {  
    name: apiKeySecretName
    properties: {
      value: cognitiveServicesAccount.listKeys().key1
    }
  }
  resource endpointSecret 'secrets' = {  
    name: endPointSecretName
    properties: {
      value: cognitiveServicesAccount.properties.endpoint
    }
  }
}
