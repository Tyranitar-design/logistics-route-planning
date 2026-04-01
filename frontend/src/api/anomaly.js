/**
 * 实时异常检测 API
 */

import request from './request'

// 运行全量检测
export const runFullDetection = (params = {}) => {
  return request.post('/anomaly/detect', params)
}

// 检测订单异常
export const detectOrderAnomalies = (orderIds = null) => {
  return request.post('/anomaly/detect/orders', { order_ids: orderIds })
}

// 检测车辆异常
export const detectVehicleAnomalies = (vehicleIds = null) => {
  return request.post('/anomaly/detect/vehicles', { vehicle_ids: vehicleIds })
}

// 检测天气影响
export const detectWeatherImpact = (weatherData = null) => {
  return request.post('/anomaly/detect/weather', { weather_data: weatherData })
}

// 检测路线偏离
export const detectRouteDeviation = (vehiclePositions) => {
  return request.post('/anomaly/detect/route', { vehicle_positions: vehiclePositions })
}

// 获取检测历史
export const getDetectionHistory = (limit = 10) => {
  return request.get(`/anomaly/history?limit=${limit}`)
}

// 获取异常趋势
export const getAnomalyTrends = (hours = 24) => {
  return request.get(`/anomaly/trends?hours=${hours}`)
}

// 获取仪表盘数据
export const getAnomalyDashboard = () => {
  return request.get('/anomaly/dashboard')
}

export default {
  runFullDetection,
  detectOrderAnomalies,
  detectVehicleAnomalies,
  detectWeatherImpact,
  detectRouteDeviation,
  getDetectionHistory,
  getAnomalyTrends,
  getAnomalyDashboard
}