import request from './request'

export function chatWithAgent(data = {}) {
  return request({
    url: '/agent/chat',
    method: 'post',
    data,
    timeout: 60000
  })
}

export function previewAgentTool(data = {}) {
  return request({
    url: '/agent/tools/preview',
    method: 'post',
    data
  })
}

export function confirmAgentAction(data = {}) {
  return request({
    url: '/agent/actions/confirm',
    method: 'post',
    data
  })
}
