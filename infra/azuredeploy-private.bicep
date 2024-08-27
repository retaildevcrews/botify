metadata name = 'Chatbot Private Networking'
metadata description = 'This module deploys private networking resources for hosting chatbots'

@description('The Azure region where resources will be deployed. Defaults to the resource group location.')
param location string = resourceGroup().location
@description('When true, a jumpbox VM and bastion host will be deployed or updated. Defaults to false.')
param jumpboxEnabled bool = false
@description('The username for the jumpbox VM. Defaults to jumpboxadmin')
param jumpboxAdminUsername string = 'jumpboxadmin'
@description('Name suffix for all resources in the module. Format: project-environment-region, Ex: chatbot-dev-use2')
@minLength(3)
param resourceNameSuffix string
@description('The principal ID of the user or group that will be granted admin access to the Key Vault. Defaults to none')
param keyVaultAdminPrincipal string = ''
@description('When true, a cosmos database will be deployed or updated. Defaults to true.')
param cosmosEnabled bool = true
@description('The name of an existing Key Vault. If provided, the module will look in the existing Key Vault for app secrets.')
param existingKeyVaultName string = ''
@description('Email address to receive alerts. If not provided, no alerts or alert group will be created.')
param alertsEmail string = ''
@description('Secrets to be stored in the deployed Key Vault. Defaults to an empty object.')
@secure()
param vaultSecrets object = {}
@description('Array of cognitive services model deployments. Defaults to a single gpt-4o model deployment')
param cognitiveServicesModelDeployments array = [
  {
    name: 'gpt-4o'
    sku: {
      name: 'Standard'
      capacity: 70
    }
    model: {
      name: 'gpt-4o'
      format: 'OpenAI'
      version: '2024-05-13'
    }
    raiPolicyName: 'Microsoft.Default'
  }
  {
    name: 'text-embedding-ada-002'
    sku: {
      name: 'Standard'
      capacity: 120
    }
    model: {
      name: 'text-embedding-ada-002'
      format: 'OpenAI'
      version: '2'
    }
    raiPolicyName: 'Microsoft.Default'
  }
]
@description('Determines whether key based authentication is disabled for the Cognitive Services Account. Defaults to true.')
param cognitiveServicesLocalAuthDisabled bool = true
@description('When true, Azure API Management will be deployed or updated. Defaults to true.')
param apimEnabled bool = true
@minLength(5)
@maxLength(50)
@description('The container registry name. Character limit: 5-50. Valid characters: Alphanumerics. Ex: chatbotdevuse2')
param acrName string = 'acr${uniqueString(resourceNameSuffix)}'
@description('The name of an existing ACR. If provided, the module will use the existing ACR to pull container images')
param existingAcrName string = ''
@allowed([
  'Enabled'
  'Disabled'
])
@description('Enables or disables public network access to the Azure API Management service. Must be enabled for initial deployment.')
param apimPublicNetworkAccess string = 'Enabled'
@description('The name of Cosmos container name.')
param cosmosContainerName string = 'chatHistory'
@description('When true, AI Studio will be deployed or updated. Defaults to false.')
param aiStudioEnabled bool = false
@description('The name of the resource group where AI Studio will be deployed. Defaults to the resource group name.')
param aiStudioResourceGroupName string = resourceGroup().name
@allowed([
  'Prevention'
  'Detection'
])
@description('The mode of the WAF policy. Defaults to Detection.')
param wafPolicyMode string = 'Detection'
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}

// Allow the user to provide secret values for existing resources
var useExistingCognitiveServices = (contains(vaultSecrets, 'AzureOpenAIEndpoint') && contains(
    vaultSecrets,
    'AzureOpenAIApiKey'
  ))
  ? true
  : false

var useExistingCosmosDBSecrets = (contains(vaultSecrets, 'AzureCosmosDBEndpoint') && contains(
    vaultSecrets,
    'AzureCosmosDBConnectionString'
  ))
  ? true
  : false

var useExistingSearchSecrets = (contains(vaultSecrets, 'AzureSearchEndpoint') && contains(
  vaultSecrets,
  'AzureSearchKey'
))

// Deploys a vnet, subnets and required NSGs
module network 'modules/networking.bicep' = {
  name: 'networkingDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    resourceNameSuffix: resourceNameSuffix
    location: location
    tags: tags
  }
}

// Deploys private DNS zones for ACR, APIM, and App Service
module privateDnsZones 'modules/privatedns.bicep' = {
  name: 'privatednsDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    virtualNetworkResourceId: network.outputs.virtualNetworkResourceId
    tags: tags
  }
}

// Deploys Azure Key Vault
module keyvault 'br/public:avm/res/key-vault/vault:0.6.1' = if (existingKeyVaultName == '') {
  name: 'keyvaultDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: 'kv-${resourceNameSuffix}-001'
    enableVaultForDeployment: true
    enableVaultForTemplateDeployment: true
    enableRbacAuthorization: true
    publicNetworkAccess: 'Disabled'
    secrets: [
      for secret in items(vaultSecrets): {
        name: secret.key
        value: secret.value
      }
    ]
    privateEndpoints: [
      {
        privateDnsZoneResourceIds: [
          privateDnsZones.outputs.keyvaultPrivateDnsZoneId
        ]
        subnetResourceId: network.outputs.privateEndpointSubnetResourceId
        privateDnsZoneGroupName: 'default'
      }
    ]
    tags: tags
  }
}

// Grants a user or group admin access to the Key Vault
module keyvaultAdminRbacAssignment 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.0' = if (keyVaultAdminPrincipal != '') {
  name: 'keyvaultAdminRbacAssignment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    resourceId: keyvault.outputs.resourceId
    principalId: keyVaultAdminPrincipal
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '00482a5a-887f-4fb3-b363-3b7fe8e74483')
  }
}

// Deploys a jumpbox VM and bastion host
module jumpbox 'modules/jumpbox.bicep' = if (jumpboxEnabled) {
  name: 'jumpboxDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    resourceNameSuffix: resourceNameSuffix
    virtualNetworkResourceId: network.outputs.virtualNetworkResourceId
    subnetResourceId: network.outputs.jumpboxSubnetResourceId
    jumpboxAdminUsername: jumpboxAdminUsername
    jumpboxSecretName: 'jumpboxSecret'
    existingKeyvaultName: existingKeyVaultName != '' ? existingKeyVaultName : keyvault.outputs.name
    tags: tags
  }
}

// Deploys Cognitive Services Account for OpenAI
module cognitiveServicesAccount 'br/public:avm/res/cognitive-services/account:0.5.3' = {
  name: 'cognitiveServicesAccountDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: 'cog-${resourceNameSuffix}-001'
    location: location
    kind: 'OpenAI'
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
      ipRules: []
    }
    customSubDomainName: resourceNameSuffix
    disableLocalAuth: cognitiveServicesLocalAuthDisabled
    managedIdentities: {
      systemAssigned: true
    }
    roleAssignments: [
      {
        roleDefinitionIdOrName: 'Cognitive Services OpenAI Contributor'
        principalId: searchUserAssignedIdentity.outputs.principalId
      }
      {
        roleDefinitionIdOrName: 'Cognitive Services Contributor'
        principalId: searchUserAssignedIdentity.outputs.principalId
      }
    ]
    privateEndpoints: [
      {
        subnetResourceId: network.outputs.privateEndpointSubnetResourceId
        privateDnsZoneResourceIds: [
          privateDnsZones.outputs.openAIPrivateDnsZoneId
        ]
        privateDnsZoneGroupName: 'default'
      }
    ]
    deployments: cognitiveServicesModelDeployments
    tags: tags
  }
}

// Store sensitive Cognitive Services Account values in Key Vault
module cognitiveServicesSecrets 'modules/cogsecrets.bicep' = if (!useExistingCognitiveServices) {
  name: 'cognitiveServicesSecretsDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    cognitiveServicesAccountName: cognitiveServicesAccount.outputs.name
    vaultName: existingKeyVaultName != '' ? existingKeyVaultName : keyvault.outputs.name
    apiKeySecretName: 'AzureOpenAIApiKey'
    endPointSecretName: 'AzureOpenAIEndpoint'
  }
}

// Deploys Azure API Management
module apim 'modules/apim.bicep' = if (apimEnabled) {
  name: 'apimDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    resourceNameSuffix: resourceNameSuffix
    location: location
    existingKeyVaultName: existingKeyVaultName == '' ? keyvault.outputs.name : existingKeyVaultName
    publicNetworkAccess: apimPublicNetworkAccess
    subnetResourceId: network.outputs.apimSubnetResourceId
    tags: tags
  }
}

// Deploys Azure Container Registry
module registry 'br/public:avm/res/container-registry/registry:0.1.1' = if (existingAcrName == '') {
  name: 'registryDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    // Required parameters
    name: acrName
    // Non-required parameters
    acrSku: 'Premium'
    privateEndpoints: [
      {
        privateDnsZoneResourceIds: [
          privateDnsZones.outputs.acrPrivateDnsZoneId
        ]
        subnetResourceId: network.outputs.privateEndpointSubnetResourceId
        privateDnsZoneGroupName: 'default'
      }
    ]
    tags: tags
  }
}

// Deploys a cosmos database for chat history
module cosmosDBAccount 'modules/cosmosdb.bicep' = if (cosmosEnabled) {
  name: 'cosmosDBDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    resourceNameSuffix: resourceNameSuffix
    containerName: cosmosContainerName
    privateDnsZoneResourceId: privateDnsZones.outputs.cosmosDBPrivateDnsZoneId
    subnetResourceId: network.outputs.privateEndpointSubnetResourceId
    tags: tags
  }
}

// Deploys Log Analytics Workspace, App Insights, and Alerts
module logging 'modules/logging-and-alerts.bicep' = {
  name: 'loggingDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    resourceNameSuffix: resourceNameSuffix
    location: location
    alertsEmail: alertsEmail
    tags: tags
  }
}

// Store sensitive CosmosDB values in Key Vault
module cosmosDBSecrets 'modules/cosmosdbsecrets.bicep' = if (!useExistingCosmosDBSecrets) {
  name: 'cosmosDBSecretsDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    cosmosDBAccountName: cosmosDBAccount.outputs.cosmosDBAccountName
    vaultName: existingKeyVaultName != '' ? existingKeyVaultName : keyvault.outputs.name
  }
}

// Create an identity for search to access other resources
module searchUserAssignedIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.2.1' =  {
  name: 'userAssignedIdentityDeployment-${uniqueString(resourceGroup().id, 'search')}'
  params: {
    location: location
    name: 'umi-search-${resourceNameSuffix}-001'
  }
}
// Deploys Azure AI Search Service
module searchService 'modules/search.bicep' = {
  name: 'searchServiceDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    userAssignedIdentity: searchUserAssignedIdentity.outputs.resourceId
    resourceNameSuffix: resourceNameSuffix
    location: location
    privateDnsZoneId: privateDnsZones.outputs.searchPrivateDnsZoneId
    privateEndpointSubnetId: network.outputs.privateEndpointSubnetResourceId
    cognitiveServicesResourceId: cognitiveServicesAccount.outputs.resourceId
    tags: tags
  }
}

// Store sensitive Azure AI Search Service values in Key Vault
module searchSecrets 'modules/searchsecrets.bicep' = if (!useExistingSearchSecrets) {
  name: 'searchSecretsDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    searchServiceName: searchService.outputs.searchServiceName
    vaultName: existingKeyVaultName != '' ? existingKeyVaultName : keyvault.outputs.name
  }
}

// Deploys AI Studio
module aiStudio 'modules/aihub.bicep' = if (aiStudioEnabled) {
  name: 'aiStudioDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  scope: resourceGroup(aiStudioResourceGroupName)
  params: {
    resourceNameSuffix: resourceNameSuffix
    existingPrivateResourceGroup: resourceGroup().name
    existingCognitiveServicesAccountName: cognitiveServicesAccount.outputs.name
    tags: tags
  }
}

// Deploy Azure Front Door and WAF Policy
module frontDoor 'modules/frontdoor.bicep' = {
  name: 'frontDoorDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    resourceNameSuffix: resourceNameSuffix
    wafPolicyMode: wafPolicyMode
    tags: tags
  }
}
