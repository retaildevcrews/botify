using 'azuredeploy-collector-private.bicep'

param resourceNameSuffix='btfy-dev-use2'
param appContainerImage = 'otel/opentelemetry-collector-contrib:0.100.0'

param appConfigurationValues = [
  'WEBSITES_PORT=4318'
  'OTEL_CONFIG=${loadTextContent('../otel_config.yaml')}'
]

param appConfigurationSecretNames = [
  'APPLICATIONINSIGHTS_CONNECTION_STRING=AppInsightsConnectionString'
]

// Optional Parameters
param tags = {
  environment: 'dev'
  app: 'botify'
  component: 'collector'
}
