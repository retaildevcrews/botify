using '../azuredeploy-entra-auth.bicep'

param appServiceName=readEnvironmentVariable('BACKEND_WEB_APP_NAME', 'app-backend-btfy-dev-use2-001')

param appRegistrationSecret=readEnvironmentVariable('APP_REGISTRATION_CLIENT_SECRET', '')

param appRegistrationId=readEnvironmentVariable('APP_REGISTRATION_ID','')

param authenticationRequired=true

param unauthenticatedClientAction='Return401'

param allowedApplications=readEnvironmentVariable('ALLOWED_APPLICATIONS','')
