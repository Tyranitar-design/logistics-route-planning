/**
 * 多式联运 API
 */

import request from './request'

// 获取运输方式
export const getTransportModes = () => {
  return request.get('/multimodal/modes')
}

// 估算运输
export const estimateTransport = (distance, weight = 1) => {
  return request.get(`/multimodal/estimate?distance=${distance}&weight=${weight}`)
}

// 优化路线
export const optimizeRoute = (params) => {
  return request.post('/multimodal/optimize-route', params)
}

// 优化最后一公里
export const optimizeLastMile = (params) => {
  return request.post('/multimodal/last-mile/optimize', params)
}

// 比较车辆类型
export const compareVehicles = (params) => {
  return request.post('/multimodal/last-mile/compare-vehicles', params)
}

// 多车辆优化
export const optimizeMultiVehicle = (params) => {
  return request.post('/multimodal/last-mile/multi-vehicle', params)
}

// 查找转运节点
export const findTransferNodes = (params) => {
  return request.post('/multimodal/transfer-nodes', params)
}

export default {
  getTransportModes,
  estimateTransport,
  optimizeRoute,
  optimizeLastMile,
  compareVehicles,
  optimizeMultiVehicle,
  findTransferNodes
}