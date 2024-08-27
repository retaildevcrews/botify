metadata name = 'Logging components'
metadata description = 'This module deploys App Insights, Log Analytics Workspace, and Alerts for logging purposes'

@description('The suffix for the name of the resources that will be created')
param resourceNameSuffix string
@description('Public network access for Ingestion. Default is Enabled.')
param publicNetworkAccessIngestion string = 'Enabled'
@description('Public network access for Ingestion. Default is Enabled.')
param publicNetworkAccessQuery string = 'Enabled'
@description('Location for all resources. Defaults to the resource group location')
param location string = resourceGroup().location
@description('Retention days for logs. Default is 30 days.')
param retentionDays int = 30
@description('Email address to receive alerts. If not provided, no alerts or alert group will be created.')
param alertsEmail string = ''
@description('Jailbreak alert name')
param jailbreakAlertName string = 'malicious-jailbreak-attempts-detected'
@description('Malicious contents alert name')
param maliciousContentsAlertName string = 'malicious-prompt-contents-detected'
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}
var mergedTags = {
  ...tags
  module: 'logging'
}

module workspace 'br/public:avm/res/operational-insights/workspace:0.3.4' = {
  name: 'workspaceDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    // Required parameters
    name: 'log-${resourceNameSuffix}-001'
    // Non-required parameters
    location: location
    tags: mergedTags
  }
}

module applicationInsights 'br/public:avm/res/insights/component:0.3.0' = {
  name: 'applicationInsightsDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    // Required parameters
    name: 'appi-${resourceNameSuffix}-001'
    workspaceResourceId: workspace.outputs.resourceId
    // Non-required parameters
    location: location
    applicationType: 'web'
    disableIpMasking: false
    disableLocalAuth: false
    forceCustomerStorageForProfiler: false
    publicNetworkAccessForIngestion: publicNetworkAccessIngestion
    publicNetworkAccessForQuery: publicNetworkAccessQuery
    retentionInDays: retentionDays
    tags: mergedTags
  }
}

module actionGroup 'br/public:avm/res/insights/action-group:0.2.5' = if (alertsEmail != '') {
  name: 'actionGroupDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    // Required parameters
    name: 'malicious-prompt-alerts'
    groupShortName: 'prompt-alert'
    // Non-required parameters
    location: 'global'
    tags: mergedTags
    enabled: true
    emailReceivers: [
      {
        name: 'Email0_-EmailAction-'
        emailAddress: alertsEmail
        commonAlertSchema: true
      }
    ]
  }
}

module jailbreakAlert 'br/public:avm/res/insights/scheduled-query-rule:0.1.4' = if (alertsEmail != '') {
  name: 'jailbreakAlertDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: jailbreakAlertName
    alertDescription: 'Detected jailbreak attempts'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    scopes: [
      applicationInsights.outputs.resourceId
    ]
    targetResourceTypes: [
      'microsoft.insights/components'
    ]
    windowSize: 'PT5M'
    criterias: {
      allOf: [
        {
          query: 'dependencies\n| where name=="content_safety.langchain.workflow" and customDimensions[\'attackDetected\']==True\n| project timestamp, promptShieldSpanAttributes=customDimensions, operation_Id\n| join kind=inner (\n    dependencies\n    | where name=="call_model.langchain.workflow"\n    | project callModelSpanAttributes=customDimensions, operation_Id\n    )\n    on operation_Id\n'
          timeAggregation: 'Count'
          dimensions: []
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    autoMitigate: false
    actions: [
      actionGroup.outputs.resourceId
    ]
  }
}

module maliciousContentsAlert 'br/public:avm/res/insights/scheduled-query-rule:0.1.4' = if (alertsEmail != '') {
  name: 'maliciousContentsAlertDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: maliciousContentsAlertName
    alertDescription: 'Five or more malicious prompt contents detected'
    severity: 3
    enabled: true
    evaluationFrequency: 'PT5M'
    scopes: [
      applicationInsights.outputs.resourceId
    ]
    targetResourceTypes: [
      'microsoft.insights/components'
    ]
    windowSize: 'PT5M'
    criterias: {
      allOf: [
        {
          query: 'dependencies\n| where name=="content_safety.langchain.workflow" and customDimensions["harmful_prompt_detected"]==True\n| project timestamp, contentModerationSpanAttributes=customDimensions, operation_Id\n| join kind=inner (\n    dependencies\n    | where name=="call_model.langchain.workflow"\n    | project callModelSpanAttributes=customDimensions, operation_Id\n    )\n    on operation_Id\n'
          timeAggregation: 'Count'
          dimensions: []
          operator: 'GreaterThan'
          threshold: 4
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    autoMitigate: false
    actions: [
      actionGroup.outputs.resourceId
    ]
  }
}
