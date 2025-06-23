using 'azuredeploy-private.bicep'

//  Required parameters
param resourceNameSuffix='<enter suffix here>'


// Optional parameters
param keyVaultAdminPrincipal = ''
param vaultSecrets = {
  jumpboxSecret: readEnvironmentVariable('JUMPBOX_SECRET', '${uniqueString(resourceNameSuffix)}.${toUpper(uniqueString('jumpbox'))}')
}
param tags = {
  environment: 'dev'
  app: 'botify'
  component: 'infra'
}
param alertsEmail = '<email address goes here>'


// Optional feature flags
// param wafPolicyMode = 'Prevention'
// param cognitiveServicesLocalAuthDisabled = false
// param apimEnabled = false
// param apimPublicNetworkAccess = 'Disabled'
// param jumpboxEnabled = true
// param jumpboxAdminUsername = 'jumpboxadmin'
// param cosmosEnabled = true
// param cosmosContainerName = 'chatHistory'
