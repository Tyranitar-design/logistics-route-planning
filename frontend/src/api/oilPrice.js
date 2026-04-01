/**
 * 油价查询 API
 */
import request from '@/api/request'

/**
 * 获取当前油价
 * @param {string} province - 省份名称
 */
export function getCurrentPrices(province = '北京') {
  return request({
    url: '/oil-price/current',
    method: 'get',
    params: { province }
  })
}

/**
 * 获取油价历史趋势
 * @param {string} province - 省份名称
 * @param {number} days - 天数
 */
export function getPriceHistory(province = '北京', days = 30) {
  return request({
    url: '/oil-price/history',
    method: 'get',
    params: { province, days }
  })
}

/**
 * 计算燃油成本
 * @param {object} data - 计算参数
 */
export function calculateFuelCost(data) {
  return request({
    url: '/oil-price/calculate',
    method: 'post',
    data
  })
}

/**
 * 获取支持的省份列表
 */
export function getProvinces() {
  return request({
    url: '/oil-price/provinces',
    method: 'get'
  })
}

/**
 * 获职油品类型列表
 */
export function getFuelTypes() {
  return request({
    url: '/oil-price/fuel-types',
    method: 'get'
  })
}

/**
 * 获取油价概览（用于仪表盘）
 */
export function getOilOverview() {
  return request({
    url: '/oil-price/overview',
    method: 'get'
  })
}

/**
 * 刷新油价缓存
 */
export function refreshCache() {
  return request({
    url: '/oil-price/refresh-cache',
    method: 'post'
  })
}
