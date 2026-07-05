/**
 * 实时异常检测 API 兼容层。
 *
 * 旧 /anomaly/* 偏演示链路仍可能存在；Vue 新主线统一使用 /ai-anomaly/*
 * 读取真实 shipment_facts 异常信号。
 */

import request from './request'

// 运行全量检测
export const runFullDetection = (params = {}) => {
  return request.post('/ai-anomaly/detect', {
    tasks: ['status', 'geo', 'cost', 'eta', 'delay', 'od_volume', 'node_congestion', 'ml'],
    limit: 50000,
    anomaly_limit: 100,
    use_ml: true,
    ...params
  })
}

// 检测订单异常
export const detectOrderAnomalies = (orderIds = null) => {
  return request.post('/ai-anomaly/detect', {
    tasks: ['status', 'eta', 'delay'],
    order_ids: orderIds,
    limit: 50000,
    anomaly_limit: 100,
    use_ml: false
  })
}

// 检测车辆异常
export const detectVehicleAnomalies = (vehicleIds = null) => {
  return request.post('/ai-anomaly/detect', {
    tasks: ['node_congestion', 'delay'],
    vehicle_ids: vehicleIds,
    limit: 50000,
    anomaly_limit: 100,
    use_ml: false
  })
}

// 检测天气影响
export const detectWeatherImpact = (weatherData = null) => {
  return request.post('/ai-anomaly/detect', {
    tasks: ['delay', 'od_volume'],
    weather_data: weatherData,
    limit: 50000,
    anomaly_limit: 100,
    use_ml: false
  })
}

// 检测路线偏离
export const detectRouteDeviation = (vehiclePositions) => {
  return request.post('/ai-anomaly/detect', {
    tasks: ['geo'],
    vehicle_positions: vehiclePositions,
    limit: 50000,
    anomaly_limit: 100,
    use_ml: false
  })
}

// 获取检测历史
export const getDetectionHistory = (limit = 10) => {
  return request.post('/ai-anomaly/detect', {
    limit: 50000,
    anomaly_limit: limit,
    use_ml: true
  })
}

// 获取异常趋势
export const getAnomalyTrends = (hours = 24) => {
  return request.post('/ai-anomaly/scorecard', {
    limit: 50000,
    anomaly_limit: 100,
    trend_hours: hours,
    use_ml: true
  })
}

// 获取仪表盘数据
export const getAnomalyDashboard = () => {
  return request.post('/ai-anomaly/scorecard', {
    limit: 50000,
    anomaly_limit: 100,
    use_ml: true
  })
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
