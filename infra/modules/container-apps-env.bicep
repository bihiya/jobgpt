param name string
param location string
param logAnalyticsCustomerId string
@secure()
param logAnalyticsSharedKey string
param tags object

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
  }
}

output id string = env.id
output name string = env.name
output defaultDomain string = env.properties.defaultDomain
