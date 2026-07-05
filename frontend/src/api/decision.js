import request from './request'

export function createDecisionScenario(data = {}) {
  return request({
    url: '/decision/scenarios',
    method: 'post',
    data
  })
}
