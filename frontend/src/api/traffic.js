import request from './request'

/**
 * 获取道路实时路况
 * @param {string} city - 城市名称
 * @param {string} roadName - 道路名称（可选）
 */
export function getRoadTraffic(city, roadName) {
  return request.get('/traffic/road', {
    params: { city, road_name: roadName }
  })
}

/**
 * 获取区域路况
 * @param {string} location - 区域范围 (lng1,lat1,lng2,lat2)
 */
export function getRectangleTraffic(location) {
  return request.get('/traffic/rectangle', {
    params: { location }
  })
}

/**
 * 检查路线路况
 * @param {object} data - { origin, destination, waypoints }
 */
export function checkRouteTraffic(data) {
  return request.post('/traffic/route', data)
}

/**
 * 分析路况并自动规避
 * @param {object} data - { origin, destination, waypoints, threshold }
 */
export function analyzeAndAvoid(data) {
  return request.post('/traffic/analyze', data)
}

/**
 * 批量监控路线
 * @param {array} routes - 路线列表
 */
export function monitorRoutes(routes) {
  return request.post('/traffic/monitor', { routes })
}
