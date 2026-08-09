param keyVaultName string
param principalId string

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

// Key Vault Secrets User
resource role 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(kv.id, principalId, '4633458b-17de-408a-b874-0445c86b69e6')
  scope: kv
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6'
    )
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
