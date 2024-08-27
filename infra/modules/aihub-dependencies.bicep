metadata name = 'AI Hub Dependencies'
metadata description = 'Creates Azure dependent resources for Azure AI Hub'

@description('Azure region of the deployment')
param location string = resourceGroup().location
@description('Name suffix for all resources in the module')
param resourceNameSuffix string
@allowed([
  'Standard_LRS'
  'Standard_ZRS'
  'Standard_GRS'
  'Standard_GZRS'
  'Standard_RAGRS'
  'Standard_RAGZRS'
  'Premium_LRS'
  'Premium_ZRS'
])
@description('Storage SKU')
param storageSkuName string = 'Standard_LRS'
@description('Create Cognitive Services Account defaults to false')
param createCognitiveServices bool = false
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}

var mergedTags = {
  ...tags
  module: 'aiHub-dependencies'
}
var storageNameCleaned = replace(replace('stai${resourceNameSuffix}001', '-', ''), '_', '')
var containerRegistryNameCleaned = replace(replace('acrai${resourceNameSuffix}001', '-', ''), '_', '')

module workspace 'br/public:avm/res/operational-insights/workspace:0.3.4' = {
  name: 'workspaceDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    // Required parameters
    name: 'log-ai-${resourceNameSuffix}-001'
    // Non-required parameters
    location: location
    tags: mergedTags
  }
}

module applicationInsights 'br/public:avm/res/insights/component:0.3.0' = {
  name: 'applicationInsightsDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    // Required parameters
    name: 'appi-ai-${resourceNameSuffix}-001'
    workspaceResourceId: workspace.outputs.resourceId
    // Non-required parameters
    location: location
    applicationType: 'web'
    disableIpMasking: false
    disableLocalAuth: false
    forceCustomerStorageForProfiler: false
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Disabled'
    retentionInDays: 30
    tags: mergedTags
  }
}

// Deploys Azure Container Registry
module registry 'br/public:avm/res/container-registry/registry:0.1.1' = {
  name: 'registryDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    // Required parameters
    name: containerRegistryNameCleaned
    // Non-required parameters
    acrSku: 'Premium'
    acrAdminUserEnabled: true
    dataEndpointEnabled: false
    networkRuleBypassOptions: 'AzureServices'
    networkRuleSetDefaultAction: 'Deny'
    quarantinePolicyStatus: 'enabled'
    retentionPolicyStatus: 'enabled'
    retentionPolicyDays: 7
    trustPolicyStatus: 'disabled'
    publicNetworkAccess: 'Disabled'
    zoneRedundancy: 'Disabled'
    tags: mergedTags
  }
}

// Deploys Azure Key Vault
module keyvault 'br/public:avm/res/key-vault/vault:0.6.1' = {
  name: 'keyvaultDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: 'kv-ai-${resourceNameSuffix}-002'
    enableVaultForDeployment: false
    enableVaultForTemplateDeployment: false
    enableVaultForDiskEncryption: false
    enablePurgeProtection: false
    enableRbacAuthorization: true
    publicNetworkAccess: 'Enabled'
    sku: 'standard'
    softDeleteRetentionInDays: 7
    tags: mergedTags
  }
}

module storageAccount 'br/public:avm/res/storage/storage-account:0.9.0' = {
  name: 'storageAccountDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    // Required parameters
    name: storageNameCleaned
    // Non-required parameters
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    skuName: storageSkuName
    accessTier: 'Hot'
    location: location
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
    requireInfrastructureEncryption: false
    blobServices: {
      enabled: true
      keyType: 'Account'
    }
    fileServices: {
      enabled: true
      keyType: 'None'
    }
    queueServices: {
      enabled: true
      keyType: 'Service'
    }
    tableServices: {
      enabled: true
      keyType: 'Service'
    }
    enableHierarchicalNamespace: false
    enableNfsV3: false
    largeFileSharesState: 'Disabled'
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    tags: mergedTags
  }
}

// Deploys Cognitive Services 
module cognitiveServicesAccount 'br/public:avm/res/cognitive-services/account:0.5.3' = if (createCognitiveServices) {
  name: 'cognitiveServicesAccountDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: 'cog-ai-${resourceNameSuffix}-001'
    location: location
    kind: 'AIServices' 
    sku: 'S0'
    apiProperties: {
      statisticsEnabled: false
    }
    tags: mergedTags
  }
}


output cognitiveServicesName string = cognitiveServicesAccount.name
output cognitiveServicesId string = createCognitiveServices ? cognitiveServicesAccount.outputs.resourceId : ''
output cognitiveServicesEndpoint string? = createCognitiveServices ? cognitiveServicesAccount.outputs.endpoint : null
output storageId string = storageAccount.outputs.resourceId
output storageAccountName string = storageAccount.outputs.name
output keyvaultId string = keyvault.outputs.resourceId
output keyvaultName string = keyvault.outputs.name
output containerRegistryId string = registry.outputs.resourceId
output applicationInsightsId string = applicationInsights.outputs.resourceId
