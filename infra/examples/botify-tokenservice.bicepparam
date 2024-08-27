using '../../apps/tokenservice/azuredeploy-tokenservice-private.bicep'

param resourceNameSuffix='btfy-dev-use2'
param containerImage = 'retaildevcrews/botify-tokenservice:beta'
param existingAcrName='acrbtfydev001'

param configurationValues = [
  'URL_PREFIX=/token'
  'ALLOWED_ORIGINS=https://app-frontend-btfy-dev-use2-001.azurewebsites.net,https://backend-cugxedaxbvhyf3eg.b01.azurefd.net'
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
