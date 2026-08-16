targetScope = 'resourceGroup'

@description('Azure region for the public App Service. Use the same region as the Container Apps API.')
param location string = 'centralindia'

@description('Globally unique App Service name. Becomes https://<name>.azurewebsites.net')
param webAppName string = 'jobpilot'

param planName string = 'plan-jobpilot-web'
param acrName string
param containerImage string
param assignAcrPull bool = false
param tags object = {
  project: 'jobpilot'
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

module publicWeb 'modules/app-service-web.bicep' = {
  name: 'publicWeb'
  params: {
    name: webAppName
    planName: planName
    location: location
    acrLoginServer: acr.properties.loginServer
    containerImage: containerImage
    tags: tags
    acrUseManagedIdentity: assignAcrPull
  }
}

module acrPull 'modules/acr-pull-role.bicep' = if (assignAcrPull) {
  name: 'acrPullPublicWeb'
  params: {
    acrName: acr.name
    principalId: publicWeb.outputs.principalId
  }
}

output publicWebName string = publicWeb.outputs.name
output publicWebUri string = publicWeb.outputs.uri
output publicWebHostName string = publicWeb.outputs.defaultHostName
