import request from './request'

export function getGisProviderHealth() {
  return request({
    url: '/gis/provider-health',
    method: 'get'
  })
}
