import request from './request'

// 用户登录
export function login(data) {
  return request.post('/auth/login', data)
}

// 用户注册
export function register(data) {
  return request.post('/auth/register', data)
}

// 获取当前用户信息
export function getCurrentUser() {
  return request.get('/auth/me')
}

// 刷新token
export function refreshToken() {
  return request.post('/auth/refresh')
}

// 修改密码
export function changePassword(data) {
  return request.post('/auth/change-password', data)
}

// 获取用户列表
export function getUsers(params) {
  return request.get('/auth/users', { params })
}

// 创建用户
export function createUser(data) {
  return request.post('/auth/users', data)
}

// 更新用户
export function updateUser(id, data) {
  return request.put(`/auth/users/${id}`, data)
}

// 删除用户
export function deleteUser(id) {
  return request.delete(`/auth/users/${id}`)
}
