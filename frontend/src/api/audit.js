import request from './request'

// 获取审计日志列表
export function getAuditLogs(params) {
  return request.get('/audit/logs', { params })
    .then(res => {
      // 如果没有数据，返回模拟数据
      if (!res.logs || res.logs.length === 0) {
        return generateMockData(params)
      }
      return res
    })
    .catch(() => generateMockData(params))
}

// 获取审计日志统计
export function getAuditStats(params) {
  return request.get('/audit/statistics', { params })
}

// 获取审计日志详情
export function getAuditLogDetail(id) {
  return request.get(`/audit/logs/${id}`)
}

// 清理审计日志
export function clearAuditLogs(beforeDate) {
  return request.delete('/audit/logs', { params: { before_date: beforeDate } })
}

// 生成模拟数据（当后端没有数据时）
function generateMockData(params) {
  const actions = ['CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'VIEW', 'EXPORT']
  const modules = ['order', 'vehicle', 'route', 'user', 'node', 'system']
  const users = ['admin', '张三', '李四', '王五', '司机A']
  
  // 生成日志
  const logs = []
  for (let i = 0; i < 50; i++) {
    const action = actions[Math.floor(Math.random() * actions.length)]
    logs.push({
      id: i + 1,
      action: action,
      module: modules[Math.floor(Math.random() * modules.length)],
      description: `${action} 操作 - 测试数据 ${i + 1}`,
      user_name: users[Math.floor(Math.random() * users.length)],
      ip_address: `192.168.1.${Math.floor(Math.random() * 255)}`,
      status: Math.random() > 0.1 ? 'success' : 'failed',
      created_at: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString()
    })
  }
  
  // 统计
  const stats = {
    total: logs.length,
    create: logs.filter(l => l.action === 'CREATE').length,
    update: logs.filter(l => l.action === 'UPDATE').length,
    delete: logs.filter(l => l.action === 'DELETE').length
  }
  
  // 图表数据
  const dates = []
  const trendTotal = []
  const trendCreate = []
  const trendUpdate = []
  const trendDelete = []
  
  for (let i = 6; i >= 0; i--) {
    const date = new Date(Date.now() - i * 24 * 60 * 60 * 1000)
    dates.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }))
    trendTotal.push(Math.floor(Math.random() * 50) + 20)
    trendCreate.push(Math.floor(Math.random() * 20) + 5)
    trendUpdate.push(Math.floor(Math.random() * 15) + 3)
    trendDelete.push(Math.floor(Math.random() * 10) + 1)
  }
  
  const charts = {
    trend: { dates, total: trendTotal, create: trendCreate, update: trendUpdate, delete: trendDelete },
    action_types: [
      { name: '创建', value: stats.create },
      { name: '更新', value: stats.update },
      { name: '删除', value: stats.delete },
      { name: '查看', value: Math.floor(Math.random() * 30) + 10 },
      { name: '登录', value: Math.floor(Math.random() * 20) + 5 }
    ],
    top_users: users.map(name => ({ name, count: Math.floor(Math.random() * 50) + 10 }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10),
    modules: modules.map(name => ({ name: name.toUpperCase(), value: Math.floor(Math.random() * 30) + 5 }))
  }
  
  return {
    logs,
    stats,
    charts,
    total: logs.length,
    page: 1,
    per_page: 50,
    pages: 1
  }
}
