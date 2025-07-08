param aiFoundryName string
param location string
param createCICDIdentity bool = false

resource aiFoundry 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: aiFoundryName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  properties: {
    allowProjectManagement: true
    customSubDomainName: aiFoundryName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource aiProject 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  name: '${aiFoundryName}-proj'
  parent: aiFoundry
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

// Create Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: '${aiFoundryName}${substring(uniqueString(resourceGroup().id), 0, 5)}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}

// Role assignment for Storage Blob Data Contributor
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, aiProject.id, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe') // Storage Blob Data Contributor
    principalId: aiProject.identity.principalId
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

// Create connection between AI Foundry and Storage Account
resource connection 'Microsoft.CognitiveServices/accounts/connections@2025-04-01-preview' = {
  name: '${aiFoundryName}-storage'
  parent: aiFoundry
  properties: {
    category: 'AzureStorageAccount'
    target: storageAccount.id
    isSharedToAll: true
    authType: 'AAD'
    metadata: {
      ApiType: 'Azure'
      ResourceId: storageAccount.id
    }
  }
}

// Create CICD Identity if required
resource cicdIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2025-01-31-preview' = if (createCICDIdentity) {
  location: location
  name: '${aiFoundryName}-cicd-mi'
}

// Role assignment for CICD Identity to have Azure AI Admin access
resource cicdAzureAIAdminRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (createCICDIdentity) {
  name: guid(aiFoundry.id, cicdIdentity.id, 'b78c5d69-af96-48a3-bf8d-a8b4d589de94')
  scope: aiFoundry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b78c5d69-af96-48a3-bf8d-a8b4d589de94') // Azure AI Admin
    principalId: cicdIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Role assignment for CICD Identity to have Cognitive Services User access
resource cicdCognitiveServicesUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (createCICDIdentity) {
  name: guid(aiFoundry.id, cicdIdentity.id, 'a97b65f3-24c7-4388-baec-2e87135dc908')
  scope: aiFoundry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908') // Cognitive Services User
    principalId: cicdIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource cicdIdentityCreds 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2025-01-31-preview' = if (createCICDIdentity) {
  parent: cicdIdentity
  name: 'gh-action-credentials'
  properties: {
    audiences: [
      'api://AzureADTokenExchange'
    ]
    issuer: 'https://token.actions.githubusercontent.com'
    subject: 'repo:retaildevcrews/botify:ref:refs/heads/red-teaming-agent-cicd'
  }
}
