import request from './request'

export function getRuntimeCapabilities(params = {}) {
  return request({
    url: '/runtime/capabilities',
    method: 'get',
    params: {
      solver_probe: true,
      ...params
    }
  })
}
