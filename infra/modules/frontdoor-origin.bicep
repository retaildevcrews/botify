metadata name = 'Azure Front Door Origin'
metadata description = 'This module creates an origin and origin group in an Azure Front Door'

@description('Name of the Azure Front Door to attach the WAF to')
param frontDoorName string

@description('Host name of the origin to attach to the Front Door')
param originHostName string

@description('Name of the origin and group to create in the Front Door')
param name string


param privateLinkResourceId string = ''
param privateLinkLocation string = ''
param privateLinkGroupId string = ''
param existingOriginGroupName string = ''

var usePrivateLink = privateLinkResourceId != '' && privateLinkLocation != '' && privateLinkGroupId != ''
var originName = 'origin-${name}'
var originGroupName = existingOriginGroupName != '' ? existingOriginGroupName : 'group-${name}'

resource cdnProfile 'Microsoft.Cdn/profiles@2023-05-01' existing = {
  name: frontDoorName
  resource originGroup 'originGroups@2024-02-01' = {
    name: originGroupName
    properties: {
      healthProbeSettings: {
        probePath: '/'
        probeRequestType: 'HEAD'
        probeProtocol: 'Https'
        probeIntervalInSeconds: 100
      }
      loadBalancingSettings: {
        additionalLatencyInMilliseconds: 50
        sampleSize: 4
        successfulSamplesRequired: 3
      }
    }
    resource origin 'origins@2024-02-01' = {
      name: originName
      properties: {
        hostName: originHostName
        originHostHeader: originHostName
        sharedPrivateLinkResource: usePrivateLink ? {
          privateLink: {
            id: privateLinkResourceId
          }
          groupId: privateLinkGroupId
          privateLinkLocation: privateLinkLocation
          requestMessage: 'Azure Front Door private link'
        } : null
        priority: 1
      }
    }
  }
}

output originName string = originName
output originGroupName string = originGroupName
