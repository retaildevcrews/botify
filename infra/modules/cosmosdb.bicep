metadata name = 'Private Cosmos DB Module'
metadata description = 'This module deploys private CosmosDB'

@description('Name suffix for all resources in the module')
param resourceNameSuffix string
@description('Private Dns Zone ResourceId for Cosmos Private Endpoint')
param privateDnsZoneResourceId string
@description('Subnet where the private endpoint will be deployed')
param subnetResourceId string
@description('Name of container that will hold chat history documents')
param containerName string
@description('Location where the resources will be deployed')
param location string = resourceGroup().location
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}

var mergedTags = {
  ...tags
  module: 'cosmosdb'
}
module cosmosDBAccount 'br/public:avm/res/document-db/database-account:0.5.4' = {
  name: 'cosmosdb-account-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: 'cosmos-${resourceNameSuffix}-001'
    capabilitiesToAdd: [
      'EnableServerless'
    ]
    enableFreeTier: false
    location: location
    locations: [
      {
        failoverPriority: 0
        isZoneRedundant: false
        locationName: location
      }
    ]    
    networkRestrictions: {
      ipRules: []
      virtualNetworkRules: []
      publicNetworkAccess: 'Disabled'
    }
    privateEndpoints: [
      {
        service: 'Sql' 
        privateDnsZoneResourceIds: [
          privateDnsZoneResourceId
        ]
        privateDnsZoneGroupName: 'default'
        subnetResourceId: subnetResourceId
      }
    ]
    sqlDatabases: [
      {
        name: 'cosmos-db-${resourceNameSuffix}'
        containers: [
          {
            name: containerName
            paths: [
              '/user_id'
            ]
            kind: 'Hash'
            version: 2
            defaultTtl: 1000
          }
        ]
      }
    ]
    tags: mergedTags
  }
}

@description('The Cosmos DB Account Name')
output cosmosDBAccountName string = cosmosDBAccount.outputs.name
