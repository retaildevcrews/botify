param kvName string
param location string = 'eastus2'
param kvTenantId string = subscription().tenantId
param objectId string = '3619f72b-3848-4361-a4ee-922ea796c9a1'
param objectId2 string = '3619f72b-3848-4361-a4ee-922ea796c9a1'

//Secrets section
@secure()
param blobStorageAccountNameSecret string
@secure()
param blobConnectionStringSecret string
@secure()
param azureOpenAIModelNameSecret string
@secure()
param azureOpenAIEndpointSecret string
@secure()
param azureOpenAIAccountNameSecret string
@secure()
param azureSearchAdminKeySecret string
@secure()
param cognitiveServiceNameSecret string
@secure()
param cognitiveServiceKeySecret string
@secure()
param contentSafetyEndpointSecret string
@secure()
param contentSafetyKeySecret string
@secure()
param cosmosDBAccountNameSecret string
@secure()
param cosmosDBContainerNameSecret string
@secure()
param cosmosDBConnectionStringSecret string
@secure()
param azureSearchEndpointSecret string
@secure()
param appPlanNameSecret string
@secure()
param logAnalyticsWorkspaceNameSecret string
@secure()
param appInsightsConnectionStringSecret string
@secure()
param cosmosDBDatabaseNameSecret string
@secure()
param cosmosDBAccountEndpointSecret string


resource keyVault 'Microsoft.KeyVault/vaults@2021-11-01-preview' = {
  name: kvName
  location: location
  properties: {
    tenantId: kvTenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    createMode: 'default'
    publicNetworkAccess: 'Enabled'
    accessPolicies: [
      {
        objectId: objectId2
        permissions: {
          secrets: [
            'all'
          ]
        }
        tenantId: subscription().tenantId
      }
    ]
    enabledForTemplateDeployment: true
  }
}

resource keyVaultSecret1 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'blobStorageAccountNameSecret'
  properties: {
    value: blobStorageAccountNameSecret
  }
}

resource keyVaultSecret2 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'blobConnectionStringSecret'
  properties: {
    value: blobConnectionStringSecret
  }
}

resource keyVaultSecret3 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azureOpenAIModelNameSecret'
  properties: {
    value: azureOpenAIModelNameSecret
  }
}

resource keyVaultSecret4 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azureOpenAIAccountNameSecret'
  properties: {
    value: azureOpenAIAccountNameSecret
  }
}

resource keyVaultSecret5 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azureOpenAIEndpointSecret'
  properties: {
    value: azureOpenAIEndpointSecret
  }
}

resource keyVaultSecret6 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azureSearchAdminKeySecret'
  properties: {
    value: azureSearchAdminKeySecret
  }
}

resource keyVaultSecret7 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'cognitiveServiceNameSecret'
  properties: {
    value: cognitiveServiceNameSecret
  }
}

resource keyVaultSecret8 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'cognitiveServiceKeySecret'
  properties: {
    value: cognitiveServiceKeySecret
  }
}

resource keyVaultSecret9 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'contentSafetyEndpointSecret'
  properties: {
    value: contentSafetyEndpointSecret
  }
}

resource keyVaultSecret10 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'contentSafetyKeySecret'
  properties: {
    value: contentSafetyKeySecret
  }
}

resource keyVaultSecret11 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'cosmosDBAccountNameSecret'
  properties: {
    value: cosmosDBAccountNameSecret
  }
}

resource keyVaultSecret12 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'cosmosDBContainerNameSecret'
  properties: {
    value: cosmosDBContainerNameSecret
  }
}

resource keyVaultSecret13 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'cosmosDBConnectionStringSecret'
  properties: {
    value: cosmosDBConnectionStringSecret
  }
}

resource keyVaultSecret14 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'azureSearchEndpointSecret'
  properties: {
    value: azureSearchEndpointSecret
  }
}

resource keyVaultSecret15 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'appPlanNameSecret'
  properties: {
    value: appPlanNameSecret
  }
}

resource keyVaultSecret16 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'logAnalyticsWorkspaceNameSecret'
  properties: {
    value: logAnalyticsWorkspaceNameSecret
  }
}

resource keyVaultSecret17 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'appInsightsConnectionStringSecret'
  properties: {
    value: appInsightsConnectionStringSecret
  }
}

resource keyVaultSecret18 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'cosmosDBDatabaseNameSecret'
  properties: {
    value: cosmosDBDatabaseNameSecret
  }
}

resource keyVaultSecret19 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'cosmosDBAccountEndpointSecret'
  properties: {
    value: cosmosDBAccountEndpointSecret
  }
}
