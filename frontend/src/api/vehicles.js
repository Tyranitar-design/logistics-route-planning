import request from './request'

// 获取车辆列表
export function getVehicles(params) {
  return request.get('/vehicles', { params })
}

// 获取单个车辆
export function getVehicle(id) {
  return request.get(`/vehicles/${id}`)
}

// 创建车辆
export function createVehicle(data) {
  return request.post('/vehicles', data)
}

// 更新车辆
export function updateVehicle(id, data) {
  return request.put(`/vehicles/${id}`, data)
}

// 删除车辆
export function deleteVehicle(id) {
  return request.delete(`/vehicles/${id}`)
}

// 更新车辆状态
export function updateVehicleStatus(id, status) {
  return request.put(`/vehicles/${id}/status`, { status })
}
