/**
 * 轨迹历史 API
 */
import request from './request'

/**
 * 生成演示轨迹
 * @param {number} vehicleId - 车辆ID
 * @param {object} data - 参数
 */
export function generateTrajectory(vehicleId, data) {
  return request({
    url: `/realtime/generate/${vehicleId}`,
    method: 'post',
    data
  })
}

/**
 * 获取车辆轨迹历史
 * @param {number} vehicleId - 车辆ID
 * @param {object} params - 查询参数
 */
export function getTrajectory(vehicleId, params = {}) {
  return request({
    url: `/realtime/${vehicleId}`,
    method: 'get',
    params
  })
}

/**
 * 获取所有轨迹
 */
export function getAllTrajectories() {
  return request({
    url: '/realtime/all',
    method: 'get'
  })
}

/**
 * 清除轨迹
 * @param {number} vehicleId - 车辆ID
 */
export function clearTrajectory(vehicleId) {
  return request({
    url: `/realtime/${vehicleId}`,
    method: 'delete'
  })
}

/**
 * 获取已完成订单轨迹
 * @param {number} days - 天数
 */
export function getCompletedOrdersTrajectory(days = 7) {
  return request({
    url: '/realtime/completed-orders',
    method: 'get',
    params: { days }
  })
}
