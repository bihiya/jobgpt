param name string
param location string
param tags object
@secure()
param mongodbUrl string
@secure()
param redisUrl string
@secure()
param secretKey string

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

resource secretMongo 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'mongodb-url'
  properties: { value: mongodbUrl }
}

resource secretRedis 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'redis-url'
  properties: { value: redisUrl }
}

resource secretApp 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'secret-key'
  properties: { value: secretKey }
}

output name string = kv.name
output id string = kv.id
output uri string = kv.properties.vaultUri
