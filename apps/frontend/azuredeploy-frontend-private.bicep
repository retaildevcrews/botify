metadata name = 'Chatbot Front End'
metadata description = 'This module deploys private networking resources for the chatbot frontend'

@description('The Azure region where resources will be deployed. Defaults to the resource group location.')
param location string = resourceGroup().location
@description('Name suffix for all resources in the module. Format: project-environment-region, Ex: chatbot-dev-use2')
@minLength(3)
param resourceNameSuffix string
@description('The name of the App Service Container app for the frontend UI. Ex: botify-ui')
param uiAppName string = 'frontend'
@description('Array of secret names to be stored in Key Vault for application configuration. Defaults to an empty array.')
param uiConfigurationSecretNames array = []
@description('Array of app settings key value pairs. Default is an empty array.')
param uiConfigurationValues array = []
@description('The container image reference for the UI in the format "repository/image:tag". Ex: retaildevcrews/botify-ui:latest')
param uiContainerImage string
@description('The name of an existing ACR to pull the UI container image from.')
param existingAcrName string
@description('The name of an existing Key Vault for application secrets')
param existingKeyVaultName string = 'kv-${resourceNameSuffix}-001'
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
@description('Determines whether the Cognitive Services Account for Speech has public access enabled. Defaults to true.')
param speechPublicAccessEnabled bool = true
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
}

resource existingAppSvcPrivateDnsZone 'Microsoft.Network/privateDnsZones@2018-09-01' existing = {
  name: privateDnsZoneName
}

resource existingSpeechPrivateDnsZone 'Microsoft.Network/privateDnsZones@2018-09-01' existing = {
  name: 'privatelink-speech.cognitiveservices.azure.com'
}

var appServiceSubnetId =  filter(existingVnet.properties.subnets, s => s.name == appServiceSubnetName)[0].id
var privateEndpointSubnetId =  filter(existingVnet.properties.subnets, s => s.name == privateEndpointSubnetName)[0].id

// Use an existing ACR if provided
resource existingRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = {
  name: existingAcrName
}

var uiImageReference = '${existingRegistry.properties.loginServer}/${uiContainerImage}'

var useExistingCognitiveSpeechServices = (contains(vaultSecrets, 'AzureSpeechEndpoint') && contains(
  vaultSecrets,
  'AzureSpeechApiKey'
) && contains(uiConfigurationValues, 'AZURE_SPEECH_REGION'))
? true
: false

// Set region from deployed cognitive Speech Service
var azureSpeechServiceRegion = useExistingCognitiveSpeechServices ? [] : ['AZURE_SPEECH_REGION=${speechServicesAccount.outputs.location}']

// Deploys Cognitive Services Account for UI appService
module speechServicesAccount 'br/public:avm/res/cognitive-services/account:0.5.3' = {
  name: 'speechServicesAccountDeployment-ui-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: 'spch-${resourceNameSuffix}-001'
    location: location
    kind: 'SpeechServices'
    publicNetworkAccess: speechPublicAccessEnabled ? 'Enabled' : 'Disabled'
    networkAcls: {
      defaultAction: speechPublicAccessEnabled ? 'Allow' : 'Deny'
      bypass: 'AzureServices'
      ipRules: []
      virtualNetworkRules: []
    }
    customSubDomainName: resourceNameSuffix
    disableLocalAuth: speechPublicAccessEnabled ? false : true
    privateEndpoints: [
      {
        subnetResourceId: privateEndpointSubnetId
        privateDnsZoneResourceIds: [
          existingSpeechPrivateDnsZone.id
        ]
        privateDnsZoneGroupName: 'default'
      }
    ]
    tags: tags
  }
}

// Store sensitive Cognitive Speech Services Account values in Key Vault
module speechServicesSecrets '../../infra/modules/cogsecrets.bicep' = if (!useExistingCognitiveSpeechServices) {
  name: 'speechServicesSecretsDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    cognitiveServicesAccountName: speechServicesAccount.outputs.name
    vaultName: existingKeyVaultName
    apiKeySecretName: 'AzureSpeechApiKey'
    endPointSecretName: 'AzureSpeechEndpoint'
  }
}

// Deploys an App Service Plan and App Service Container for the UI
module appServiceUI '../../infra/modules/appservice.bicep' = {
  name: 'appserviceUIDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    resourceNameSuffix: resourceNameSuffix
    appName: uiAppName
    containerImageReference: uiImageReference
    containerRegistryId: existingRegistry.id
    location: location
    appServiceSubnetId: appServiceSubnetId
    privateEndpointSubnetId: privateEndpointSubnetId
    privateDnsZoneId: existingAppSvcPrivateDnsZone.id
    appConfigurationValues: union(azureSpeechServiceRegion, uiConfigurationValues)
    appConfigurationSecretNames: uiConfigurationSecretNames
    existingKeyVaultName: existingKeyVaultName
    publicNetworkAccess: 'Enabled'
    tags: tags
  }
}

output frontendUrl string = 'https://${appServiceUI.outputs.appServiceDefaultDomainName}'
