import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    const message = error.response?.data?.fallback_reason || error.response?.data?.error || error.response?.data?.message
    if (error.code === 'ECONNABORTED' || String(error.message || '').includes('timeout')) {
      ElMessage.error('请求超时：高级 AI 任务请使用手动全量分析，页面默认已使用轻量模式')
      return Promise.reject(error)
    }
    if (error.response) {
      switch (error.response.status) {
        case 401:
          ElMessage.error(message || '需要登录或登录已过期，请重新登录后再访问该接口')
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user')
          window.location.href = '/login'
          break
        case 403:
          ElMessage.error(message || '当前账号没有权限访问该接口')
          break
        case 404:
          ElMessage.error(
            message || '接口不存在：请确认后端是当前 backend\\.venv 进程，并检查 /api/runtime/capabilities 的路由注册摘要'
          )
          break
        case 500:
          ElMessage.error(message || '服务器错误：请查看后端日志定位具体接口')
          break
        default:
          ElMessage.error(message || '请求失败')
      }
    } else {
      ElMessage.error('后端不可达：请确认 Flask 服务已启动且前端代理指向 /api')
    }
    return Promise.reject(error)
  }
)

export default request
