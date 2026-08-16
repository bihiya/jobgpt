targetScope = 'resourceGroup'

param location string
param environmentName string
param resourceSuffix string
@secure()
param mongodbUrl string
@secure()
param redisUrl string
@secure()
param secretKey string
param corsOrigins string
param tags object
@description('Public Azure hostname origin included in API CORS (App Service azurewebsites.net).')
param publicWebOrigin string = 'https://jobpilot.azurewebsites.net'

// Placeholder until azd deploy pushes the real image and wires ACR.
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

var abbr = {
  acr: 'cr'
  kv: 'kv'
  log: 'log'
  appi: 'appi'
  cae: 'cae'
  ca: 'ca'
  job: 'job'
  st: 'st'
}

var acrName = toLower('${abbr.acr}jobpilot${resourceSuffix}')
var kvName = toLower(take('${abbr.kv}-jobpilot-${resourceSuffix}', 24))
var logName = '${abbr.log}-jobpilot-${resourceSuffix}'
var appiName = '${abbr.appi}-jobpilot-${resourceSuffix}'
var caeName = '${abbr.cae}-jobpilot-${resourceSuffix}'
var apiName = '${abbr.ca}-jobpilot-api-${resourceSuffix}'
var webName = '${abbr.ca}-jobpilot-web-${resourceSuffix}'
var fetchJobName = '${abbr.job}-jobpilot-fetch-${resourceSuffix}'
var matchJobName = '${abbr.job}-jobpilot-match-${resourceSuffix}'
var applyJobName = '${abbr.job}-jobpilot-apply-${resourceSuffix}'
var storageName = toLower(take('${abbr.st}jobpilot${resourceSuffix}', 24))
var blobContainerName = 'uploads'

module logAnalytics 'modules/log-analytics.bicep' = {
  name: 'logAnalytics'
  params: {
    name: logName
    location: location
    tags: tags
  }
}

module appInsights 'modules/app-insights.bicep' = {
  name: 'appInsights'
  params: {
    name: appiName
    location: location
    workspaceResourceId: logAnalytics.outputs.id
    tags: tags
  }
}

module acr 'modules/container-registry.bicep' = {
  name: 'acr'
  params: {
    name: acrName
    location: location
    tags: tags
  }
}

module keyVault 'modules/key-vault.bicep' = {
  name: 'keyVault'
  params: {
    name: kvName
    location: location
    tags: tags
    mongodbUrl: mongodbUrl
    redisUrl: redisUrl
    secretKey: secretKey
  }
}

module storage 'modules/storage-account.bicep' = {
  name: 'storage'
  params: {
    name: storageName
    location: location
    tags: tags
    containerName: blobContainerName
  }
}

module cae 'modules/container-apps-env.bicep' = {
  name: 'containerAppsEnv'
  params: {
    name: caeName
    location: location
    logAnalyticsCustomerId: logAnalytics.outputs.customerId
    logAnalyticsSharedKey: logAnalytics.outputs.primarySharedKey
    tags: tags
  }
}

var sharedSecrets = [
  { name: 'mongodb-url', value: mongodbUrl }
  { name: 'redis-url', value: redisUrl }
  { name: 'secret-key', value: secretKey }
  // Connection string is the live auth path: the GitHub OIDC principal cannot
  // assign Storage Blob Data Contributor, so managed identity alone is not enough.
  { name: 'azure-storage-connection-string', value: storage.outputs.connectionString }
]

module web 'modules/container-app-web.bicep' = {
  name: 'web'
  params: {
    name: webName
    location: location
    environmentId: cae.outputs.id
    containerImage: containerImage
    tags: tags
  }
}

// Public hostname is the App Service azurewebsites.net URL. ACA web stays as a fallback origin.
var azureWebOrigins = '${publicWebOrigin},https://${web.outputs.fqdn}'
var corsOriginsEffective = empty(corsOrigins)
  ? azureWebOrigins
  : '${corsOrigins},${azureWebOrigins}'

var sharedEnv = [
  { name: 'APP_ENV', value: 'production' }
  { name: 'DEBUG', value: 'false' }
  { name: 'KAFKA_ENABLED', value: 'false' }
  { name: 'AZURE_JOBS_ENABLED', value: 'true' }
  { name: 'AZURE_SUBSCRIPTION_ID', value: subscription().subscriptionId }
  { name: 'AZURE_RESOURCE_GROUP', value: resourceGroup().name }
  { name: 'AZURE_JOB_FETCH', value: fetchJobName }
  { name: 'AZURE_JOB_MATCH', value: matchJobName }
  { name: 'AZURE_JOB_APPLY', value: applyJobName }
  { name: 'CORS_ORIGINS', value: corsOriginsEffective }
  { name: 'PLAYWRIGHT_HEADLESS', value: 'true' }
  { name: 'PLAYWRIGHT_NO_SANDBOX', value: 'true' }
  { name: 'WEB_CONCURRENCY', value: '1' }
  { name: 'GUNICORN_TIMEOUT', value: '120' }
  { name: 'MONGODB_DB', value: 'jobpilot' }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.outputs.connectionString }
  { name: 'MONGODB_URL', secretRef: 'mongodb-url' }
  { name: 'REDIS_URL', secretRef: 'redis-url' }
  { name: 'SECRET_KEY', secretRef: 'secret-key' }
  { name: 'AZURE_STORAGE_ACCOUNT', value: storage.outputs.name }
  { name: 'AZURE_STORAGE_CONTAINER', value: storage.outputs.containerName }
  { name: 'AZURE_STORAGE_CONNECTION_STRING', secretRef: 'azure-storage-connection-string' }
]

module api 'modules/container-app-api.bicep' = {
  name: 'api'
  params: {
    name: apiName
    location: location
    environmentId: cae.outputs.id
    containerImage: containerImage
    env: sharedEnv
    secrets: sharedSecrets
    tags: tags
  }
}

module fetchJob 'modules/container-app-job.bicep' = {
  name: 'fetchJob'
  params: {
    name: fetchJobName
    location: location
    environmentId: cae.outputs.id
    containerImage: containerImage
    jobType: 'fetch'
    cpu: '1.0'
    memory: '2Gi'
    replicaTimeout: 1800
    env: sharedEnv
    secrets: sharedSecrets
    tags: tags
  }
}

module matchJob 'modules/container-app-job.bicep' = {
  name: 'matchJob'
  params: {
    name: matchJobName
    location: location
    environmentId: cae.outputs.id
    containerImage: containerImage
    jobType: 'match'
    cpu: '0.5'
    memory: '1Gi'
    replicaTimeout: 900
    env: sharedEnv
    secrets: sharedSecrets
    tags: tags
  }
}

module applyJob 'modules/container-app-job.bicep' = {
  name: 'applyJob'
  params: {
    name: applyJobName
    location: location
    environmentId: cae.outputs.id
    containerImage: containerImage
    jobType: 'apply'
    cpu: '1.0'
    memory: '2Gi'
    replicaTimeout: 1800
    env: sharedEnv
    secrets: sharedSecrets
    tags: tags
  }
}

module acrPullApi 'modules/acr-pull-role.bicep' = {
  name: 'acrPullApi'
  params: {
    acrName: acr.outputs.name
    principalId: api.outputs.principalId
  }
}

module acrPullWeb 'modules/acr-pull-role.bicep' = {
  name: 'acrPullWeb'
  params: {
    acrName: acr.outputs.name
    principalId: web.outputs.principalId
  }
}

module acrPullFetch 'modules/acr-pull-role.bicep' = {
  name: 'acrPullFetch'
  params: {
    acrName: acr.outputs.name
    principalId: fetchJob.outputs.principalId
  }
}

module acrPullMatch 'modules/acr-pull-role.bicep' = {
  name: 'acrPullMatch'
  params: {
    acrName: acr.outputs.name
    principalId: matchJob.outputs.principalId
  }
}

module acrPullApply 'modules/acr-pull-role.bicep' = {
  name: 'acrPullApply'
  params: {
    acrName: acr.outputs.name
    principalId: applyJob.outputs.principalId
  }
}

module kvAccessApi 'modules/key-vault-access.bicep' = {
  name: 'kvAccessApi'
  params: {
    keyVaultName: keyVault.outputs.name
    principalId: api.outputs.principalId
  }
}

module blobApi 'modules/blob-data-role.bicep' = {
  name: 'blobApi'
  params: {
    storageAccountName: storage.outputs.name
    principalId: api.outputs.principalId
  }
}

module blobFetch 'modules/blob-data-role.bicep' = {
  name: 'blobFetch'
  params: {
    storageAccountName: storage.outputs.name
    principalId: fetchJob.outputs.principalId
  }
}

module blobMatch 'modules/blob-data-role.bicep' = {
  name: 'blobMatch'
  params: {
    storageAccountName: storage.outputs.name
    principalId: matchJob.outputs.principalId
  }
}

module blobApply 'modules/blob-data-role.bicep' = {
  name: 'blobApply'
  params: {
    storageAccountName: storage.outputs.name
    principalId: applyJob.outputs.principalId
  }
}

module startFetch 'modules/job-starter-role.bicep' = {
  name: 'startFetch'
  params: {
    jobName: fetchJob.outputs.name
    principalId: api.outputs.principalId
  }
}

module startMatch 'modules/job-starter-role.bicep' = {
  name: 'startMatch'
  params: {
    jobName: matchJob.outputs.name
    principalId: api.outputs.principalId
  }
}

module startApply 'modules/job-starter-role.bicep' = {
  name: 'startApply'
  params: {
    jobName: applyJob.outputs.name
    principalId: api.outputs.principalId
  }
}

output acrName string = acr.outputs.name
output acrLoginServer string = acr.outputs.loginServer
output apiName string = api.outputs.name
output apiUri string = api.outputs.uri
output webName string = web.outputs.name
output webUri string = web.outputs.uri
output publicWebUri string = publicWebOrigin
output fetchJobName string = fetchJob.outputs.name
output matchJobName string = matchJob.outputs.name
output applyJobName string = applyJob.outputs.name
output appInsightsConnectionString string = appInsights.outputs.connectionString
output storageAccountName string = storage.outputs.name
output storageContainerName string = storage.outputs.containerName
