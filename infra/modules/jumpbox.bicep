metadata name = 'Jumpbox and Bastion Host Deployment'
metadata description = 'This module deploys a Jumpbox and Bastion Host in the specified virtual network'
@description('Name suffix for all resources in the module')
param resourceNameSuffix string
@description('name of admin user for the jumpbox')
param jumpboxAdminUsername string = 'jumpboxadmin'
@description('Virtual network where the jumpbox and bastion will be deployed')
param virtualNetworkResourceId string
@description('Subnet where the jumpbox will be deployed')
param subnetResourceId string
@description('name of existing keyvault containing the password for admin user')
param existingKeyvaultName string 
@description('name of existing secret in keyvault containing the password for admin user')
param jumpboxSecretName string 
@description('Size of the virtual machine')
param vmSize string = 'Standard_DS2_v2'
@description('Operating system type')
param osType string = 'Windows'
@description('Image offer')
param imageOffer string = 'WindowsServer'
@description('Image publisher')
param imagePublisher string = 'MicrosoftWindowsServer'
@description('Image SKU')
param imageSku string = '2022-datacenter-azure-edition'
@description('Image version')
param imageVersion string = 'latest'
@description('Size of the OS disk in GB')
param osDiskSizeGB int = 128
@description('Type of OS disk')
param osDiskType string = 'Premium_LRS'
@description('Whether to use system-assigned identity')
param useSystemAssignedIdentity bool = true
@description('Whether to enable auto-shutdown')
param autoShutdown string = 'Enabled'
@description('Time to shut down the VM')
param shutdownTime string = '01:00'
@description('Time zone for auto-shutdown')
param timeZone string = 'UTC'
@description('Size of the bastion host')
param bastionHostSku string = 'Standard'
@description('Tags to be applied to all resources. Defaults to an empty object.')
param tags object = {}

var mergedTags = {
  ...tags
  module: 'jumpbox'
}

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: existingKeyvaultName
}
// Omit the resource name suffix from the hostname to avoid exceeding the 15-character limit in Windows
var hostname = osType == 'Windows' ? 'vm-jumpbox' : 'vm-jumpbox-${resourceNameSuffix}'

module virtualMachine 'br/public:avm/res/compute/virtual-machine:0.4.2' = {
  name: 'jumpboxVMDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    adminUsername: jumpboxAdminUsername
    imageReference: {
      offer: imageOffer
      publisher: imagePublisher
      sku: imageSku
      version: imageVersion
    }
    name: '${hostname}-001'
    managedIdentities: {
      systemAssigned: useSystemAssignedIdentity
    }
    encryptionAtHost: false
    nicConfigurations: [
      {
        ipConfigurations: [
          {
            name: 'ipconfig01'
            subnetResourceId: subnetResourceId
          }
        ]
        nicSuffix: '-nic-01'
      }
    ]
    osDisk: {
      caching: 'ReadWrite'
      diskSizeGB: osDiskSizeGB
      managedDisk: {
        storageAccountType: osDiskType
      }
    }
    osType: osType
    vmSize: vmSize
    zone: 0
    adminPassword: kv.getSecret(jumpboxSecretName)
    autoShutdownConfig: {
      time: shutdownTime
      dailyRecurrenceTime: shutdownTime
      status: autoShutdown
      timeZone: timeZone
    }
    tags: mergedTags
  }
}

module bastionHost 'br/public:avm/res/network/bastion-host:0.2.1' = {
  name: 'bastionHostDeployment-${uniqueString(resourceGroup().id, resourceNameSuffix)}'
  params: {
    name: 'bas-${resourceNameSuffix}-001'
    skuName: bastionHostSku
    virtualNetworkResourceId: virtualNetworkResourceId
    tags: mergedTags
  }
}
