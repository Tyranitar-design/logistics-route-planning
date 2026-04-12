import request from './request'

// 获取 Redis 连接状态
export function getRedisStatus() {
  return request({ url: '/redis/status', method: 'get' })
}

// 获取热门路线排行榜
export function getPopularRoutes(limit = 10) {
  return request({ url: '/redis/popular-routes', method: 'get', params: { limit } })
}

// 获取订单计数
export function getOrderCount(region = 'total', date = null) {
  return request({ url: '/redis/order-count', method: 'get', params: { region, date } })
}

// 获取缓存的仪表盘数据
export function getDashboardCache() {
  return request({ url: '/redis/dashboard-cache', method: 'get' })
}

// 获取搜索历史
export function getSearchHistory(userId = 1, limit = 10) {
  return request({ url: '/redis/search-history', method: 'get', params: { user_id: userId, limit } })
}

// 添加搜索历史
export function addSearchHistory(userId, query) {
  return request({ url: '/redis/search-history', method: 'post', data: { user_id: userId, query } })
}
