using 'azuredeploy-tokenservice-private.bicep'

param resourceNameSuffix='btfy-dev-use2'
param containerImage = 'retaildevcrews/botify-tokenservice:beta'
param existingAcrName='acr${uniqueString(resourceNameSuffix)}'

param configurationValues = [
]

param configurationSecretNames = [
  'API_APP_ID=BackendAppId'
  'SPEECH_ENDPOINT=AzureSpeechEndpoint'
  'SPEECH_RESOURCE_ID=AzureSpeechResource'
]

// Optional parameters
param tags = {
  environment: 'dev'
  app: 'botify'
  component: 'tokenService'
}
param apimSubscriptionRequired = false
param existingApimName = 'apim-${resourceNameSuffix}-001'
param existingFrontdoorName = 'afd-${resourceNameSuffix}-001'
