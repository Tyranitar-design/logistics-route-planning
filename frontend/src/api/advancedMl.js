/**
 * 高级预测 API
 */

import request from './request'

const interactiveParams = (params = {}) => ({
  runtime_profile: 'interactive',
  limit: 5000,
  time_granularity: 'auto',
  ...params
})

// 训练模型
export const trainAdvancedModels = (days = 180, options = {}) => {
  return request.post('/advanced-ml/train', {
    days,
    runtime_profile: 'full',
    limit: 10000,
    model_family: 'lstm',
    ...options
  }, { timeout: 90000 })
}

// LSTM 预测
export const getLSTMPrediction = (days = 7, params = {}) => {
  return request.get('/advanced-ml/predict/lstm', { params: interactiveParams({ days, ...params }) })
}

// Prophet 预测
export const getProphetPrediction = (days = 7, params = {}) => {
  return request.get('/advanced-ml/predict/prophet', { params: interactiveParams({ days, ...params }) })
}

// 融合预测
export const getEnsemblePrediction = (days = 7, params = {}) => {
  return request.get('/advanced-ml/predict/ensemble', { params: interactiveParams({ days, ...params }) })
}

// 预测 + 异常预警
export const getPredictionWithAnomaly = (days = 7, params = {}) => {
  return request.get('/advanced-ml/predict/with-anomaly', {
    params: interactiveParams({ days, anomaly_limit: 8, ...params })
  })
}

// 异常检测
export const detectAnomalies = (data, options = {}) => {
  return request.post('/advanced-ml/anomaly/detect', {
    data,
    runtime_profile: 'interactive',
    limit: 5000,
    use_ml: false,
    ...options
  })
}

// 按区域预测
export const predictByRegion = (days = 7, region = null, params = {}) => {
  return request.get('/advanced-ml/predict/by-region', {
    params: interactiveParams({ days, region, ...params })
  })
}

// 获取模型状态
export const getAdvancedMLStatus = () => {
  return request.get('/advanced-ml/status')
}

export default {
  trainAdvancedModels,
  getLSTMPrediction,
  getProphetPrediction,
  getEnsemblePrediction,
  getPredictionWithAnomaly,
  detectAnomalies,
  predictByRegion,
  getAdvancedMLStatus
}
