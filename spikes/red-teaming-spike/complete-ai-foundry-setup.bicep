/*
Complete AI Foundry setup including:
- Cognitive Services (AI Foundry) resource
- AI Foundry project
- Storage Account
- Connection between Cognitive Services and Storage Account
*/

// Parameters for resource names
param aiFoundryName string = 'testbotify'
param location string = 'eastus2'

// Create Cognitive Services (AI Foundry) resource
resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: aiFoundryName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: aiFoundryName
    publicNetworkAccess: 'Enabled'
    allowProjectManagement: true
  }
}

// Create User Assigned Managed Identity
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${aiFoundryName}-mi'
  location: location
}

// Create AI Foundry project
resource aiFoundryProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  name: '${aiFoundryName}-redTeam-project'
  parent: aiFoundry
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
}

// Create Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: '${aiFoundryName}${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}

// Role assignment for Storage Blob Data Contributor
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, managedIdentity.id, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Role assignment for current user to have Cognitive Services Contributor access
resource userRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiFoundry.id, deployer().objectId, '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68')
  scope: aiFoundry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68') // Cognitive Services Contributor
    principalId: deployer().objectId
    principalType: 'User'
  }
}

// // Create connection between AI Foundry and Storage Account
// resource connection 'Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview' = {
//   name: '${aiFoundryName}-storage'
//   parent: aiFoundry
//   properties: {
//     category: 'AzureStorageAccount'
//     target: storageAccount.id
//     isSharedToAll: true
//     authType: 'ManagedIdentity'
//     credentials: {
//       clientId: managedIdentity.properties.clientId
//       resourceId: managedIdentity.id
//     }
//     metadata: {
//       ApiType: 'Azure'
//       ResourceId: storageAccount.id
//     }
//   }
// }

// // Outputs
// output aiFoundryId string = aiFoundry.id
// output aiFoundryEndpoint string = aiFoundry.properties.endpoint
// output projectId string = aiFoundryProject.id
// output storageAccountId string = storageAccount.id
// output connectionId string = connection.id
// output managedIdentityId string = managedIdentity.id
// output managedIdentityClientId string = managedIdentity.properties.clientId
// output managedIdentityClientId string = managedIdentity.properties.clientId
