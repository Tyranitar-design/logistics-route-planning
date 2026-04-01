/**
 * 天气服务 API
 */
import request from './request'

/**
 * 获取实时天气
 * @param {string} city - 城市名称
 */
export function getWeatherNow(city) {
  return request({
    url: '/weather/now',
    method: 'get',
    params: { city }
  })
}

/**
 * 获取天气预报（未来4天）
 * @param {string} city - 城市名称
 */
export function getWeatherForecast(city) {
  return request({
    url: '/weather/forecast',
    method: 'get',
    params: { city }
  })
}

/**
 * 分析天气对运输的影响
 * @param {string} weather - 天气状况
 * @param {string} temperature - 温度（可选）
 */
export function analyzeWeatherImpact(weather, temperature = null) {
  return request({
    url: '/weather/impact',
    method: 'get',
    params: { weather, temperature }
  })
}

/**
 * 获取沿途天气情况
 * @param {string[]} cities - 城市名称列表
 */
export function getRouteWeather(cities) {
  return request({
    url: '/weather/route',
    method: 'get',
    params: { cities: cities.join(',') }
  })
}

/**
 * 获取节点位置的天气
 * @param {number} nodeId - 节点ID
 */
export function getNodeWeather(nodeId) {
  return request({
    url: `/weather/node/${nodeId}`,
    method: 'get'
  })
}
