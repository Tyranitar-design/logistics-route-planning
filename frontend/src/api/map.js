import request from './request'

// 获取地图节点数据
export function getMapNodes() {
  return request({
    url: '/map/nodes',
    method: 'get'
  })
}

// 获取地图路线数据
export function getMapRoutes() {
  return request({
    url: '/map/routes',
    method: 'get'
  })
}
