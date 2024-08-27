metadata name = 'Entra Authentication Configuration Module'
metadata description = 'This module updates AuthSettingsV2 and appSettings for the given App Service Name.'

@description('The name of an existing App Service for the UI.')
param appServiceName string


@description('The updated AppSettings partial structure for Entra ID Authentication integration.')
param newAppSettings object

@description('The existing AppSettings structure for Entra ID Authentication integration')
param currentAppSettings object

@description('The new AuthSettingsV2 object for Entra ID Authentication integration')
param newAuthSettingsV2 object


// Get the existing AppService
resource webAppService 'Microsoft.Web/sites@2023-12-01' existing = {
  name: appServiceName
}

// Update appsettings property
resource siteconfig 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: webAppService
  name: 'appsettings'
  properties: union(currentAppSettings, newAppSettings)
}

// Update authsettingsV2 property
resource authConfig 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: webAppService
  name:  'authsettingsV2'
  properties: newAuthSettingsV2
}
