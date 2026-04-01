/**
 * 高级路径优化 API
 */
import request from './request'

/**
 * 高级路径优化
 * @param {Object} data - 参数
 * @param {Array} data.node_ids - 节点ID列表
 * @param {string} data.algorithm - 算法选择 (aco, pso, drl, hybrid)
 * @param {Object} data.params - 算法参数
 */
export function optimizeRoute(data = {}) {
  return request({
    url: '/advanced-route/optimize',
    method: 'post',
    data
  })
}

/**
 * 对比不同算法效果
 * @param {Array} nodeIds - 节点ID列表
 */
export function compareAlgorithms(nodeIds = null) {
  return request({
    url: '/advanced-route/compare',
    method: 'post',
    data: { node_ids: nodeIds }
  })
}

/**
 * 获取可用算法列表
 */
export function getAlgorithms() {
  return request({
    url: '/advanced-route/algorithms',
    method: 'get'
  })
}

/**
 * 获取算法收敛曲线数据
 * @param {string} algorithm - 算法名称
 * @param {Array} nodeIds - 节点ID列表
 */
export function getConvergenceData(algorithm, nodeIds = null) {
  const params = nodeIds ? { node_ids: nodeIds.join(',') } : {}
  return request({
    url: `/advanced-route/convergence/${algorithm}`,
    method: 'get',
    params
  })
}