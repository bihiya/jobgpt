param jobName string
param principalId string

resource job 'Microsoft.App/jobs@2024-03-01' existing = {
  name: jobName
}

// Contributor scoped to this job (includes Microsoft.App/jobs/start/action)
resource role 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(job.id, principalId, 'b24988ac-6180-42a0-ab88-20f7382dd24c')
  scope: job
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'b24988ac-6180-42a0-ab88-20f7382dd24c'
    )
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
