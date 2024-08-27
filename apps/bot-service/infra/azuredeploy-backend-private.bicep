metadata name = 'Chatbot Backend'
metadata description = 'This module deploys private networking resources for the chatbot backend'

@description('The Azure region where resources will be deployed. Defaults to the resource group location.')
param location string = resourceGroup().location
@description('Name suffix for all resources in the module. Format: project-environment-region, Ex: chatbot-dev-use2')
@minLength(3)
param resourceNameSuffix string
@description('The name of the App Service Container app for the backend API. Ex: botify-api')
param appName string = 'backend'
@description('Array of secret names to be stored in Key Vault for application configuration. Defaults to an empty array.')
param appConfigurationSecretNames array = []
@description('Array of app settings key value pairs. Default is an empty array.')
param appConfigurationValues array = []
@description('Secrets to be stored in the deployed Key Vault. Defaults to an empty object.')
@secure()
param vaultSecrets object = {}
@description('The container image reference for the API in the format "repository/image:tag". Ex: retaildevcrews/botify-api:latest')
param appContainerImage string
@description('The name of an existing ACR to pull the API container image from.')
param existingAcrName string
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
@description('The name of the existing API Management instance to deploy the API to. Defaults to an empty string.')
param existingApimName string = ''
@description('Determines if an API subscription is required to access the API. Defaults to true.')
param apimSubscriptionRequired bool = true
@description('The name of the existing Front Door to associate with the API.')
param existingFrontdoorName string = ''
@description('The name of the existing Front Door WAF to associate with the API.')
param existingFrontdoorWAFName string = ''
@description('Determines if the front door endpoint is enabled. Defaults to Enabled.')
@allowed([
  'Enabled'
  'Disabled'
])
param frontDoorEndpointState string = 'Enabled'
@description('Name of the front door endpoint. If empty will default to app name plus unique string.')
param frontDoorEndpointName string = ''
@description('The name of the existing Log Analytics workspace to associate with the Front Door.')
param existingLogAnalyticsWorkspaceName string = ''
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}

resource existingVnet 'Microsoft.Network/virtualNetworks@2021-02-01' existing = {
  name: existingVnetName
}

resource existingAppSvcPrivateDnsZone 'Microsoft.Network/privateDnsZones@2018-09-01' existing = {
  name: privateDnsZoneName
}

resource existingKeyVault 'Microsoft.KeyVault/vaults@2021-06-01-preview' existing = {
  name: existingKeyVaultName
  resource secrets 'secrets@2023-07-01' = [
    for secret in items(vaultSecrets): {
      name: secret.key
      properties: {
        value: secret.value
      }
    }
  ]
}

resource existingApim 'Microsoft.ApiManagement/service@2023-05-01-preview' existing = if (existingApimName != '') {
  name: existingApimName
}

var appServiceSubnetId = filter(existingVnet.properties.subnets, s => s.name == appServiceSubnetName)[0].id
var privateEndpointSubnetId = filter(existingVnet.properties.subnets, s => s.name == privateEndpointSubnetName)[0].id

var permittedIpAddresses = union(
  allowedIpAddresses,[]
)
// Use an existing ACR if provided
resource existingRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = {
  name: existingAcrName
}

var apiImageReference = '${existingRegistry.properties.loginServer}/${appContainerImage}'

resource existingCdnProfile 'Microsoft.Cdn/profiles@2024-02-01' existing = if (existingFrontdoorName != '') {
  name: existingFrontdoorName
}

resource existingFrontdoorWAF 'Microsoft.Network/FrontDoorWebApplicationFirewallPolicies@2024-02-01' = if (existingFrontdoorWAFName != '') {
  name: existingFrontdoorWAFName
  sku: {
    name: 'Premium_AzureFrontDoor'
  }
  location: 'global'
}

// Deploys an App Service Plan and App Service Container for the backend API
module appService '../../../infra/modules/appservice.bicep' = {
  name: 'appserviceDeployment-${appName}-${uniqueString(resourceGroup().id, resourceNameSuffix, appName)}'
  params: {
    resourceNameSuffix: resourceNameSuffix
    appName: appName
    containerImageReference: apiImageReference
    containerRegistryId: existingRegistry.id
    location: location
    appServiceSubnetId: appServiceSubnetId
    privateEndpointSubnetId: privateEndpointSubnetId
    privateDnsZoneId: existingAppSvcPrivateDnsZone.id
    appConfigurationValues: appConfigurationValues
    appConfigurationSecretNames: appConfigurationSecretNames
    existingKeyVaultName: existingKeyVaultName
    publicNetworkAccess: length(permittedIpAddresses) < 1 ? 'Disabled' : 'Enabled'
    allowedIpAddresses: permittedIpAddresses
    vnetRouteAllEnabled: true
    tags: tags
  }
}

resource apimBackend 'Microsoft.ApiManagement/service/backends@2023-05-01-preview' = if (existingApimName != '') {
  name: 'app-${appName}-${resourceNameSuffix}'
  parent: existingApim
  properties: {
    url: 'https://${appService.outputs.appServiceDefaultDomainName}'
    protocol: 'http'
    resourceId: '${environment().resourceManager}/${appService.outputs.appServiceResourceId}'
    credentials: {
      header: {
        'x-functions-key': ['${appService.outputs.appServiceName}']
      }
    }
  }
}
// Include FDID check in the APIM policy if a Front Door is provided
var apimPolicyXml = existingFrontdoorName != ''
? '<policies>\r\n  <inbound>\r\n    <base />\r\n    <check-header name="X-Azure-FDID" failed-check-httpcode="403" failed-check-error-message="frontdoorID mismatch" ignore-case="false">\r\n    <value>${existingCdnProfile.properties.frontDoorId}</value>\r\n    </check-header>\r\n    <set-backend-service id="apim-generated-policy" backend-id="${apimBackend.name}" />\r\n  </inbound>\r\n  <backend>\r\n    <base />\r\n  </backend>\r\n  <outbound>\r\n    <base />\r\n  </outbound>\r\n  <on-error>\r\n    <base />\r\n  </on-error>\r\n</policies>'
: '<policies>\r\n  <inbound>\r\n    <base />\r\n    <set-backend-service id="apim-generated-policy" backend-id="${apimBackend.name}" />\r\n  </inbound>\r\n  <backend>\r\n    <base />\r\n  </backend>\r\n  <outbound>\r\n    <base />\r\n  </outbound>\r\n  <on-error>\r\n    <base />\r\n  </on-error>\r\n</policies>'

resource publishApiToApim 'Microsoft.ApiManagement/service/apis@2023-05-01-preview' = if (existingApimName != '') {
  name: 'app-${appName}-${resourceNameSuffix}'
  parent: existingApim
  dependsOn: [
    appService
  ]
  properties: {
    displayName: 'Botify API'
    path: '/'
    protocols: [
      'https'
    ]
    subscriptionRequired: apimSubscriptionRequired
    subscriptionKeyParameterNames: {
      header: 'Ocp-Apim-Subscription-Key'
      query: 'subscription-key'
    }
    apiRevision: '1'
  }
  resource defaultPolicy 'policies' = {
    name: 'policy'
    properties: {
      format: 'rawxml'
      value: apimPolicyXml
    }
  }
  resource getAll 'operations' = {
    name: 'get'
    properties: {
      displayName: 'Get'
      method: 'GET'
      urlTemplate: '/*'
    }
  }
  resource postAll 'operations' = {
    name: 'post'
    properties: {
      displayName: 'Post'
      method: 'POST'
      urlTemplate: '/*'
    }
  }
  resource putAll 'operations' = {
    name: 'put'
    properties: {
      displayName: 'Put'
      method: 'PUT'
      urlTemplate: '/*'
    }
  }
  resource patchAll 'operations' = {
    name: 'patch'
    properties: {
      displayName: 'Patch'
      method: 'PATCH'
      urlTemplate: '/*'
    }
  }
  resource deleteAll 'operations' = {
    name: 'delete'
    properties: {
      displayName: 'Delete'
      method: 'DELETE'
      urlTemplate: '/*'
    }
  }
  resource head 'operations' = {
    name: 'head'
    properties: {
      displayName: 'Head'
      method: 'HEAD'
      urlTemplate: '/*'
    }
  }
  resource options 'operations' = {
    name: 'opt'
    properties: {
      displayName: 'Opt'
      method: 'OPTIONS'
      urlTemplate: '/*'
    }
  }
  resource trace 'operations' = {
    name: 'trace'
    properties: {
      displayName: 'TRACE'
      method: 'TRACE'
      urlTemplate: '/*'
    }
  }
}

resource devSubscription 'Microsoft.ApiManagement/service/subscriptions@2023-05-01-preview' = {
  name: 'dev'
  parent: existingApim
  properties: {
    scope: publishApiToApim.id
    displayName: 'Backend Dev Subscription'
    state: 'active'
    allowTracing: true
  }
}

// Store subscription key in Key Vault for access by other components
resource devSubscriptionKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'ApimDevKey'
  parent: existingKeyVault
  properties: {
    value: devSubscription.listSecrets().primaryKey
  }
}

module frontDoorConnect '../../../infra/modules/frontdoor-connect.bicep' = if (existingFrontdoorName != '') {
  name: 'frontdoorConnect-backend-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    frontDoorName: existingFrontdoorName
    appName: appName
    endpointName: frontDoorEndpointName
    appHostName: existingApim.properties.hostnameConfigurations[0].hostName
    wafPolicyName: existingFrontdoorWAFName
    endpointState: frontDoorEndpointState
    logAnalyticsWorkspaceName: existingLogAnalyticsWorkspaceName
  }
}

// Store backend API URL in Key Vault for access by other components
resource backendUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  name: 'BackendUrl'
  parent: existingKeyVault
  properties: {
    value: existingFrontdoorName != '' && frontDoorEndpointState == 'Enabled' ? 'https://${frontDoorConnect.outputs.endpointHostName}' : 'https://${existingApim.properties.hostnameConfigurations[0].hostName}'
  }
}

output backendUrl string = existingFrontdoorName != '' && frontDoorEndpointState == 'Enabled' ? 'https://${frontDoorConnect.outputs.endpointHostName}' : 'https://${existingApim.properties.hostnameConfigurations[0].hostName}'
