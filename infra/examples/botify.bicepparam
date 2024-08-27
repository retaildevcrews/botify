using '../azuredeploy-private.bicep'

//  Required parameters
param resourceNameSuffix='btfy-dev-use2'

// Optional parameters
param keyVaultAdminPrincipal = '44970694-8175-4246-b62b-b72e7df1a567' // ADC-ADM Group
param vaultSecrets = {
  jumpboxSecret: readEnvironmentVariable('JUMPBOX_SECRET', '${uniqueString(resourceNameSuffix)}.${toUpper(uniqueString('jumpbox'))}')
}
param tags = {
  environment: 'dev'
  app: 'botify'
  component: 'infra'
}

// Optional feature flags
param cognitiveServicesLocalAuthDisabled = false
param acrName = 'acrbtfydev001'
param apimEnabled = true
param aiStudioEnabled = true
param aiStudioResourceGroupName = 'rg-botify-aistudio'
// param wafPolicyMode = 'Prevention'
// param apimPublicNetworkAccess = 'Disabled'
// param jumpboxEnabled = true
// param jumpboxAdminUsername = 'jumpboxadmin'
// param cosmosEnabled = true
// param cosmosContainerName = 'chatHistory'

// Can override to adjust models and capacity
/* param cognitiveServicesModelDeployments = [
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
] */
param alertsEmail = '<email address goes here'
