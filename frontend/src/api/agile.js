/**
 * 敏捷路径优化 API
 */
import request from './request'

/**
 * 敏捷路径优化
 * @param {Object} params - 参数
 * @param {Array} params.order_ids - 订单ID列表
 * @param {Array} params.vehicle_ids - 车辆ID列表
 * @param {string} params.algorithm - 算法选择
 * @param {Object} params.constraints - 约束条件
 * @param {Object} params.weights - 优化权重
 */
export function optimizeRoutes(params = {}) {
  return request({
    url: '/agile/optimize',
    method: 'post',
    data: params
  })
}

/**
 * 获取智能拼单建议
 * @param {Object} params - 参数
 * @param {string} params.order_ids - 订单ID列表（逗号分隔）
 * @param {number} params.max_distance - 最大合并距离
 */
export function getMergeSuggestions(params = {}) {
  return request({
    url: '/agile/merge-suggestions',
    method: 'get',
    params
  })
}

/**
 * 获取实时优化建议
 * @param {number} vehicleId - 车辆ID
 * @param {Object} location - 位置
 * @param {number} location.lat - 纬度
 * @param {number} location.lng - 经度
 */
export function getRealtimeSuggestions(vehicleId, location = {}) {
  return request({
    url: `/agile/realtime/${vehicleId}`,
    method: 'get',
    params: location
  })
}

/**
 * 获取可用算法列表
 */
export function getAlgorithms() {
  return request({
    url: '/agile/algorithms',
    method: 'get'
  })
}

/**
 * 成本估算
 * @param {Object} params - 参数
 * @param {number} params.distance - 距离（公里）
 * @param {number} params.duration - 时长（分钟）
 * @param {string} params.vehicle_type - 车辆类型
 * @param {number} params.load_weight - 载重（吨）
 */
export function estimateCost(params = {}) {
  return request({
    url: '/agile/cost-estimate',
    method: 'post',
    data: params
  })
}

/**
 * 应用优化结果
 * @param {Array} routes - 路线列表
 */
export function applyOptimization(routes) {
  return request({
    url: '/agile/apply',
    method: 'post',
    data: { routes }
  })
}

/**
 * 对比不同算法效果
 * @param {Object} params - 参数
 * @param {Array} params.order_ids - 订单ID列表
 * @param {Array} params.vehicle_ids - 车辆ID列表
 * @param {Array} params.algorithms - 要对比的算法列表
 */
export function compareAlgorithms(params = {}) {
  return request({
    url: '/agile/compare',
    method: 'post',
    data: params
  })
}