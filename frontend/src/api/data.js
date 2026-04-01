import request from './request'

// ==================== 数据导入 ====================

/**
 * 导入节点数据
 * @param {FormData} formData - 包含 Excel 文件的表单数据
 */
export function importNodes(formData) {
  return request.post('/data/import/nodes', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

/**
 * 导入订单数据
 * @param {FormData} formData - 包含 Excel 文件的表单数据
 */
export function importOrders(formData) {
  return request.post('/data/import/orders', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

/**
 * 导入路线数据
 */
export function importRoutes(formData) {
  return request.post('/data/import/routes', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// ==================== 数据导出 ====================

/**
 * 导出数据
 * @param {Object} params - 导出参数
 * @param {string} params.type - 导出类型: nodes, routes, vehicles, orders, transport_report
 * @param {string} params.format - 导出格式: xlsx, csv
 * @param {string} params.start_date - 开始日期（报表用）
 * @param {string} params.end_date - 结束日期（报表用）
 * @returns {Promise<Blob>} - 返回文件 Blob
 */
export function exportData(params) {
  return request.get('/data/export', {
    params,
    responseType: 'blob'
  })
}

/**
 * 导出节点数据
 */
export function exportNodes(format = 'xlsx') {
  return exportData({ type: 'nodes', format })
}

/**
 * 导出订单数据
 */
export function exportOrders(format = 'xlsx') {
  return exportData({ type: 'orders', format })
}

/**
 * 导出运输报表
 */
export function exportTransportReport(startDate, endDate, format = 'xlsx') {
  return exportData({
    type: 'transport_report',
    format,
    start_date: startDate,
    end_date: endDate
  })
}

/**
 * 下载导入模板
 * @param {string} type - 模板类型: nodes, orders
 */
export function downloadTemplate(type) {
  return request.get(`/data/template/${type}`, {
    responseType: 'blob'
  })
}
