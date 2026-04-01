/**
 * 供应链风险管理 API
 */
import request from './request'

// ==================== 仪表盘 ====================

/**
 * 获取风险管理仪表盘数据
 */
export function getRiskDashboard() {
  return request({
    url: '/risk/dashboard',
    method: 'get'
  })
}

// ==================== 卡拉杰克矩阵 ====================

/**
 * 卡拉杰克矩阵物资分类
 */
export function classifyItem(data) {
  return request({
    url: '/risk/kraljic/classify',
    method: 'post',
    data
  })
}

/**
 * 获取订单分类结果
 */
export function getClassifiedOrders() {
  return request({
    url: '/risk/kraljic/orders',
    method: 'get'
  })
}

/**
 * 获取分类说明
 */
export function getKraljicCategories() {
  return request({
    url: '/risk/kraljic/categories',
    method: 'get'
  })
}

// ==================== 风险评估矩阵 ====================

/**
 * 评估路线风险
 */
export function assessRoute(routeId, params = {}) {
  return request({
    url: `/risk/assessment/route/${routeId}`,
    method: 'get',
    params
  })
}

/**
 * 获取风险矩阵数据
 */
export function getRiskMatrix() {
  return request({
    url: '/risk/assessment/matrix',
    method: 'get'
  })
}

/**
 * 获取风险等级说明
 */
export function getRiskLevels() {
  return request({
    url: '/risk/assessment/levels',
    method: 'get'
  })
}

// ==================== CBA决策模型 ====================

/**
 * 计算CBA决策
 */
export function calculateCBA(data) {
  return request({
    url: '/risk/cba/calculate',
    method: 'post',
    data
  })
}

/**
 * 批量CBA分析
 */
export function batchCBA(scenarios) {
  return request({
    url: '/risk/cba/batch',
    method: 'post',
    data: { scenarios }
  })
}

// ==================== AWRP成本估算 ====================

/**
 * 估算AWRP成本
 */
export function estimateAWRP(data) {
  return request({
    url: '/risk/awrp/estimate',
    method: 'post',
    data
  })
}

/**
 * 对比路线AWRP成本
 */
export function compareAWRPRoutes(data) {
  return request({
    url: '/risk/awrp/compare',
    method: 'post',
    data
  })
}

/**
 * 获取危机区域列表
 */
export function getCrisisZones() {
  return request({
    url: '/risk/awrp/zones',
    method: 'get'
  })
}

/**
 * 获取AWRP费率表
 */
export function getAWRPRates() {
  return request({
    url: '/risk/awrp/rates',
    method: 'get'
  })
}