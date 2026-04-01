import request from './request'

// 获取路线列表
export function getRoutes(params) {
  return request.get('/routes', { params })
}

// 获取单条路线
export function getRoute(id) {
  return request.get(`/routes/${id}`)
}

// 创建路线
export function createRoute(data) {
  return request.post('/routes', data)
}

// 更新路线
export function updateRoute(id, data) {
  return request.put(`/routes/${id}`, data)
}

// 删除路线
export function deleteRoute(id) {
  return request.delete(`/routes/${id}`)
}

// 路径规划推荐
export function recommendRoute(data) {
  return request.post('/routes/recommend', data)
}

// 获取路径计算
export function calculateRoute(data) {
  return request.post('/routes/calculate', data)
}

// 对比两种方案
export function compareRoutes(originId, destinationId) {
  return request.post('/multi-objective/optimize', {
    origin_id: originId,
    destination_id: destinationId,
    weights: { distance: 0.3, time: 0.3, cost: 0.4 },
    algorithm: 'all'
  })
}
