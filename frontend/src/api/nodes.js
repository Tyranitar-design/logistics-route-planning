import request from './request'

// 获取节点列表（分页）
export function getNodes(params) {
  return request.get('/nodes', { params })
}

// 获取所有节点（下拉选择用）
export function getAllNodes() {
  return request.get('/nodes/all')
}

// 获取单个节点
export function getNode(id) {
  return request.get(`/nodes/${id}`)
}

// 创建节点
export function createNode(data) {
  return request.post('/nodes', data)
}

// 更新节点
export function updateNode(id, data) {
  return request.put(`/nodes/${id}`, data)
}

// 删除节点
export function deleteNode(id) {
  return request.delete(`/nodes/${id}`)
}

// 获取路线列表
export function getRoutes(params) {
  return request.get('/routes', { params })
}

// 获取单条路线
export function getRoute(id) {
  return request.get(`/routes/${id}`)
}
