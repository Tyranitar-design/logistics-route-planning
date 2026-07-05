/**
 * 机器学习预测 API 兼容层。
 *
 * 旧 /ml/* 蓝图在当前本地启动方式中可能被 DISABLE_ML_ROUTES 关闭；
 * 这里保留旧函数名，但统一转发到真实 shipment_facts 驱动的 /ai-prediction/*。
 */

import request from './request'

/**
 * 训练预测模型
 */
export function trainModel(days = 90) {
  return request.post('/ai-prediction/model/train', {
    task: 'eta',
    limit: 50000,
    test_ratio: 0.25,
    training_window_days: days
  })
}

/**
 * 获取需求预测
 */
export function getPredictions(days = 7, region = null) {
  const params = { days }
  if (region) params.city = region
  return request.get('/ai-prediction/demand/forecast', { params })
}

/**
 * 获取聚合预测结果
 */
export function getAggregatedPrediction(days = 7) {
  return request.get('/ai-prediction/demand/forecast', { params: { days, limit: 50000 } })
}

/**
 * 获取合并配送建议
 */
export function getMergeSuggestions(threshold = 10) {
  return request.post('/ai-prediction/scorecard', {
    horizon_days: 14,
    test_days: 14,
    sequence_length: 14,
    limit: 50000,
    suggestion_threshold: threshold
  })
}

/**
 * 获取车辆调配建议
 */
export function getVehicleAllocation(days = 7) {
  return request.post('/ai-prediction/capacity-gap/forecast', {
    horizon_days: days,
    test_days: days,
    sequence_length: 14,
    limit: 50000
  })
}

/**
 * 智能调度优化
 */
export function optimizeDispatch(orders, vehicles) {
  return request.post('/dispatch/preview', {
    orders,
    vehicles,
    data_source: 'auto',
    solver: 'auto',
    persist: false
  })
}

/**
 * 获取模型状态
 */
export function getModelStatus() {
  return request.get('/ai-prediction/model/status')
}
