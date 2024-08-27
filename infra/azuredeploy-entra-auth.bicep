metadata name = 'Entra Authentication Configuration'
metadata description = 'This module deploys AuthSettingsV2 object and adds required appSettings.'


@description('The name of an existing App Service for the UI.')
param appServiceName string

@description('The Id of the current Tenant.')
param tenantId string = tenant().tenantId

@description('Determines whether authentication is required. Defaults to true.')
param authenticationRequired bool = true

@description('The action to take when an unauthenticated client attempts to access the app. Defaults to Return302.')
param unauthenticatedClientAction string = 'Return302'

@description('The App Registration Id')
@secure()
param appRegistrationId string

@description('The App Registration Secret.')
@secure()
param appRegistrationSecret string

@description('The allowed applications for the app.')
param allowedApplications string = ''

// Get the global Azure authentication endpoint from Azure environment. e.g. 'https://login.microsoftonline.com'
var loginEndpoint = environment().authentication.loginEndpoint

// Create a new AppSettings object to support Entra Id Auth
var newAppSettingsObject = {
  MICROSOFT_PROVIDER_AUTHENTICATION_SECRET: appRegistrationSecret
  WEBSITE_AUTH_AAD_ALLOWED_TENANTS : tenantId
}

// Create a new AuthSettingsV2 object to support Entra Id Auth
var newAuthSettingsV2Object = {
   globalValidation: {
        requireAuthentication: authenticationRequired
        unauthenticatedClientAction: unauthenticatedClientAction
        redirectToProvider: 'azureActiveDirectory' 
      }
    httpSettings: {
        forwardProxy: {
          convention: 'Standard'
        }
        requireHttps: true
        routes: {
          apiPrefix: '/.auth'
        }
      }
     identityProviders: {
        azureActiveDirectory: {
          enabled: true
          login: {
            disableWWWAuthenticate: false
          }
          validation: {
            defaultAuthorizationPolicy: {
              allowedApplications: union(split(allowedApplications, ','),[appRegistrationId])
            }
          }          
          registration: {
            clientId: appRegistrationId
            clientSecretSettingName: 'MICROSOFT_PROVIDER_AUTHENTICATION_SECRET'
            openIdIssuer: '${loginEndpoint}${tenantId}/v2.0/'
          }
        }
      }
    login: {
        preserveUrlFragmentsForLogins: false
        tokenStore: {
          enabled: true
        }
      }
    platform: {
        enabled: true
        runtimeVersion: '~1'
    } 
  }


// Deploys an updates both AppSetting and AuthSetting for the frontend UI
module appSettings 'modules/entra-auth.bicep' = {
  name: '${deployment().name}-app-auth-settings'
  params: {
    appServiceName: appServiceName
    // App Settings
    newAppSettings: newAppSettingsObject
    currentAppSettings: list(resourceId('Microsoft.Web/sites/config', appServiceName, 'appsettings'), '2023-12-01').properties
    // Auth Settings
    newAuthSettingsV2: newAuthSettingsV2Object
  }
}
