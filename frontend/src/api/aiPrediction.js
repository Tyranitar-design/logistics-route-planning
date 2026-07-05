/**
 * 真实 shipment_facts 驱动的 AI 预测 API。
 *
 * 这些接口替代旧 /ml/* 链路，适配当前后端 /ai-prediction/* 蓝图。
 */

import request from './request'

export const INTERACTIVE_LIMIT = 5000
export const TRAINING_LIMIT = 10000
export const FULL_LIMIT = 50000

const DEFAULT_PROFILE = 'interactive'
const FULL_TIMEOUT = 120000
const PREDICT_TIMEOUT = 60000

export function getPredictionHealth() {
  return request.get('/ai-prediction/health')
}

export function getPredictionTimelineAudit(params = {}) {
  return request.get('/ai-prediction/timeline/audit', { params })
}

export function evaluatePredictionBaselines(params = {}) {
  return request.post('/ai-prediction/baseline/evaluate', {
    tasks: ['demand', 'eta', 'delay', 'cost'],
    horizon_days: 7,
    runtime_profile: DEFAULT_PROFILE,
    limit: INTERACTIVE_LIMIT,
    ...params
  })
}

export function getDemandForecast(days = 7, city = null, limit = INTERACTIVE_LIMIT, options = {}) {
  const params = {
    days,
    runtime_profile: DEFAULT_PROFILE,
    limit,
    time_granularity: 'auto',
    series_source: 'shipped_at',
    ...options
  }
  if (city) params.city = city
  return request.get('/ai-prediction/demand/forecast', { params })
}

export function evaluateTimeSeriesBenchmark(params = {}) {
  return request.post('/ai-prediction/time-series/benchmark', {
    task: 'demand',
    horizon_days: 14,
    test_days: 14,
    sequence_length: 14,
    runtime_profile: DEFAULT_PROFILE,
    limit: INTERACTIVE_LIMIT,
    ...params
  })
}

export function forecastCapacityGap(params = {}) {
  return request.post('/ai-prediction/capacity-gap/forecast', {
    horizon_days: 14,
    test_days: 14,
    sequence_length: 14,
    runtime_profile: DEFAULT_PROFILE,
    limit: INTERACTIVE_LIMIT,
    ...params
  })
}

export function forecastCostVolatility(params = {}) {
  return request.post('/ai-prediction/cost-volatility/forecast', {
    horizon_days: 14,
    test_days: 14,
    sequence_length: 14,
    volatility_window: 7,
    runtime_profile: DEFAULT_PROFILE,
    limit: INTERACTIVE_LIMIT,
    ...params
  })
}

export function getPredictionScorecard(params = {}) {
  return request.post('/ai-prediction/scorecard', {
    horizon_days: 14,
    test_days: 14,
    sequence_length: 14,
    runtime_profile: DEFAULT_PROFILE,
    limit: INTERACTIVE_LIMIT,
    ...params
  })
}

export function getPredictionFeatureDataset(params = {}) {
  return request.post('/ai-prediction/features/dataset', {
    task: 'eta',
    runtime_profile: DEFAULT_PROFILE,
    limit: INTERACTIVE_LIMIT,
    row_limit: 8,
    ...params
  })
}

export function getPredictionModelStatus() {
  return request.get('/ai-prediction/model/status')
}

export function createPredictionJob(params = {}) {
  return request.post('/ai-prediction/jobs', {
    task: 'demand',
    model_family: 'lstm',
    runtime_profile: 'full',
    limit: FULL_LIMIT,
    horizon_days: 14,
    test_days: 14,
    sequence_length: 14,
    ...params
  }, { timeout: 10000 })
}

export function getPredictionJob(jobId) {
  return request.get(`/ai-prediction/jobs/${jobId}`)
}

export function trainPredictionModel(params = {}) {
  return request.post('/ai-prediction/model/train', {
    task: 'eta',
    runtime_profile: 'full',
    limit: TRAINING_LIMIT,
    test_ratio: 0.25,
    hash_buckets: 24,
    alpha: 1.0,
    ...params
  }, { timeout: FULL_TIMEOUT })
}

export function evaluatePredictionModel(params = {}) {
  return request.post('/ai-prediction/model/evaluate', {
    task: 'eta',
    runtime_profile: 'full',
    limit: TRAINING_LIMIT,
    row_limit: 20,
    ...params
  }, { timeout: PREDICT_TIMEOUT })
}

export function predictWithPredictionModel(params = {}) {
  return request.post('/ai-prediction/model/predict', {
    task: 'eta',
    runtime_profile: 'full',
    limit: TRAINING_LIMIT,
    row_limit: 20,
    ...params
  }, { timeout: PREDICT_TIMEOUT })
}

export default {
  getPredictionHealth,
  getPredictionTimelineAudit,
  evaluatePredictionBaselines,
  getDemandForecast,
  evaluateTimeSeriesBenchmark,
  forecastCapacityGap,
  forecastCostVolatility,
  getPredictionScorecard,
  getPredictionFeatureDataset,
  getPredictionModelStatus,
  createPredictionJob,
  getPredictionJob,
  trainPredictionModel,
  evaluatePredictionModel,
  predictWithPredictionModel
}
