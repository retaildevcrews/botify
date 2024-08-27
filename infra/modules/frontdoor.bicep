metadata name = 'Azure Front Door Module'
metadata description = 'This module deploys Azure Front Door and default WAF policies for frontend and backend'

@description('Name suffix for all resources in the module')
param resourceNameSuffix string
@allowed([
  'Prevention'
  'Detection'
])
@description('The mode of the WAF policy. Defaults to Detection.')
param wafPolicyMode string = 'Detection'
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}

var mergedTags = {
  ...tags
  module: 'frontdoor'
}

// Deploy Azure Front Door
module frontDoor 'br/public:avm/res/cdn/profile:0.3.0' = {
  name: 'cdnProfileDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: 'afd-${resourceNameSuffix}-001'
    // Premium is required access to Private Link
    sku: 'Premium_AzureFrontDoor'
    location: 'global'
    tags: mergedTags
  }
}

module backendWAFPolicy 'br/public:avm/res/network/front-door-web-application-firewall-policy:0.1.1' = {
  name: 'frontDoorWAFPolicyDeployment-backend-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: replace('wafbackend${resourceNameSuffix}001', '-', '')
    // Premium is required for access to managed rules.
    sku: 'Premium_AzureFrontDoor'
    policySettings: {
      enabledState: 'Enabled'
      mode: wafPolicyMode
      customBlockResponseBody: base64('WAF Policy violation')
    }
    managedRules: {
      managedRuleSets: [
        {
          ruleSetType: 'Microsoft_DefaultRuleSet'
          ruleSetVersion: '2.1'
          ruleSetAction: 'Block'
        }
        {
          ruleSetType: 'Microsoft_BotManagerRuleSet'
          ruleSetVersion: '1.1'
        }
      ]
    }
    customRules: {}
    tags: mergedTags
  }
}

@description('The name of the Front Door')
output frontDoorName string = frontDoor.outputs.name
@description('The resource ID of the backend WAF Policy')
output backendWafPolicyName string = backendWAFPolicy.outputs.name
