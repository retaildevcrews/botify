metadata name = 'Azure Front Door Security Profile'
metadata description = 'This module associates Front Door with a WAF Policy'

@description('Name of the Azure Front Door to attach the WAF to')
param frontDoorName string

@description('Name of the WAF to attach the Front Door to')
param frontDoorWAFName string

@description('Name of the endpoint defined on the Front Door')
param frontDoorEndpointName string

param logAnalyticsWorkspaceName string = ''
// Existing Azure Front Door
resource frontDoor 'Microsoft.Cdn/profiles@2023-05-01' existing = {
  name: frontDoorName
}

// Existing Front Door WAF policy
resource frontDoorWAF 'Microsoft.Network/FrontDoorWebApplicationFirewallPolicies@2022-05-01' existing = {
  name: frontDoorWAFName
}

// Existing Front Door endpoint 
resource frontDoorEndpoint 'Microsoft.Cdn/profiles/afdEndpoints@2023-05-01' existing = {
  name: frontDoorEndpointName
  parent: frontDoor
}

resource existingLogAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = if (logAnalyticsWorkspaceName != '') {
  name: logAnalyticsWorkspaceName
}

// Associate WAF policy with Front Door
resource wafPolicyAssociation 'Microsoft.Cdn/profiles/securityPolicies@2023-05-01' = {
  name: frontDoorEndpointName
  parent: frontDoor
  properties: {
    parameters: {
      wafPolicy: {
        id: frontDoorWAF.id
      }
      associations: [
        {
          domains: [
            {
              id: frontDoorEndpoint.id
            }
          ]
          patternsToMatch: [
            '/*'
          ]
        }
      ]
      type: 'WebApplicationFirewall'
    }
  }
}

resource logAnalyticsWorkspaceDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (logAnalyticsWorkspaceName != ''){
  scope: frontDoor
  name: 'diagnosticSettings'
  properties: {
    workspaceId: existingLogAnalyticsWorkspace.id
    logs: [
      {
        category: 'FrontDoorWebApplicationFirewallLog'
        enabled: true
      }
    ]
  }
}
