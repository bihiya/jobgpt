param name string
param planName string
param location string
param acrLoginServer string
param containerImage string
param tags object
param acrUseManagedIdentity bool = true

// Linux containers require Basic (B1) or higher. Always On keeps the
// public hostname warm; ACA web can still scale to zero as a fallback.
resource plan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: planName
  location: location
  kind: 'linux'
  tags: tags
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  properties: {
    reserved: true
  }
}

resource web 'Microsoft.Web/sites@2024-04-01' = {
  name: name
  location: location
  kind: 'app,linux,container'
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    reserved: true
    siteConfig: {
      linuxFxVersion: 'DOCKER|${containerImage}'
      acrUseManagedIdentityCreds: acrUseManagedIdentity
      alwaysOn: true
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      http20Enabled: true
      healthCheckPath: '/'
    }
  }
}

resource appSettings 'Microsoft.Web/sites/config@2024-04-01' = {
  parent: web
  name: 'appsettings'
  properties: {
    WEBSITES_PORT: '80'
    WEBSITES_ENABLE_APP_SERVICE_STORAGE: 'false'
    DOCKER_REGISTRY_SERVER_URL: 'https://${acrLoginServer}'
    DOCKER_ENABLE_CI: 'false'
  }
}

output name string = web.name
output defaultHostName string = web.properties.defaultHostName
output uri string = 'https://${web.properties.defaultHostName}'
output principalId string = web.identity.principalId
