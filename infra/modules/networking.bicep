metadata name = 'Virtual Network Module'
metadata description = 'This module deploys a Virtual Network with subnets and NSGs '

@description('Name suffix for all resources in the module')
param resourceNameSuffix string
@description('Location for all resources in the module')
param location string = resourceGroup().location
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}
var mergedTags = {
  ...tags
  module: 'networking'
}
var apimSubnetName = 'snet-apim-001'

module apimNSG 'br/public:avm/res/network/network-security-group:0.3.1' = {
  name: 'apimNSGDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: 'vnet-${resourceNameSuffix}-001-${apimSubnetName}-nsg-${location}'
    location: location
    securityRules: [
      // inbound rules
      {
        name: 'afd-to-vnet'
        properties: {
          direction: 'Inbound'
          access: 'Allow'
          priority: 100
          description: 'Client communication to API Management from Front Door'
          sourceAddressPrefix: 'AzureFrontDoor.Backend'
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRanges: ['80', '443']
          protocol: 'Tcp'
        }
      }
      {
        name: 'apim-to-vnet'
        properties: {
          direction: 'Inbound'
          access: 'Allow'
          priority: 110
          description: 'Management endpoint for Azure portal and PowerShell'
          sourceAddressPrefix: 'ApiManagement'
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRange: '3443'
          protocol: 'Tcp'
        }
      }
      {
        name: 'atm-to-vnet'
        properties: {
          direction: 'Inbound'
          access: 'Allow'
          priority: 130
          description: 'Azure Traffic Manager routing for multi-region deployment'
          sourceAddressPrefix: 'AzureTrafficManager'
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRange: '443'
          protocol: 'Tcp'
        }
      }
      // outbound rules
      {
        name: 'vnet-to-storage'
        properties: {
          direction: 'Outbound'
          access: 'Allow'
          priority: 140
          description: 'Dependency on Azure Storage for core service functionality'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'Storage'
          destinationPortRange: '443'
          protocol: 'Tcp'
        }
      }
      {
        name: 'vnet-to-sql'
        properties: {
          direction: 'Outbound'
          access: 'Allow'
          priority: 150
          description: 'Access to Azure SQL endpoints for core service functionality'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'Sql'
          destinationPortRange: '1433'
          protocol: 'Tcp'
        }
      }
      {
        name: 'vnet-to-kv'
        properties: {
          direction: 'Outbound'
          access: 'Allow'
          priority: 160
          description: 'Access to Azure Key Vault for core service functionality'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'AzureKeyVault'
          destinationPortRange: '443'
          protocol: 'Tcp'
        }
      }
      {
        name: 'vnet-to-az-monitor'
        properties: {
          direction: 'Outbound'
          access: 'Allow'
          priority: 170
          description: 'Publish Diagnostics Logs and Metrics, Resource Health, and Application Insights'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'AzureMonitor'
          destinationPortRanges: ['443', '1886']
          protocol: 'Tcp'
        }
      }
    ]
  }
}

module virtualNetwork 'br/public:avm/res/network/virtual-network:0.1.6' = {
  name: 'virtualNetworkDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    // Required parameters
    addressPrefixes: [
      '10.0.0.0/22'
    ]
    name: 'vnet-${resourceNameSuffix}-001'
    location: location
    subnets: [
      {
        addressPrefix: '10.0.0.0/26'
        name: 'GatewaySubnet'
      }
      {
        addressPrefix: '10.0.0.64/26'
        name: 'AzureBastionSubnet'
      }
      {
        addressPrefix: '10.0.0.128/27'
        name: 'snet-pe-001'
      }
      {
        addressPrefix: '10.0.0.160/27'
        name: 'snet-ghr-001'
      }
      {
        addressPrefix: '10.0.0.192/27'
        name: 'snet-jumpbox-001'
      }
      {
        addressPrefix: '10.0.1.0/24'
        name: 'snet-appsvc-001'
        delegations: [
          {
            name: 'appSvcDelegation'
            properties: {
              serviceName: 'Microsoft.Web/serverFarms'
            }
          }
        ]
      }
      {
        addressPrefix: '10.0.2.0/29'
        name: apimSubnetName
        networkSecurityGroupResourceId: apimNSG.outputs.resourceId
      }
    ]
    tags: mergedTags
  }
}

@description('Resource ID of the virtual network')
output virtualNetworkResourceId string = virtualNetwork.outputs.resourceId
@description('Resource IDs of the subnets')
output subnetResourceIds array = [
  virtualNetwork.outputs.subnetResourceIds
]
@description('Names of the subnets')
output subnetNames array = [
  virtualNetwork.outputs.subnetNames
]
@description('Resource ID of the subnet for Private Endpoints')
output privateEndpointSubnetResourceId string = virtualNetwork.outputs.subnetResourceIds[2]
@description('Resource ID of the subnet for Jumpbox VM')
output jumpboxSubnetResourceId string = virtualNetwork.outputs.subnetResourceIds[4]
@description('Resource ID of the subnet for appService')
output appServiceSubnetResourceId string = virtualNetwork.outputs.subnetResourceIds[5]
@description('Resource ID of the subnet for APIM')
output apimSubnetResourceId string = virtualNetwork.outputs.subnetResourceIds[6]
@description('Name of the virtual network')
output virtualNetworkName string = virtualNetwork.outputs.name
