import request from './request'

// 获取总览统计
export function getOverview() {
  return request.get('/stats/overview')
}

// 获取订单趋势
export function getOrderTrend() {
  return request.get('/stats/orders/trend')
}

// 获取订单分布
export function getOrderDistribution() {
  return request.get('/stats/orders/distribution')
}

// 获取路线分析
export function getRouteAnalysis() {
  return request.get('/stats/routes/analysis')
}

// 获取车辆利用率
export function getVehicleUtilization() {
  return request.get('/stats/vehicles/utilization')
}
