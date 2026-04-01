/**
 * 高级预测 API
 */

import request from './request'

// 训练模型
export const trainAdvancedModels = (days = 180) => {
  return request.post('/advanced-ml/train', { days })
}

// LSTM 预测
export const getLSTMPrediction = (days = 7) => {
  return request.get(`/advanced-ml/predict/lstm?days=${days}`)
}

// Prophet 预测
export const getProphetPrediction = (days = 7) => {
  return request.get(`/advanced-ml/predict/prophet?days=${days}`)
}

// 融合预测
export const getEnsemblePrediction = (days = 7) => {
  return request.get(`/advanced-ml/predict/ensemble?days=${days}`)
}

// 预测 + 异常预警
export const getPredictionWithAnomaly = (days = 7) => {
  return request.get(`/advanced-ml/predict/with-anomaly?days=${days}`)
}

// 异常检测
export const detectAnomalies = (data) => {
  return request.post('/advanced-ml/anomaly/detect', { data })
}

// 按区域预测
export const predictByRegion = (days = 7, region = null) => {
  const url = region 
    ? `/advanced-ml/predict/by-region?days=${days}&region=${region}`
    : `/advanced-ml/predict/by-region?days=${days}`
  return request.get(url)
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