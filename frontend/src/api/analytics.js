/**
 * 数据分析 API
 */
import request from './request'

/**
 * 获取仪表盘数据
 */
export function getDashboard() {
  return request({
    url: '/analytics/dashboard',
    method: 'get'
  })
}

/**
 * 获取趋势分析
 * @param {Object} params - 参数
 * @param {string} params.start_date - 开始日期
 * @param {string} params.end_date - 结束日期
 * @param {string} params.granularity - 粒度
 */
export function getTrend(params = {}) {
  return request({
    url: '/analytics/trend',
    method: 'get',
    params
  })
}

/**
 * 获取成本分析
 * @param {string} period - 周期 (week, month, quarter, year)
 */
export function getCostAnalysis(period = 'month') {
  return request({
    url: '/analytics/cost',
    method: 'get',
    params: { period }
  })
}

/**
 * 获取路线性能分析
 */
export function getRoutePerformance() {
  return request({
    url: '/analytics/routes',
    method: 'get'
  })
}

/**
 * 获取车辆性能分析
 */
export function getVehiclePerformance() {
  return request({
    url: '/analytics/vehicles',
    method: 'get'
  })
}

/**
 * 生成运营报表
 * @param {Object} params - 参数
 * @param {string} params.type - 报表类型
 * @param {string} params.start_date - 开始日期
 * @param {string} params.end_date - 结束日期
 */
export function generateReport(params = {}) {
  return request({
    url: '/analytics/report',
    method: 'get',
    params
  })
}

/**
 * 需求预测
 * @param {number} days - 预测天数
 */
export function predictDemand(days = 7) {
  return request({
    url: '/analytics/predict',
    method: 'get',
    params: { days }
  })
}

/**
 * 导出 Excel 报表
 * @param {Object} params - 参数
 */
export async function exportExcel(params = {}) {
  const token = localStorage.getItem('access_token')
  if (!token) {
    throw new Error('请先登录')
  }
  
  const query = new URLSearchParams(params).toString()
  const url = `${request.defaults.baseURL}/analytics/export/excel?${query}`
  
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('登录已过期，请重新登录')
      }
      throw new Error('导出失败')
    }
    
    // 获取 blob
    const blob = await response.blob()
    
    // 创建下载链接
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.setAttribute('download', `report_${params.type || 'daily'}.xlsx`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
    
    return { success: true }
  } catch (error) {
    console.error('Excel 导出失败:', error)
    throw error
  }
}

/**
 * 导出 PDF 报表
 * @param {Object} params - 参数
 */
export async function exportPDF(params = {}) {
  const token = localStorage.getItem('access_token')
  if (!token) {
    throw new Error('请先登录')
  }
  
  const query = new URLSearchParams(params).toString()
  const url = `${request.defaults.baseURL}/analytics/export/pdf?${query}`
  
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('登录已过期，请重新登录')
      }
      throw new Error('导出失败')
    }
    
    // 获取 blob
    const blob = await response.blob()
    
    // 创建下载链接
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.setAttribute('download', `report_${params.type || 'daily'}.pdf`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
    
    return { success: true }
  } catch (error) {
    console.error('PDF 导出失败:', error)
    throw error
  }
}