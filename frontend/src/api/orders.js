import request from './request'

// 获取订单列表
export function getOrders(params) {
  return request.get('/orders', { params })
}

// 获取单个订单
export function getOrder(id) {
  return request.get(`/orders/${id}`)
}

// 创建订单
export function createOrder(data) {
  return request.post('/orders', data)
}

// 更新订单
export function updateOrder(id, data) {
  return request.put(`/orders/${id}`, data)
}

// 删除订单
export function deleteOrder(id) {
  return request.delete(`/orders/${id}`)
}

// 更新订单状态
export function updateOrderStatus(id, status) {
  return request.put(`/orders/${id}/status`, { status })
}

// 分配车辆
export function assignVehicle(id, vehicleId) {
  return request.post(`/orders/${id}/assign`, { vehicle_id: vehicleId })
}

// 获取订单统计
export function getStatistics() {
  return request.get('/orders/statistics')
}

// 为订单推荐路线
export function recommendOrderRoute(orderId, preferSource = 'auto') {
  return request.get(`/orders/${orderId}/recommend-route`, {
    params: { prefer_source: preferSource }
  })
}

// 根据起点终点推荐路线（创建订单前预览）
export function recommendRouteForNodes(originId, destinationId, weight = 0, preferSource = 'auto') {
  return request.post('/orders/recommend-route', {
    origin_id: originId,
    destination_id: destinationId,
    weight,
    prefer_source: preferSource
  })
}

// 应用推荐路线到订单
export function applyRouteToOrder(orderId, routeData) {
  return request.post(`/orders/${orderId}/apply-route`, { route_data: routeData })
}

// 获取订单可用车辆
export function getAvailableVehiclesForOrder(orderId, weight = 0, volume = 0) {
  return request.get(`/orders/${orderId}/available-vehicles`, {
    params: { weight, volume }
  })
}
