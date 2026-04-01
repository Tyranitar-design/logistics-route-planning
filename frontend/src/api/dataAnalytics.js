/**
 * 数据分析 API
 */

import request from './request'

// 获取预测性维护数据
export const getPredictiveMaintenance = () => {
  return request.get('/data-analytics/predictive-maintenance')
}

// 交通预测
export const predictTraffic = (routes) => {
  return request.post('/data-analytics/traffic-prediction', { routes })
}

// 客户画像
export const getCustomerProfiles = () => {
  return request.get('/data-analytics/customer-profiles')
}

// 单个客户详情
export const getCustomerDetail = (customerId) => {
  return request.get(`/data-analytics/customer/${customerId}`)
}

// 供应链可视化
export const getSupplyChain = () => {
  return request.get('/data-analytics/supply-chain')
}

// 追踪订单
export const trackOrder = (orderId) => {
  return request.get(`/data-analytics/supply-chain/track/${orderId}`)
}

// 碳足迹报告
export const getCarbonFootprint = () => {
  return request.get('/data-analytics/carbon-footprint')
}

// 计算碳排放
export const calculateCarbon = (params) => {
  return request.post('/data-analytics/carbon-footprint/calculate', params)
}

// 绿色路线推荐
export const findGreenRoutes = (routes) => {
  return request.post('/data-analytics/green-routes', { routes })
}

// 综合仪表盘
export const getAnalyticsDashboard = () => {
  return request.get('/data-analytics/dashboard')
}

export default {
  getPredictiveMaintenance,
  predictTraffic,
  getCustomerProfiles,
  getCustomerDetail,
  getSupplyChain,
  trackOrder,
  getCarbonFootprint,
  calculateCarbon,
  findGreenRoutes,
  getAnalyticsDashboard
}