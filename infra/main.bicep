targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the azd environment that is being deployed')
param environmentName string

@minLength(1)
@description('Primary Azure region for all resources')
param location string

@description('MongoDB connection string (Atlas SRV recommended)')
@secure()
param mongodbUrl string

@description('Redis connection string (Upstash recommended)')
@secure()
param redisUrl string

@description('App secret key for JWT signing')
@secure()
param secretKey string

@description('Comma-separated CORS origins (Vercel frontend URL)')
param corsOrigins string = 'http://localhost:3000'

@description('Tags applied to all resources')
param tags object = {}

var resourceSuffix = take(uniqueString(subscription().id, environmentName, location), 6)
var resourceGroupName = 'rg-jobpilot-${environmentName}'
var baseTags = union({ 'azd-env-name': environmentName, project: 'jobpilot' }, tags)

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: baseTags
}

module resources 'resources.bicep' = {
  name: 'jobpilot-resources'
  scope: rg
  params: {
    location: location
    environmentName: environmentName
    resourceSuffix: resourceSuffix
    mongodbUrl: mongodbUrl
    redisUrl: redisUrl
    secretKey: secretKey
    corsOrigins: corsOrigins
    tags: baseTags
  }
}

output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.acrLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = resources.outputs.acrName
output SERVICE_API_NAME string = resources.outputs.apiName
output SERVICE_API_URI string = resources.outputs.apiUri
output AZURE_JOB_FETCH_NAME string = resources.outputs.fetchJobName
output AZURE_JOB_MATCH_NAME string = resources.outputs.matchJobName
output AZURE_JOB_APPLY_NAME string = resources.outputs.applyJobName
output AZURE_SUBSCRIPTION_ID string = subscription().subscriptionId
output APPLICATIONINSIGHTS_CONNECTION_STRING string = resources.outputs.appInsightsConnectionString
