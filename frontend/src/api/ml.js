/**
 * 机器学习预测 API
 */

import request from './request'

/**
 * 训练预测模型
 */
export function trainModel(days = 90) {
  return request.post('/ml/train', { days })
}

/**
 * 获取需求预测
 */
export function getPredictions(days = 7, region = null) {
  const params = { days }
  if (region) params.region = region
  return request.get('/ml/predict', { params })
}

/**
 * 获取聚合预测结果
 */
export function getAggregatedPrediction(days = 7) {
  return request.get('/ml/predict/aggregated', { params: { days } })
}

/**
 * 获取合并配送建议
 */
export function getMergeSuggestions(threshold = 10) {
  return request.get('/ml/merge-suggestions', { params: { threshold } })
}

/**
 * 获取车辆调配建议
 */
export function getVehicleAllocation(days = 7) {
  return request.get('/ml/vehicle-allocation', { params: { days } })
}

/**
 * 智能调度优化
 */
export function optimizeDispatch(orders, vehicles) {
  return request.post('/ml/optimize-dispatch', { orders, vehicles })
}

/**
 * 获取模型状态
 */
export function getModelStatus() {
  return request.get('/ml/model/status')
}