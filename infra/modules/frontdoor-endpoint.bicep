metadata name = 'Azure Front Door Endpoint'
metadata description = 'This module creates an endpoint and route on an Azure Front Door'

@description('Name of the Azure Front Door to attach the WAF to')
param frontDoorName string

@description('Name of the endpoint to create on the Front Door')
param endpointName string

param location string = resourceGroup().location
param endpointState string = 'Enabled'
param originGroupName string
param linkToDefaultDomain string = 'Enabled'

resource frontDoor 'Microsoft.Cdn/profiles@2024-02-01' existing = {
  name: frontDoorName
}

resource originGroup 'Microsoft.Cdn/profiles/originGroups@2024-02-01' existing = {
  parent: frontDoor
  name: originGroupName
}

resource frontDoorEndpoint 'Microsoft.Cdn/profiles/afdEndpoints@2024-02-01' = {
  name: endpointName
  parent: frontDoor
  location: location
  properties: {
    enabledState: endpointState
  }
  resource route 'routes@2024-02-01' = {
    name: 'route-app-${endpointName}'
    properties: {
      linkToDefaultDomain: linkToDefaultDomain
      originGroup: {
        id: originGroup.id
      }
      patternsToMatch: [
        '/*'
      ]
    }
  }
}

output endpointName string = frontDoorEndpoint.name
output hostName string = frontDoorEndpoint.properties.hostName
