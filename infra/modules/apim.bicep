metadata name = 'API Management Service with Private Endpoint'
metadata description = 'This module deploys an Azure API Management service with private endpoint support. '

@description('The suffix for the name of the resources that will be created')
param resourceNameSuffix string
@description('Location for all resources. Defaults to the resource group location')
param location string = resourceGroup().location
param publisherName string = 'rdc'
@description('Email address of the API Management service publisher')
param publisherEmail string = 'apimgmt-noreply@mail.windowsazure.com'
@description('Public network access to the API Management service')
@allowed([
  'Enabled'
  'Disabled'
])
param publicNetworkAccess string = 'Enabled'
@description('The name of the existing key vault to use for storing the API Management service secrets')
param existingKeyVaultName string = ''
@description('Resource Id for APIM subnet')
param subnetResourceId string
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}

var mergedTags = {
  ...tags
  module: 'apim'
}

resource apimService 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: 'apim-${resourceNameSuffix}-001'
  location: location
  sku: {
    name: 'Developer'
    capacity: 1
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    // Currently only non vnet injected APIM services can be created with private endpoint
    virtualNetworkType: 'External'
    virtualNetworkConfiguration: {
      subnetResourceId: subnetResourceId
    }
    // Blocking all public network access not allowd during service creation
    publicNetworkAccess: publicNetworkAccess
  }
  tags: mergedTags
}

resource existingKeyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = if (existingKeyVaultName != ''){
  name: existingKeyVaultName
  resource apimPrimaryKeySecret 'secrets' = {
    name: 'ApimPrimaryKey'
    properties: {
      value: listSecrets('${apimService.id}/subscriptions/master', '2023-05-01-preview').primaryKey
    }
  }
}

@description('The IP address of the API Management service gateway')
output apimGatewayIpAddress array = apimService.properties.outboundPublicIPAddresses
@description('The API Management service name')
output apimServiceName string = apimService.name
@description('The API Management service gateway url')
output apimGatewayURL string = apimService.properties.gatewayUrl
