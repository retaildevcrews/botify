using 'azuredeploy-entra-auth.bicep'

param appServiceName=readEnvironmentVariable('FRONTEND_UI_WEB_APP_NAME', '')

param appRegistrationSecret=readEnvironmentVariable('APP_REGISTRATION_CLIENT_SECRET', '')

param appRegistrationId=readEnvironmentVariable('APP_REGISTRATION_ID','')

