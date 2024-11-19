@description('Required. Deployment Suffix.')
param deploymentSuffix string

@description('Required. Active Directory App ID.')
param appId string

@description('Required. Active Directory App Secret Value.')
@secure()
param appPassword string

@description('Required. The SAS token for the blob hosting your data.')
@secure()
param blobSASToken string

@description('Log Analytics Workspace Name to Use')
@minLength(0)
@maxLength(24)
param logAnalyticsWorkspaceName string

@description('Optional. The name of the resource group where the resources (Azure Search etc.) where deployed previously. Defaults to current resource group.')
param resourceGroupSearch string = resourceGroup().name

@description('Required. The name of the Azure Search service deployed previously.')
param azureSearchName string

@description('Required. The name of the Azure Search index to use.')
param azureSearchIndexName string

@description('Optional. The API version for the Azure Search service.')
param azureSearchAPIVersion string = '2024-05-01-preview'

@description('Required. The name of the Azure OpenAI resource deployed previously.')
param azureOpenAIName string

@description('Required. The API key of the Azure OpenAI resource deployed previously.')
@secure()
param azureOpenAIAPIKey string

@description('Optional. The model name for the Azure OpenAI service.')
param azureOpenAIModelName string = 'gpt-35-turbo-1106'

@description('Optional. The API version for the Azure OpenAI service.')
param azureOpenAIAPIVersion string = '2024-08-01-preview'

@description('Required. The name of the Azure CosmosDB.')
param cosmosDBAccountName string

@description('Required. The name of the Azure CosmosDB container.')
param cosmosDBContainerName string

@description('Optional. The globally unique and immutable bot ID. Also used to configure the displayName of the bot, which is mutable.')
param botId string = 'BotId-${uniqueString(resourceGroup().id)}-${deploymentSuffix}'

@description('Optional, defaults to F0. The pricing tier of the Bot Service Registration. Acceptable values are F0 and S1.')
@allowed([
  'F0'
  'S1'
])
param botSKU string = 'F0'

@description('Optional. The name of the new App Service Plan.')
param appServicePlanName string = 'AppServicePlan-Backend-${uniqueString(resourceGroup().id)}-${deploymentSuffix}'

@description('Optional, defaults to S3. The SKU of the App Service Plan. Acceptable values are B3, S3 and P2v3.')
@allowed([
  'B3'
  'S3'
  'P2v3'
])
param appServicePlanSKU string = 'S3'

@description('Optional, defaults to resource group location. The location of the resources.')
param location string = resourceGroup().location

// Existing Azure Container Registry
@description('Required, the name of the existing Azure Container Registry to pull images from')
param acrName string

@description('Optional, the container image from the registry to run')
param containerImage string = 'retaildevcrews/botify-backend:beta'

var publishingUsername = '$${botId}'
var webAppName = 'webApp-Backend-${botId}'
var siteHost = '${webAppName}.azurewebsites.net'
var botEndpoint = 'https://${siteHost}/api/messages'

// Existing Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2020-08-01' existing = {
  name: logAnalyticsWorkspaceName
  scope: resourceGroup(resourceGroupSearch)
}

// Existing Azure Search service.
resource azureSearch 'Microsoft.Search/searchServices@2021-04-01-preview' existing = {
  name: azureSearchName
  scope: resourceGroup(resourceGroupSearch)
}

// Existing Azure CosmosDB resource.
resource cosmosDB 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' existing = {
  name: cosmosDBAccountName
  scope: resourceGroup(resourceGroupSearch)
}

// Create a new Linux App Service Plan if no existing App Service Plan name was passed in.
resource appServicePlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: appServicePlanSKU
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// Create a Web App using a Linux App Service Plan.
resource webApp 'Microsoft.Web/sites@2022-09-01' = {
  name: webAppName
  location: location
  tags: { 'azd-service-name': 'backend' }
  kind: 'app,linux,container'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    enabled: true
    hostNameSslStates: [
      {
        name: '${webAppName}.azurewebsites.net'
        sslState: 'Disabled'
        hostType: 'Standard'
      }
      {
        name: '${webAppName}.scm.azurewebsites.net'
        sslState: 'Disabled'
        hostType: 'Repository'
      }
    ]
    serverFarmId: appServicePlan.id
    reserved: true
    scmSiteAlsoStopped: false
    clientAffinityEnabled: false
    clientCertEnabled: false
    hostNamesDisabled: false
    containerSize: 0
    dailyMemoryTimeQuota: 0
    httpsOnly: false
    siteConfig: {
      appSettings: [
        {
          name: 'MicrosoftAppId'
          value: appId
        }
        {
          name: 'MicrosoftAppPassword'
          value: appPassword
        }
        {
          name: 'BLOB_SAS_TOKEN'
          value: blobSASToken
        }
        {
          name: 'AZURE_SEARCH_ENDPOINT'
          value: 'https://${azureSearchName}.search.windows.net'
        }
        {
          name: 'AZURE_SEARCH_KEY'
          value: azureSearch.listAdminKeys().primaryKey
        }
        {
          name: 'AZURE_SEARCH_INDEX_NAME'
          value: azureSearchIndexName
        }
        {
          name: 'AZURE_SEARCH_API_VERSION'
          value: azureSearchAPIVersion
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: 'https://${azureOpenAIName}.openai.azure.com/'
        }
        {
          name: 'AZURE_OPENAI_API_KEY'
          value: azureOpenAIAPIKey
        }
        {
          name: 'AZURE_OPENAI_MODEL_NAME'
          value: azureOpenAIModelName
        }
        {
          name: 'AZURE_OPENAI_API_VERSION'
          value: azureOpenAIAPIVersion
        }
        {
          name: 'AZURE_COSMOSDB_ENDPOINT'
          value: 'https://${cosmosDBAccountName}.documents.azure.com:443/'
        }
        {
          name: 'AZURE_COSMOSDB_NAME'
          value: cosmosDBAccountName
        }
        {
          name: 'AZURE_COSMOSDB_CONTAINER_NAME'
          value: cosmosDBContainerName
        }
        {
          name: 'AZURE_COSMOSDB_CONNECTION_STRING'
          value: cosmosDB.listConnectionStrings().connectionStrings[0].connectionString
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'DOCKER_REGISTRY_SERVER_URL'
          value: 'https://${acrName}.azurecr.io'
        }
      ]
      cors: {
        allowedOrigins: [
          'https://botservice.hosting.portal.azure.net'
          'https://hosting.onecloud.azure-test.net/'
        ]
      }
    }
  }
}

resource webAppConfig 'Microsoft.Web/sites/config@2022-09-01' = {
  parent: webApp
  name: 'web'
  properties: {
    numberOfWorkers: 1
    defaultDocuments: [
      'Default.htm'
      'Default.html'
      'Default.asp'
      'index.htm'
      'index.html'
      'iisstart.htm'
      'default.aspx'
      'index.php'
      'hostingstart.html'
    ]
    netFrameworkVersion: 'v4.0'
    phpVersion: ''
    pythonVersion: ''
    nodeVersion: ''
    linuxFxVersion: 'DOCKER|${acrName}.azurecr.io/${containerImage}'
    acrUseManagedIdentityCreds: true
    requestTracingEnabled: false
    remoteDebuggingEnabled: false
    remoteDebuggingVersion: 'VS2017'
    httpLoggingEnabled: true
    logsDirectorySizeLimit: 35
    detailedErrorLoggingEnabled: false
    publishingUsername: publishingUsername
    scmType: 'None'
    use32BitWorkerProcess: true
    webSocketsEnabled: false
    alwaysOn: false
    appCommandLine: 'runserver.sh'
    managedPipelineMode: 'Integrated'
    virtualApplications: [
      {
        virtualPath: '/'
        physicalPath: 'site\\wwwroot'
        preloadEnabled: false
        virtualDirectories: null
      }
    ]
    loadBalancing: 'LeastRequests'
    experiments: {
      rampUpRules: []
    }
    autoHealEnabled: false
    vnetName: ''
    minTlsVersion: '1.2'
    ftpsState: 'FtpsOnly'
    publicNetworkAccess: 'Disabled'
  }
}

resource webApp_Microsoft_Insights_default 'Microsoft.Insights/diagnosticSettings@2017-05-01-preview' = {
  name: 'default'
  properties: {
    workspaceId: logAnalyticsWorkspace.id
  }
  scope: webApp
}

resource bot 'Microsoft.BotService/botServices@2022-09-15' = {
  name: botId
  location: 'global'
  kind: 'azurebot'
  sku: {
    name: botSKU
  }
  properties: {
    displayName: botId
    iconUrl: 'https://docs.botframework.com/static/devportal/client/images/bot-framework-default.png'
    endpoint: botEndpoint
    msaAppId: appId
    luisAppIds: []
    schemaTransformationVersion: '1.3'
    isCmekEnabled: false
  }
  dependsOn: [
    webApp
  ]
}

module roleAssignments 'role-assignments.bicep' = {
  name: 'role-assignments'
  params: {
    webAppPrincipalId: webApp.identity.principalId
    acrName: acrName
  }
}

output botServiceName string = bot.name
output webAppName string = webApp.name
output webAppUrl string = webApp.properties.defaultHostName
