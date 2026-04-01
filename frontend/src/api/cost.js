/**
 * 成本分析 API
 */
import request from './request'

// 获取成本总览
export function getCostOverview() {
  return request.get('/cost/overview')
}

// 获取成本趋势
export function getCostTrend(days = 30) {
  return request.get('/cost/trend', { params: { days } })
}

// 获取成本分布
export function getCostDistribution() {
  return request.get('/cost/distribution')
}

// 获取节点成本
export function getCostByNode() {
  return request.get('/cost/by-node')
}

// 获取车辆成本
export function getCostByVehicle() {
  return request.get('/cost/by-vehicle')
}

// 获取成本构成
export function getCostComponents() {
  return request.get('/cost/cost-components')
}

// 获取路线对比
export function getRouteComparison() {
  return request.get('/cost/comparison')
}

// 获取优化建议
export function getOptimizationSuggestions() {
  return request.get('/cost/optimization-suggestions')
}
