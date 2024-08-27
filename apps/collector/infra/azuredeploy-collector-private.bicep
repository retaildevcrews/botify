metadata name = 'OpenTelemetry Collector'
metadata description = 'This module deploys private networking resources for OpenTelemetry Collector'

@description('The Azure region where resources will be deployed. Defaults to the resource group location.')
param location string = resourceGroup().location
@description('Name suffix for all resources in the module. Format: project-environment-region, Ex: chatbot-dev-use2')
@minLength(3)
param resourceNameSuffix string
@description('The name of the App Service Container app')
param appName string = 'collector'
@description('Array of secret names to be stored in Key Vault for application configuration. Defaults to an empty array.')
param appConfigurationSecretNames array = []
@description('Array of app settings key value pairs. Default is an empty array.')
param appConfigurationValues array = []
@description('Secrets to be stored in the deployed Key Vault. Defaults to an empty object.')
@secure()
param vaultSecrets object = {}
@description('The container image reference for the app in the format "repository/image:tag". Ex: otel/opentelemetry-collector-contrib:0.100.0')
param appContainerImage string
@description('The name of an existing Key Vault for application secrets')
param existingKeyVaultName string = 'kv-${resourceNameSuffix}-001'
@description('The name of the existing VNet to deploy the resources into.')
param existingVnetName string = 'vnet-${resourceNameSuffix}-001'
@description('The name of the existing subnet for the App Service.')
param appServiceSubnetName string = 'snet-appsvc-001'
@description('The name of the existing subnet for the private endpoint.')
param privateEndpointSubnetName string = 'snet-pe-001'
@description('The name of the existing private DNS zone for the App Service.')
param privateDnsZoneName string = 'privatelink.azurewebsites.net'
@description('Array of IP addresses to allow access to the App Service. Defaults to an empty array.')
param allowedIpAddresses array = []
@description('The name of the existing Application Insights instance to use for monitoring.')
param existingAppInsightsName string = 'appi-${resourceNameSuffix}-001'
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}

resource existingVnet 'Microsoft.Network/virtualNetworks@2021-02-01' existing = {
  name: existingVnetName
}

resource existingAppSvcPrivateDnsZone 'Microsoft.Network/privateDnsZones@2018-09-01' existing = {
  name: privateDnsZoneName
}

resource existingAppInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: existingAppInsightsName
}

resource existingKeyVault 'Microsoft.KeyVault/vaults@2021-06-01-preview' existing = {
  name: existingKeyVaultName
  resource appiSecret 'secrets@2023-07-01' = {
      name: 'AppInsightsConnectionString'
      properties: {
        value: existingAppInsights.properties.ConnectionString
      }
    }
  resource secrets 'secrets@2023-07-01' = [
    for secret in items(vaultSecrets): {
      name: secret.key
      properties: {
        value: secret.value
      }
    }
  ]
}

var appServiceSubnetId = filter(existingVnet.properties.subnets, s => s.name == appServiceSubnetName)[0].id
var privateEndpointSubnetId = filter(existingVnet.properties.subnets, s => s.name == privateEndpointSubnetName)[0].id

// Deploys an App Service Plan and App Service Container for the backend API
module appService '../../../infra/modules/appservice.bicep' = {
  name: 'appserviceDeployment-otel-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    resourceNameSuffix: resourceNameSuffix
    appName: appName
    containerImageReference: appContainerImage
    location: location
    appServiceSubnetId: appServiceSubnetId
    privateEndpointSubnetId: privateEndpointSubnetId
    privateDnsZoneId: existingAppSvcPrivateDnsZone.id
    appConfigurationValues: appConfigurationValues
    appConfigurationSecretNames: appConfigurationSecretNames
    appCommandLine: ' --config=env:OTEL_CONFIG'
    existingKeyVaultName: existingKeyVaultName
    publicNetworkAccess: 'Disabled'
    allowedIpAddresses: allowedIpAddresses
    acrUseManagedIdentityCreds: false
    vnetImagePullEnabled: false
    tags: tags
  }
}
