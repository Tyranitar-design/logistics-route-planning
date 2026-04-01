// 供应商管理 API
import request from './request'

// ============ 供应商档案 ============

// 获取供应商列表
export function getSuppliers(params) {
  return request({
    url: '/suppliers',
    method: 'get',
    params
  })
}

// 获取供应商统计
export function getSupplierStatistics() {
  return request({
    url: '/suppliers/statistics',
    method: 'get'
  })
}

// 获取供应商详情
export function getSupplier(id) {
  return request({
    url: `/suppliers/${id}`,
    method: 'get'
  })
}

// 创建供应商
export function createSupplier(data) {
  return request({
    url: '/suppliers',
    method: 'post',
    data
  })
}

// 更新供应商
export function updateSupplier(id, data) {
  return request({
    url: `/suppliers/${id}`,
    method: 'put',
    data
  })
}

// 删除供应商
export function deleteSupplier(id) {
  return request({
    url: `/suppliers/${id}`,
    method: 'delete'
  })
}

// ============ 绩效评估 ============

// 获取供应商绩效
export function getSupplierPerformance(id) {
  return request({
    url: `/suppliers/${id}/performance`,
    method: 'get'
  })
}

// 执行绩效评估
export function evaluateSupplier(id, data) {
  return request({
    url: `/suppliers/${id}/evaluate`,
    method: 'post',
    data
  })
}

// 获取卡拉杰克矩阵
export function getPerformanceMatrix() {
  return request({
    url: '/suppliers/performance-matrix',
    method: 'get'
  })
}

// ============ 合同管理 ============

// 获取合同列表
export function getContracts(supplierId, params) {
  return request({
    url: `/suppliers/${supplierId}/contracts`,
    method: 'get',
    params
  })
}

// 创建合同
export function createContract(supplierId, data) {
  return request({
    url: `/suppliers/${supplierId}/contracts`,
    method: 'post',
    data
  })
}

// 更新合同
export function updateContract(contractId, data) {
  return request({
    url: `/suppliers/contracts/${contractId}`,
    method: 'put',
    data
  })
}

// 获取即将到期合同
export function getExpiringContracts(days = 30) {
  return request({
    url: '/suppliers/contracts/expiring',
    method: 'get',
    params: { days }
  })
}

// ============ 对账结算 ============

// 获取结算记录
export function getSettlements(supplierId, params) {
  return request({
    url: `/suppliers/${supplierId}/settlements`,
    method: 'get',
    params
  })
}

// 创建结算单
export function createSettlement(supplierId, data) {
  return request({
    url: `/suppliers/${supplierId}/settlements`,
    method: 'post',
    data
  })
}

// 确认对账
export function confirmSettlement(settlementId, data) {
  return request({
    url: `/suppliers/settlements/${settlementId}/confirm`,
    method: 'post',
    data
  })
}

// 记录付款
export function recordPayment(settlementId, data) {
  return request({
    url: `/suppliers/settlements/${settlementId}/pay`,
    method: 'post',
    data
  })
}

// ============ 风险监控 ============

// 获取风险记录
export function getRisks(supplierId, params) {
  return request({
    url: `/suppliers/${supplierId}/risks`,
    method: 'get',
    params
  })
}

// 上报风险
export function reportRisk(supplierId, data) {
  return request({
    url: `/suppliers/${supplierId}/risks`,
    method: 'post',
    data
  })
}

// 处置风险
export function mitigateRisk(riskId, data) {
  return request({
    url: `/suppliers/risks/${riskId}/mitigate`,
    method: 'post',
    data
  })
}

// 获取风险仪表盘
export function getRiskDashboard() {
  return request({
    url: '/suppliers/risk-dashboard',
    method: 'get'
  })
}

// ============ 选项数据 ============

// 获取供应商类型
export function getSupplierTypes() {
  return request({
    url: '/suppliers/types',
    method: 'get'
  })
}

// 获取卡拉杰克分类
export function getKraljicCategories() {
  return request({
    url: '/suppliers/kraljic-categories',
    method: 'get'
  })
}

// 获取风险类型
export function getRiskTypes() {
  return request({
    url: '/suppliers/risk-types',
    method: 'get'
  })
}

// 获取风险等级
export function getRiskLevels() {
  return request({
    url: '/suppliers/risk-levels',
    method: 'get'
  })
}
