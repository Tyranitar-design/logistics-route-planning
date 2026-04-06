/**
 * 数据采集 API
 * 油价、天气、路况、快递价格
 */
import request from './request'

/**
 * 获取数据源状态
 */
export function getDataSourceStatus() {
  return request({
    url: '/crawler/status',
    method: 'get'
  })
}

/**
 * 获取全国油价数据
 */
export function getOilPrices() {
  return request({
    url: '/crawler/oil',
    method: 'get'
  })
}

/**
 * 获取城市天气数据
 * @param {string} city - 城市名称
 */
export function getCityWeather(city) {
  return request({
    url: `/crawler/weather/${encodeURIComponent(city)}`,
    method: 'get'
  })
}

/**
 * 获取城市路况数据
 * @param {string} city - 城市名称
 */
export function getCityTraffic(city) {
  return request({
    url: `/crawler/traffic/${encodeURIComponent(city)}`,
    method: 'get'
  })
}

/**
 * 对比快递价格
 * @param {string} origin - 寄件城市
 * @param {string} destination - 收件城市
 * @param {number} weight - 重量(kg)
 */
export function compareExpressPrices(origin, destination, weight = 1) {
  return request({
    url: '/crawler/express/compare',
    method: 'post',
    data: { origin, destination, weight }
  })
}

/**
 * 推荐最优快递
 * @param {string} origin - 寄件城市
 * @param {string} destination - 收件城市
 * @param {number} weight - 重量(kg)
 * @param {string} priority - 优先级: price | speed | balanced
 */
export function recommendExpress(origin, destination, weight = 1, priority = 'balanced') {
  return request({
    url: '/crawler/express/recommend',
    method: 'post',
    data: { origin, destination, weight, priority }
  })
}

/**
 * 一键采集所有数据
 * @param {string[]} cities - 城市列表
 */
export function collectAllData(cities = ['北京', '上海', '广州', '深圳']) {
  return request({
    url: '/crawler/all',
    method: 'get',
    params: { cities: cities.join(',') }
  })
}
