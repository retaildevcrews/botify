metadata name = 'Azure Front Door Connect'
metadata description = 'This module connects a resource to Front Door'

@description('Name of the Azure Front Door to connect to')
param frontDoorName string
@description('Name of the app to connect to the Front Door')
param appName string
@description('Host name of the origin to connect to the Front Door')
param appHostName string
@description('Resource ID of the Private Link resource to connect to the Front Door')
param privateLinkResourceId string = ''
@description('Location of the Private Link resource to connect to the Front Door')
param privateLinkLocation string = ''
@description('Group ID of the Private Link resource to connect to the Front Door')
param privateLinkGroupId string = ''
@description('State of the endpoint')
@allowed([
  'Enabled'
  'Disabled'
])
param endpointState string = 'Disabled'
@description('Optional. Name of the WAF policy to associate with the endpoint')
param wafPolicyName string = ''
param logAnalyticsWorkspaceName string = ''
param endpointName string = ''
var usePrivateLink = privateLinkResourceId != '' && privateLinkLocation != '' && privateLinkGroupId != ''

// Create an Origin and Origin Group in front door for the app
module origin 'frontdoor-origin.bicep' = {
  name: 'afd-origin-${appName}-${uniqueString(resourceGroup().id, frontDoorName)}'
  params: {
    name: appName
    frontDoorName: frontDoorName
    originHostName: appHostName
    privateLinkGroupId: usePrivateLink ? privateLinkGroupId : ''
    privateLinkLocation:  usePrivateLink ? privateLinkLocation : ''
    privateLinkResourceId: usePrivateLink ? privateLinkResourceId : ''
  }
}

// Create an Endpoint in front door for the app, using the Origin created above
module endpoint 'frontdoor-endpoint.bicep' = {
  name: 'afd-endpoint-${appName}-${uniqueString(resourceGroup().id, frontDoorName)}'
  params: {
    frontDoorName: frontDoorName
    endpointName: endpointName != '' ? endpointName : '${appName}-${uniqueString(appHostName)}'
    endpointState: endpointState
    originGroupName: origin.outputs.originGroupName
  }
}

// Optionally associate a WAF policy with the endpoint
module wafPolicyAssociation '../../infra/modules/frontdoor-security-profile.bicep' = if (wafPolicyName != '') {
  name: 'afd-wafPolicyAssociation-${appName}-${uniqueString(resourceGroup().id, frontDoorName)}'
  params: {
    frontDoorName: frontDoorName
    frontDoorWAFName: wafPolicyName
    frontDoorEndpointName: endpoint.outputs.endpointName
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
  }
}

output endpointHostName string = endpoint.outputs.hostName
