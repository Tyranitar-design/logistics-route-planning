/**
 * 高德地图 API 接口
 */
import request from './request'

/**
 * 地理编码 - 地址转坐标
 */
export function geocode(address, city = null) {
  return request.get('/amap/geocode', { params: { address, city } })
}

/**
 * 逆地理编码 - 坐标转地址
 */
export function regeocode(longitude, latitude) {
  return request.get('/amap/regeocode', { params: { longitude, latitude } })
}

/**
 * 驾车路线规划
 * @param {Object} data - 请求参数
 * @param {number|Object} data.origin - 起点（节点ID或坐标）
 * @param {number|Object} data.destination - 终点
 * @param {Array} data.waypoints - 途经点
 * @param {number} data.strategy - 路线策略（0-10）
 * @param {boolean} data.show_traffic - 是否返回路况
 */
export function drivingRoute(data) {
  return request.post('/amap/route/driving', data)
}

/**
 * 多路线规划
 */
export function multiRoute(origin, destination) {
  return request.post('/amap/route/multi', { origin, destination })
}

/**
 * 获取周边路况
 */
export function trafficAround(longitude, latitude, radius = 1000) {
  return request.get('/amap/traffic/around', { 
    params: { longitude, latitude, radius } 
  })
}

/**
 * 获取节点周边路况
 */
export function trafficAtNode(nodeId) {
  return request.get(`/amap/traffic/node/${nodeId}`)
}

/**
 * 批量距离计算
 */
export function distanceMatrix(origins, destinations, strategy = 0) {
  return request.post('/amap/distance-matrix', { origins, destinations, strategy })
}

/**
 * 对比本地算法和高德地图的路线规划
 */
export function compareRoutes(originId, destinationId) {
  return request.post('/amap/route/compare', { 
    origin_id: originId, 
    destination_id: destinationId 
  })
}
