metadata name = 'Token Service'
metadata description = 'This module deploys a token service app'

@description('The Azure region where resources will be deployed. Defaults to the resource group location.')
param location string = resourceGroup().location
@description('Name suffix for all resources in the module. Format: project-environment-region, Ex: chatbot-dev-use2')
@minLength(3)
param resourceNameSuffix string
@description('The name of the App Service Container app. Ex: tokenservice')
param appName string = 'tokenservice'
@description('Array of secret names to be stored in Key Vault for application configuration. Defaults to an empty array.')
param configurationSecretNames array = []
@description('Array of app settings key value pairs. Default is an empty array.')
param configurationValues array = []
@description('The container image reference in the format "repository/image:tag". Ex: retaildevcrews/botify-ui:latest')
param containerImage string
@description('The name of an existing ACR to pull the container image from.')
param existingAcrName string
@description('The name of an existing Key Vault for application secrets')
param existingKeyVaultName string = 'kv-${resourceNameSuffix}-001'
@description('The name of an existing Speech Service')
param existingSpeechServiceName string = 'spch-${resourceNameSuffix}-001'
@description('The name of the existing API Management instance to deploy the API to. Defaults to an empty string.')
param existingApimName string = ''
@description('Determines if an API subscription is required to access the API. Defaults to true.')
param apimSubscriptionRequired bool = true
@description('The name of the existing Front Door to associate with the API.')
param existingFrontdoorName string = ''
@description('Secrets to be stored in the deployed Key Vault. Defaults to an empty object.')
@secure()
param vaultSecrets object = {}
@description('The name of the existing VNet to deploy the resources into.')
param existingVnetName string = 'vnet-${resourceNameSuffix}-001'
@description('The name of the existing subnet for the App Service.')
param appServiceSubnetName string = 'snet-appsvc-001'
@description('The name of the existing subnet for the private endpoint.')
param privateEndpointSubnetName string = 'snet-pe-001'
@description('The name of the existing private DNS zone for the App Service.')
param privateDnsZoneName string = 'privatelink.azurewebsites.net'
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}

resource existingVnet 'Microsoft.Network/virtualNetworks@2021-02-01' existing = {
  name: existingVnetName
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
  resource speechResource 'secrets@2023-07-01' = {
    name: 'AzureSpeechResource'
    properties: {
      value: existingSpeechService.id
    }
  }
}

resource existingAppSvcPrivateDnsZone 'Microsoft.Network/privateDnsZones@2018-09-01' existing = {
  name: privateDnsZoneName
}

resource existingSpeechService 'Microsoft.CognitiveServices/accounts@2021-04-30' existing = {
  name: existingSpeechServiceName
}

resource existingApim 'Microsoft.ApiManagement/service@2023-05-01-preview' existing = if (existingApimName != '') {
  name: existingApimName
}

resource existingCdnProfile 'Microsoft.Cdn/profiles@2024-02-01' existing = if (existingFrontdoorName != '') {
  name: existingFrontdoorName
}

var appServiceSubnetId =  filter(existingVnet.properties.subnets, s => s.name == appServiceSubnetName)[0].id
var privateEndpointSubnetId =  filter(existingVnet.properties.subnets, s => s.name == privateEndpointSubnetName)[0].id

// Use an existing ACR if provided
resource existingRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = {
  name: existingAcrName
}

var imageReference = '${existingRegistry.properties.loginServer}/${containerImage}'

// Create an identity for the App
module userAssignedIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.2.1' = {
  name: 'userAssignedIdentityDeployment-${appName}-${uniqueString(resourceGroup().id, appName)}'
  params: {
    location: location
    name: 'umi-${appName}-${resourceNameSuffix}-001'
    tags: tags
  }
}

// Allow App to use speech service
// Cognitive Services Speech Services User. See https://github.com/Azure/bicep-registry-modules/blob/main/avm/res/cognitive-services/account/main.bicep
module roleAssignmentSpeechUser 'br/public:avm/ptn/authorization/resource-role-assignment:0.1.0' = {
  name: 'appServiceSpeechUser-${appName}-${uniqueString(resourceGroup().id, appName)}'
  params: {
    principalId: userAssignedIdentity.outputs.principalId
    resourceId: existingSpeechService.id
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', 'f2dc8367-1007-4938-bd23-fe263f013447')
  }
}

// Deploys an App Service Plan and App Service Container for the UI
module appService '../../infra/modules/appservice.bicep' = {
  name: 'appserviceTokenServiceDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    resourceNameSuffix: resourceNameSuffix
    appName: appName
    existingManagedIdentityName: userAssignedIdentity.outputs.name
    containerImageReference: imageReference
    containerRegistryId: existingRegistry.id
    location: location
    appServiceSubnetId: appServiceSubnetId
    privateEndpointSubnetId: privateEndpointSubnetId
    privateDnsZoneId: existingAppSvcPrivateDnsZone.id
    appConfigurationValues: union(configurationValues, ['AZURE_CLIENT_ID=${userAssignedIdentity.outputs.clientId}'])
    appConfigurationSecretNames: configurationSecretNames
    existingKeyVaultName: existingKeyVaultName
    publicNetworkAccess: 'Disabled'
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
    displayName: 'Token Service'
    path: '/token'
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

output tokenServiceUrl string = 'https://${appService.outputs.appServiceDefaultDomainName}'
