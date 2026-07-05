/**
 * 真实 shipment_facts 驱动的 AI 异常检测 API。
 *
 * 这些接口替代旧 /anomaly/* 页面依赖，适配当前 /ai-anomaly/* 蓝图。
 */

import request from './request'

export const INTERACTIVE_ANOMALY_TASKS = ['status', 'geo', 'cost', 'eta', 'delay', 'od_volume', 'node_congestion']
export const FULL_ANOMALY_TASKS = [...INTERACTIVE_ANOMALY_TASKS, 'ml']
export const INTERACTIVE_LIMIT = 5000
export const FULL_LIMIT = 50000
const FULL_TIMEOUT = 120000

export function getAiAnomalyHealth() {
  return request.get('/ai-anomaly/health')
}

export function detectShipmentAnomalies(params = {}) {
  const isFull = params.runtime_profile === 'full'
  return request.post('/ai-anomaly/detect', {
    tasks: isFull ? FULL_ANOMALY_TASKS : INTERACTIVE_ANOMALY_TASKS,
    runtime_profile: isFull ? 'full' : 'interactive',
    limit: isFull ? FULL_LIMIT : INTERACTIVE_LIMIT,
    anomaly_limit: 40,
    use_ml: isFull,
    ...params
  }, isFull ? { timeout: FULL_TIMEOUT } : undefined)
}

export function getAiAnomalyScorecard(params = {}) {
  const isFull = params.runtime_profile === 'full'
  return request.post('/ai-anomaly/scorecard', {
    tasks: isFull ? FULL_ANOMALY_TASKS : INTERACTIVE_ANOMALY_TASKS,
    runtime_profile: isFull ? 'full' : 'interactive',
    limit: isFull ? FULL_LIMIT : INTERACTIVE_LIMIT,
    anomaly_limit: isFull ? 160 : 80,
    use_ml: isFull,
    ...params
  }, isFull ? { timeout: FULL_TIMEOUT } : undefined)
}

export function explainShipmentAnomaly(params = {}) {
  return request.post('/ai-anomaly/explain', params)
}

export default {
  getAiAnomalyHealth,
  detectShipmentAnomalies,
  getAiAnomalyScorecard,
  explainShipmentAnomaly
}
