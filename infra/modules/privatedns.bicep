metadata name = 'Private DNS Zone Module'
metadata description = 'This module deploys private DNS zones Key Vault, ACR, App Service, APIM, CosmosDB, OpenAI, Cognitive Services, and Search'
@description('ID of the virtual network to link the private DNS zones to')
param virtualNetworkResourceId string
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}
var mergedTags = {
  ...tags
  module: 'privatedns'
}

module kvPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.2.5' = {
  name: 'kvSvcPrivateDnsZoneDeployment-${uniqueString(resourceGroup().id, virtualNetworkResourceId)}'
  params: {
    name: 'privatelink.vaultcore.azure.net'
    location: 'global'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: virtualNetworkResourceId
      }
    ]
    tags: mergedTags
  }
}

module openAIPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.2.5' = {
  name: 'openAIPrivateDnsZoneDeployment-${uniqueString(resourceGroup().id, virtualNetworkResourceId)}'
  params: {
    name: 'privatelink.openai.azure.com'
    location: 'global'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: virtualNetworkResourceId
      }
    ]
    tags: mergedTags
  }
}

module speechServicePrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.2.5' = {
  name: 'speechServicePrivateDnsZoneDeployment-${uniqueString(resourceGroup().id, virtualNetworkResourceId)}'
  params: {
    name: 'privatelink-speech.cognitiveservices.azure.com'
    location: 'global'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: virtualNetworkResourceId
      }
    ]
    tags: mergedTags
  }
}

module cognitiveServicesPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.2.5' = {
  name: 'cognitiveServicesPrivateDnsZoneDeployment-${uniqueString(resourceGroup().id, virtualNetworkResourceId)}'
  params: {
    name: 'privatelink.cognitiveservices.azure.com'
    location: 'global'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: virtualNetworkResourceId
      }
    ]
    tags: mergedTags
  }
}

module acrPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.2.5' = {
  name: 'acrPrivateDnsZoneDeployment-${uniqueString(resourceGroup().id, virtualNetworkResourceId)}'
  params: {
    name: 'privatelink.azurecr.io'
    location: 'global'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: virtualNetworkResourceId
      }
    ]
    tags: mergedTags
  }
}

module appSvcPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.2.5' = {
  name: 'appSvcPrivateDnsZoneDeployment-${uniqueString(resourceGroup().id, virtualNetworkResourceId)}'
  params: {
    name: 'privatelink.azurewebsites.net'
    location: 'global'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: virtualNetworkResourceId
      }
    ]
    tags: mergedTags
  }
}

module apimPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.2.5' = {
  name: 'apimSvcPrivateDnsZoneDeployment-${uniqueString(resourceGroup().id, virtualNetworkResourceId)}'
  params: {
    name: 'privatelink.azure-api.net'
    location: 'global'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: virtualNetworkResourceId
      }
    ]
    tags: mergedTags
  }
}

module cosmosDBPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.2.5' = {
  name: 'cosmosDBPrivateDnsZoneDeployment-${uniqueString(resourceGroup().id, virtualNetworkResourceId)}'
  params: {
    name: 'privatelink.documents.azure.com'
    location: 'global'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: virtualNetworkResourceId
      }
    ]
    tags: mergedTags
  }
}

module searchPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.2.5' = {
  name: 'searchPrivateDnsZoneDeployment-${uniqueString(resourceGroup().id, virtualNetworkResourceId)}'
  params: {
    name: 'privatelink.search.windows.net'
    location: 'global'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: virtualNetworkResourceId
      }
    ]
    tags: mergedTags
  }
}

module storagePrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.2.5' = {
  name: 'storagePrivateDnsZoneDeployment-${uniqueString(resourceGroup().id, virtualNetworkResourceId)}'
  params: {
    name: 'privatelink.blob.${environment().suffixes.storage}'
    location: 'global'
    virtualNetworkLinks: [
      {
        virtualNetworkResourceId: virtualNetworkResourceId
      }
    ]
    tags: mergedTags
  }
}

output acrPrivateDnsZoneId string = acrPrivateDnsZone.outputs.resourceId
output appServicePrivateDnsZoneId string = appSvcPrivateDnsZone.outputs.resourceId
output apimPrivateDnsZoneId string = apimPrivateDnsZone.outputs.resourceId
output keyvaultPrivateDnsZoneId string = kvPrivateDnsZone.outputs.resourceId
output cosmosDBPrivateDnsZoneId string = cosmosDBPrivateDnsZone.outputs.resourceId
output openAIPrivateDnsZoneId string = openAIPrivateDnsZone.outputs.resourceId
output cognitiveServicesPrivateDnsZoneId string = cognitiveServicesPrivateDnsZone.outputs.resourceId
output speechServicePrivateDnsZoneId string = speechServicePrivateDnsZone.outputs.resourceId
output searchPrivateDnsZoneId string = searchPrivateDnsZone.outputs.resourceId
output storagePrivateDnsZoneId string = storagePrivateDnsZone.outputs.resourceId
