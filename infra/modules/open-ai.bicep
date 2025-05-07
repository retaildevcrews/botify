param openaiServiceAccountName string
param location string
param cognitiveServiceSKU string
param modeldeploymentname string
param model string
param modelversion string
param capacity int

resource openAIService 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: openaiServiceAccountName
  location: location
  sku: {
    name: cognitiveServiceSKU
  }
  kind: 'AIServices'
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

resource azopenaideployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAIService
  name: modeldeploymentname
  properties: {
      model: {
          format: 'OpenAI'
          name: model
          version: modelversion
      }
  }
  sku: {
    name: 'Standard'
    capacity: capacity
  }
}

output azureOpenAIEndpoint string = openAIService.properties.endpoint
