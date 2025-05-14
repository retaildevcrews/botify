param cognitiveServiceName string
param location string
param cognitiveServiceSKU string

resource cognitiveService 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: cognitiveServiceName
  location: location
  sku: {
    name: cognitiveServiceSKU
  }
  kind: 'CognitiveServices'
  properties: {}
}

output cognitiveServiceKey string = cognitiveService.listKeys().key1
