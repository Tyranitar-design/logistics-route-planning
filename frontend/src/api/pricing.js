/**
 * 动态定价 API
 */

import request from './request'

// 计算价格
export const calculatePrice = (params) => {
  return request.post('/pricing/calculate', params)
}

// 获取价格预测
export const getPriceForecast = (distance, region = null, hours = 24) => {
  let url = `/pricing/forecast?distance=${distance}&hours=${hours}`
  if (region) url += `&region=${region}`
  return request.get(url)
}

// 批量定价
export const batchPricing = (orders) => {
  return request.post('/pricing/batch', { orders })
}

// 获取定价统计
export const getPricingStatistics = () => {
  return request.get('/pricing/statistics')
}

// 获取时段定价信息
export const getTimeSlotPricing = () => {
  return request.get('/pricing/time-slots')
}

export default {
  calculatePrice,
  getPriceForecast,
  batchPricing,
  getPricingStatistics,
  getTimeSlotPricing
}