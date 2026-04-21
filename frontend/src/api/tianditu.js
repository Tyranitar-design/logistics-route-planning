/**
 * 天地图 API 接口
 * 官方文档：https://lbs.tianditu.gov.cn/server/guide.html
 */
import request from './request'

/**
 * 驾车路线规划
 * @param {Object} data - 请求参数
 * @param {number} [data.origin_id] - 起点节点ID
 * @param {Array} [data.origin] - 起点坐标 [lng, lat]
 * @param {number} [data.destination_id] - 终点节点ID
 * @param {Array} [data.destination] - 终点坐标 [lng, lat]
 * @param {string} [data.strategy] - 路线策略
 *   '0' - 推荐路线（默认）
 *   '1' - 最短距离
 *   '2' - 最短时间
 *   '3' - 避开高速
 * @returns {Promise<Object>} 路线规划结果
 */
export function drivingRoute(data) {
  return request.post('/tianditu/drive', data)
}

/**
 * 通过坐标进行路径规划（简化接口）
 * @param {number} originLng - 起点经度
 * @param {number} originLat - 起点纬度
 * @param {number} destLng - 终点经度
 * @param {number} destLat - 终点纬度
 * @param {string} [strategy='0'] - 路线策略
 */
export function drivingRouteByCoords(originLng, originLat, destLng, destLat, strategy = '0') {
  return request.post('/tianditu/drive/coords', {
    origin_lng: originLng,
    origin_lat: originLat,
    dest_lng: destLng,
    dest_lat: destLat,
    strategy
  })
}

/**
 * 地名搜索
 * @param {string} keywords - 搜索关键词
 * @param {number} [level=12] - 地图级别（1-18）
 */
export function searchPOI(keywords, level = 12) {
  return request.get('/tianditu/search', {
    params: { keywords, level }
  })
}

/**
 * 地理编码 - 地址转坐标
 * @param {string} address - 地址字符串
 * @param {string} [city] - 城市名称（可选）
 */
export function geocode(address, city = null) {
  return request.get('/tianditu/geocode', {
    params: { address, city }
  })
}

/**
 * 批量距离计算
 * @param {Array<Array<number>>} origins - 起点列表 [[lng, lat], ...]
 * @param {Array<Array<number>>} destinations - 终点列表 [[lng, lat], ...]
 * @param {string} [strategy='0'] - 路线策略
 */
export function distanceMatrix(origins, destinations, strategy = '0') {
  return request.post('/tianditu/distance-matrix', {
    origins,
    destinations,
    strategy
  })
}

/**
 * 天地图与高德地图路径对比
 * @param {number} originId - 起点节点ID
 * @param {number} destinationId - 终点节点ID
 * @param {string} [strategy='0'] - 路线策略
 * @returns {Promise<Object>} 对比结果，包含天地图和高德的路径数据
 */
export function compareWithAmap(originId, destinationId, strategy = '0') {
  return request.post('/tianditu/compare/amap', {
    origin_id: originId,
    destination_id: destinationId,
    strategy
  })
}

/**
 * 获取天地图 Key 配置状态
 * @returns {Promise<Object>} { browser_key_configured: boolean, server_key_configured: boolean }
 */
export function getKeysInfo() {
  return request.get('/tianditu/keys')
}

/**
 * 获取浏览器端 Key（用于前端直接调用天地图 JS API）
 * 注意：这只是获取 Key 的状态，实际 Key 不暴露给前端
 */
export function getBrowserKeyStatus() {
  return request.get('/tianditu/keys')
}
