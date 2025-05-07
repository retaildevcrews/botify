param cognitiveServiceName string
param location string
param cognitiveServiceSKU string
param contentsafetyName string

resource cognitiveService 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: cognitiveServiceName
  location: location
  sku: {
    name: cognitiveServiceSKU
  }
  kind: 'CognitiveServices'
}

resource contentsafetyaccount 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: contentsafetyName
  location: location
  kind: 'ContentSafety'
  sku: {
    name: cognitiveServiceSKU
  }
  properties: {
  }
}

output cognitiveServiceKey string = cognitiveService.listKeys().key1
output contentSafetyEndpoint string = contentsafetyaccount.properties.endpoint
output contentSafetyKey string = contentsafetyaccount.listKeys().key1
