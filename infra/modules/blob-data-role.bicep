param storageAccountName string
param principalId string

resource st 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

// Storage Blob Data Contributor
resource role 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(st.id, principalId, 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  scope: st
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
    )
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
