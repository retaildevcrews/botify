@description('Required. The Service Principal id of the web app.')
param webAppPrincipalId string

@description('Required. The name of the Azure Container Registry.')
param acrName string

// https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/containers#acrpull
var acrPullId = resourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')

// Existing Azure Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2022-12-01' existing = {
  name: acrName
}

resource webAppAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(webAppPrincipalId, containerRegistry.id, 'acrPull')
  scope: containerRegistry
  properties: {
    principalId: webAppPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullId
  }
}
