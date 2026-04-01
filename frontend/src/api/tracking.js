/**
 * 运输轨迹 API
 */
import request from './request'

/**
 * 获取路线轨迹坐标点
 */
export function getRoutePolyline(originId, destinationId) {
  return request.get(`/tracking/route/${originId}/${destinationId}`)
}

/**
 * 获取订单运输轨迹模拟数据
 */
export function simulateTracking(orderId, speed = 1.0) {
  return request.get(`/tracking/simulate/${orderId}`, {
    params: { speed }
  })
}

/**
 * 计算指定进度下的位置
 */
export function calculatePosition(polyline, progress) {
  return request.post('/tracking/position', { polyline, progress })
}

/**
 * 估算订单到达时间
 */
export function estimateArrival(orderId, progress = 0) {
  return request.get(`/tracking/eta/${orderId}`, {
    params: { progress }
  })
}

/**
 * 获取订单运输历史轨迹
 */
export function getTrackingHistory(orderId) {
  return request.get(`/tracking/history/${orderId}`)
}
