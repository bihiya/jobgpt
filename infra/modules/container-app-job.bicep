param name string
param location string
param environmentId string
param containerImage string
param jobType string
param cpu string
param memory string
param replicaTimeout int
param env array
param secrets array
param tags object

var jobEnv = concat(env, [
  { name: 'JOB_TYPE', value: jobType }
])

resource job 'Microsoft.App/jobs@2024-03-01' = {
  name: name
  location: location
  tags: union(tags, { 'job-type': jobType })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: environmentId
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: replicaTimeout
      replicaRetryLimit: 1
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      secrets: secrets
    }
    template: {
      containers: [
        {
          name: 'worker'
          image: containerImage
          command: ['python', '-m', 'app.workers.run_job']
          env: jobEnv
          resources: {
            cpu: json(cpu)
            memory: memory
          }
        }
      ]
    }
  }
}

output name string = job.name
output principalId string = job.identity.principalId
