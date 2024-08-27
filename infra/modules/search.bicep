metadata name = 'Private AI Search Service Module'
metadata description = 'This module deploys a private AI Search Service'

@description('The suffix for the name of the resources that will be created')
param resourceNameSuffix string
@description('The ID of the subnet to deploy the private endpoint to')
param privateEndpointSubnetId string
@description('Private DNS Zone ID for the Private Endpoint')
param privateDnsZoneId string
@description('Public network access for the App Service. Default is disabled.')
param publicNetworkAccess string = 'disabled'
@description('Location for all resources. Defaults to the resource group location')
param location string = resourceGroup().location
@description('User assigned identity to be used for the search service')
param userAssignedIdentity string = ''
@description('Resource ID of the Cognitive Services account to be linked to the search service')
param cognitiveServicesResourceId string = ''
@description('SKU name for the search service. Default is standard')
@allowed(['basic', 'free', 'standard', 'standard2', 'standard3', 'storage_optimized_l1', 'storage_optimized_l2'])
param skuName string = 'standard'
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}

var mergedTags = {
  ...tags
  module: 'search'
}

var identityConfig = (userAssignedIdentity != '') ? { type: 'SystemAssigned, UserAssigned', userAssignedIdentities: { '${userAssignedIdentity}': {} } } : { type: 'SystemAssigned' }

resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  location: location
  name: 'srch-${resourceNameSuffix}-001'
  sku: {
    name: skuName
  }
  identity: identityConfig
  properties: {
    authOptions: {
      aadOrApiKey: { aadAuthFailureMode: 'http401WithBearerChallenge' }
    }
    encryptionWithCmk: { enforcement: 'Unspecified' }
    disableLocalAuth: false
    hostingMode: 'default'
    partitionCount: 1
    replicaCount: 1
    publicNetworkAccess: publicNetworkAccess
    semanticSearch: 'standard'
  }
  tags: mergedTags
  resource privateLink 'sharedPrivateLinkResources@2024-03-01-preview' = if (cognitiveServicesResourceId != ''){
    name: 'pep-oai-search'
    properties: {
      privateLinkResourceId: cognitiveServicesResourceId
      groupId: 'openai_account'
      requestMessage: 'allow search service access'
    }
  }
}
module searchService_privateEndpoints 'br/public:avm/res/network/private-endpoint:0.4.1' = {
  name: '${uniqueString(deployment().name, location)}-searchService-PrivateEndpoint-001'
  params: {
    name: 'pep-${last(split(searchService.id, '/'))}-${'searchService'}-001'
    privateLinkServiceConnections: [
      {
        name: '${last(split(searchService.id, '/'))}-searchService-001'
        properties: {
          privateLinkServiceId: searchService.id
          groupIds: [
            'searchService'
          ]
        }
      }
    ]
    tags: mergedTags
    subnetResourceId: privateEndpointSubnetId
    location: location
    privateDnsZoneGroupName: 'default'
    privateDnsZoneResourceIds: [privateDnsZoneId]
  }
}

output searchServiceName string = searchService.name
output searchServiceSystemAssignedMIPrincipalId string = searchService.identity.principalId
