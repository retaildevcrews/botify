metadata name = 'App Service with Private Endpoint'
metadata description = 'This module deploys an App Service Container with a Private Endpoint'

@description('Subnet ID for the App Service')
param appServiceSubnetId string
@description('Subnet ID for the Private Endpoint')
param privateEndpointSubnetId string
@description('Private DNS Zone ID for the Private Endpoint')
param privateDnsZoneId string
@description('Name suffix for all resources in the module')
param resourceNameSuffix string
@ description('Container image reference for the App. Example: myregistry.azurecr.io/myimage:latest')
param containerImageReference string
@description('Name of the App')
param appName string
@description('Name of an existing App Service Plan. If not provided, a new one will be created.')
param existingAppServicePlanName string = ''
@description('Name of an existing Managed Identity. If not provided, a new one will be created.')
param existingManagedIdentityName string = ''
@description('ID of a container registry to allow the App Service to pull images from. Required RBAC role assignment will be created.')
param containerRegistryId string = ''
@description('Array of public IP addresses to allow access to the App Service. Default is an empty array.')
param allowedIpAddresses array = []
@description('Name of an existing Key Vault for application secrets. If provided, required role assignment will be created.')
param existingKeyVaultName string = ''
@description('Array of app settings key value pairs. Default is an empty array.')
param appConfigurationValues array = []
@description('Array of secret names in the Key Vault to be added to app settings. Default is an empty array.')
param appConfigurationSecretNames array = []
@description('Command line to start the app. Default is an empty string.')
param appCommandLine string = ''
@description('Location for all resources in the module')
param location string = resourceGroup().location
@description('Public network access for the App Service. Default is Enabled.')
param publicNetworkAccess string = 'Enabled'
@description('Name of the SKU for the App Service Plan. Default is B1.')
param skuName string = 'B1'
@description('Tier of the SKU for the App Service Plan. Default is Basic.')
param skuTier string = 'Basic'
@description('Kind of the App Service Plan. Default is Linux.')
param planKind string = 'Linux'
@description('Kind of the App Service. Default is app,linux.')
param appKind string = 'app,linux'
@description('Whether to enable VNet image pull. Default is true.')
param vnetImagePullEnabled bool = true
@description('Whether to use managed identity credentials for ACR. Default is true.')
param acrUseManagedIdentityCreds bool = true
@description('Whether to route all traffic through the VNet. Default is false.')
param vnetRouteAllEnabled bool = false
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}

var mergedTags = {
  ...tags
  module: 'appservice'
}

// Allowed public IP addresses, useful for connecting APIM
var ipSecurityRules = [for address in allowedIpAddresses: {
  ipAddress: '${address}/32'
  action: 'Allow'
  priority: 100 + indexOf(allowedIpAddresses, address)
  name: 'Allow IP Address'
  description: 'Allow IP Address'
}]

resource existingManagedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-07-31-preview' existing = if (existingManagedIdentityName != '') {
  name: existingManagedIdentityName
}
resource existingKeyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = if (existingKeyVaultName != '') {
  name: existingKeyVaultName
}

module appServicePlan 'br/public:avm/res/web/serverfarm:0.1.1' = if (existingAppServicePlanName == '') {
  name: 'asp-deployment-${appName}-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: 'asp-${appName}-${resourceNameSuffix}-001'
    location: location
    reserved: planKind == 'Linux' ? true : false
    sku: {
      name: skuName
      tier: skuTier
    }
    kind: planKind
    tags: mergedTags
  }
}

resource existingAppServicePlan 'Microsoft.Web/serverfarms@2023-12-01' existing = if (existingAppServicePlanName != '') {
  name: existingAppServicePlanName
}

// Create an identity for the App
module userAssignedIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.2.1' = if (existingManagedIdentityName == '') {
  name: 'userAssignedIdentityDeployment-${appName}-${uniqueString(resourceGroup().id, appName)}'
  params: {
    location: location
    name: 'umi-${appName}-${resourceNameSuffix}-001'
    tags: mergedTags
  }
}

// Allow App to Pull from ACR
module roleAssignmentPull 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.0' = if (containerRegistryId != '') {
  name: 'appServiceRoleAssignmentPull-${appName}-${uniqueString(resourceGroup().id, appName)}'
  params: {
    principalId: existingManagedIdentityName == '' ? userAssignedIdentity.outputs.principalId : existingManagedIdentity.properties.principalId
    resourceId: containerRegistryId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}

// Allow User Assigned ID to read secret contents from KeyVault
module userIdRoleAssignmentKVSecretUser 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.0' = if (existingKeyVaultName != '') {
  name: 'appUserRoleAssignmentKVSecretUser-${appName}-${uniqueString(resourceGroup().id, appName)}'
  params: {
    principalId: existingManagedIdentityName == '' ? userAssignedIdentity.outputs.principalId : existingManagedIdentity.properties.principalId
    resourceId: existingKeyVault.id
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
  }
}

// Initialize an empty array to store app settings
var appConfiguration = [
  for item in appConfigurationValues: {
    name: split(item, '=')[0]
    value: replace(item, '${split(item, '=')[0]}=','')
  }
]

// Add secret references to app settings
var appSecretReferences = [
  for item in appConfigurationSecretNames: {
    // Split each string by '-' to get the secret name and environment variable name
    // item[0] will be the environment variable name and item[1] will be the secret name
    name: split(item, '=')[0]
    value: '@Microsoft.KeyVault(VaultName=${existingKeyVaultName};SecretName=${split(item, '=')[1]})'
  }
]

var appSettings = concat(appConfiguration, appSecretReferences)

module appServiceContainer 'br/public:avm/res/web/site:0.3.5' = {
  name: 'siteDeployment-${appName}-${uniqueString(resourceGroup().id, appName)}'
  params: {
    managedIdentities: {
      systemAssigned: false
      userAssignedResourceIds: existingManagedIdentityName == '' ? [userAssignedIdentity.outputs.resourceId] : [existingManagedIdentity.id]
    }
    location: location
    keyVaultAccessIdentityResourceId: existingManagedIdentityName == '' ? userAssignedIdentity.outputs.resourceId : existingManagedIdentity.id
    publicNetworkAccess: publicNetworkAccess
    virtualNetworkSubnetId: appServiceSubnetId
    kind: appKind
    name: 'app-${appName}-${resourceNameSuffix}-001'
    serverFarmResourceId: existingAppServicePlanName == '' ? appServicePlan.outputs.resourceId : existingAppServicePlan.id
    vnetImagePullEnabled: vnetImagePullEnabled
    vnetRouteAllEnabled: vnetRouteAllEnabled
    siteConfig: {
      httpLoggingEnabled: true
      logsDirectorySizeLimit: 100
      ipSecurityRestrictionsDefaultAction: ipSecurityRules == [] && publicNetworkAccess == 'Enabled' ? 'Allow' : 'Deny'
      ipSecurityRestrictions: ipSecurityRules != [] ? ipSecurityRules : null
      acrUseManagedIdentityCreds: acrUseManagedIdentityCreds
      acrUserManagedIdentityId: existingManagedIdentityName == '' ? userAssignedIdentity.outputs.clientId : existingManagedIdentity.properties.clientId
      linuxFxVersion: 'DOCKER|${containerImageReference}'
      appSettings: appSettings
      appCommandLine: appCommandLine != '' ? appCommandLine : null
    }
    privateEndpoints: [
      {
        subnetResourceId: privateEndpointSubnetId
        privateDnsZoneResourceIds: [
          privateDnsZoneId
        ]
      }
    ]
    tags: mergedTags
  }
}

@description('The app default domain name')
output appServiceDefaultDomainName string = appServiceContainer.outputs.defaultHostname
@description('The name of the App Service')
output appServiceName string = appServiceContainer.outputs.name
@description('The app resource ID')
output appServiceResourceId string = appServiceContainer.outputs.resourceId
