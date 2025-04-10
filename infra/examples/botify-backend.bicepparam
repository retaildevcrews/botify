using '../../apps/bot-service/infra/azuredeploy-backend-private.bicep'

param resourceNameSuffix='btfy-dev-use2'
param appContainerImage = 'retaildevcrews/botify-backend:beta'
param existingAcrName = 'acrbtfydev001'
param existingApimName = 'apim-${resourceNameSuffix}-001'
param apimSubscriptionRequired = true
param existingFrontdoorName = 'afd-${resourceNameSuffix}-001'
param existingFrontdoorWAFName = replace('wafbackend${resourceNameSuffix}001', '-', '')
param existingLogAnalyticsWorkspaceName = 'log-${resourceNameSuffix}-001'

param vaultSecrets = {
  PromptShieldSubscriptionKey: readEnvironmentVariable('CONTENT_SAFETY_KEY','')
}

param appConfigurationValues = [
  'AZURE_OPENAI_API_VERSION=2024-08-01-preview'
  'AZURE_SEARCH_INDEX_NAME=cogsrch-index-coffee-from-json'
  'AZURE_SEARCH_API_VERSION=2024-05-01-preview'
  'AZURE_COSMOSDB_NAME=chatHistory'
  'AZURE_COSMOSDB_CONTAINER_NAME=completions'
  'AZURE_OPENAI_MODEL_NAME=gpt-4o'
  'CONTENT_SAFETY_ENDPOINT=${readEnvironmentVariable('CONTENT_SAFETY_ENDPOINT', 'https://aus-content-safety.cognitiveservices.azure.com/')}'
  'OPEN_TELEMETRY_COLLECTOR_ENDPOINT=https://app-collector-${resourceNameSuffix}-001.azurewebsites.net:443'
  'SEARCH_ENDPOINT_ENABLED=true'
]

param appConfigurationSecretNames = [
  'AZURE_SEARCH_ENDPOINT=AzureSearchEndpoint'
  'AZURE_SEARCH_KEY=AzureSearchKey'
  'AZURE_OPENAI_ENDPOINT=AzureOpenAIEndpoint'
  'AZURE_OPENAI_API_KEY=AzureOpenAIApiKey'
  'AZURE_COSMOSDB_ENDPOINT=AzureCosmosDBEndpoint'
  'AZURE_COSMOSDB_CONNECTION_STRING=AzureCosmosDBConnectionString'
  'AZURE_COMOSDB_CONNECTION_STRING=AzureCosmosDBConnectionString'
  'CONTENT_SAFETY_KEY=PromptShieldSubscriptionKey'
]

// Optional parameters
param tags = {
  environment: 'dev'
  app: 'botify'
  component: 'backend'
}
param frontDoorEndpointName = 'backend'
