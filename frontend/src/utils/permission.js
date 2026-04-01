/**
 * 权限工具
 * 用于判断用户角色和权限
 */

/**
 * 获取当前用户信息
 */
export function getCurrentUser() {
  const userStr = localStorage.getItem('user')
  if (!userStr) return null
  
  try {
    return JSON.parse(userStr)
  } catch (e) {
    return null
  }
}

/**
 * 检查是否已登录
 */
export function isLoggedIn() {
  return !!localStorage.getItem('access_token')
}

/**
 * 检查是否是管理员
 */
export function isAdmin() {
  const user = getCurrentUser()
  return user?.role === 'admin'
}

/**
 * 检查是否是普通用户
 */
export function isUser() {
  const user = getCurrentUser()
  return user?.role === 'user' || user?.role === 'operator'
}

/**
 * 检查是否有编辑权限
 * 只有管理员可以编辑
 */
export function canEdit() {
  return isAdmin()
}

/**
 * 检查是否有删除权限
 * 只有管理员可以删除
 */
export function canDelete() {
  return isAdmin()
}

/**
 * 检查是否有创建权限
 * 只有管理员可以创建
 */
export function canCreate() {
  return isAdmin()
}

/**
 * 获取角色显示名称
 */
export function getRoleName(role) {
  const roleMap = {
    admin: '管理员',
    user: '普通用户',
    operator: '操作员',
    driver: '司机'
  }
  return roleMap[role] || role
}

/**
 * 获取角色标签类型（用于 el-tag）
 */
export function getRoleTagType(role) {
  const typeMap = {
    admin: 'danger',
    user: 'success',
    operator: 'warning',
    driver: 'info'
  }
  return typeMap[role] || ''
}

export default {
  getCurrentUser,
  isLoggedIn,
  isAdmin,
  isUser,
  canEdit,
  canDelete,
  canCreate,
  getRoleName,
  getRoleTagType
}