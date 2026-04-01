import request from './request'

/**
 * 获取可用的优化目标列表
 */
export function getObjectives() {
  return request.get('/multi-objective/objectives')
}

/**
 * 多目标路径优化
 * @param {object} data - { origin_id, destination_id, weights, algorithm }
 */
export function optimizeRoute(data) {
  return request.post('/multi-objective/optimize', data)
}

/**
 * 对比多条路线
 * @param {array} routes - 路线列表
 */
export function compareRoutes(routes) {
  return request.post('/multi-objective/compare', { routes })
}
