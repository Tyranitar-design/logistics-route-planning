/**
 * 库存优化 API
 */

import request from './request'

// 综合库存优化
export const optimizeInventory = (params) => {
  return request.post('/inventory/optimize', params)
}

// 计算 EOQ
export const calculateEOQ = (params) => {
  return request.post('/inventory/eoq', params)
}

// 计算安全库存
export const calculateSafetyStock = (params) => {
  return request.post('/inventory/safety-stock', params)
}

// 库存周转分析
export const analyzeTurnover = (items) => {
  return request.post('/inventory/turnover-analysis', { items })
}

// 获取库存预警
export const getInventoryAlerts = (items) => {
  return request.post('/inventory/alerts', { items })
}

// 设置 VMI
export const setupVMI = (params) => {
  return request.post('/inventory/vmi/setup', params)
}

// 计算 VMI 补货
export const calculateVMIReplenishment = (params) => {
  return request.post('/inventory/vmi/replenishment', params)
}

export default {
  optimizeInventory,
  calculateEOQ,
  calculateSafetyStock,
  analyzeTurnover,
  getInventoryAlerts,
  setupVMI,
  calculateVMIReplenishment
}