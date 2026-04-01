/**
 * 智能预警中心 API
 */
import request from './request'

/**
 * 获取预警仪表盘数据
 */
export function getAlertDashboard() {
  return request({
    url: '/alert/dashboard',
    method: 'get'
  })
}

/**
 * 获取预警列表
 * @param {Object} params - 查询参数
 */
export function getAlerts(params = {}) {
  return request({
    url: '/alert/alerts',
    method: 'get',
    params
  })
}

/**
 * 获取预警统计
 */
export function getAlertStatistics() {
  return request({
    url: '/alert/statistics',
    method: 'get'
  })
}

/**
 * 标记预警为已读
 * @param {string} alertId - 预警ID
 */
export function markAlertRead(alertId) {
  return request({
    url: `/alert/alerts/${alertId}/read`,
    method: 'post'
  })
}

/**
 * 标记预警为已解决
 * @param {string} alertId - 预警ID
 */
export function markAlertResolved(alertId) {
  return request({
    url: `/alert/alerts/${alertId}/resolve`,
    method: 'post'
  })
}

/**
 * 获取预警规则
 */
export function getAlertRules() {
  return request({
    url: '/alert/rules',
    method: 'get'
  })
}