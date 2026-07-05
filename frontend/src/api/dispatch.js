/**
 * 智能调度 API
 */
import request from './request'

const INTERACTIVE_SHADOW_PARAMS = {
  runtime_profile: 'interactive',
  scenario_limit: 1,
  row_limit: 20,
  anomaly_source_limit: 2000,
  anomaly_limit: 40,
  use_ml: false,
  top_k: 5
}

const SHADOW_FULL_TIMEOUT = 120000

function shadowRequestConfig(params = {}) {
  return params.runtime_profile === 'full' ? { timeout: SHADOW_FULL_TIMEOUT } : undefined
}

/**
 * 自动调度
 * @param {Object} params - 调度参数
 * @param {number[]} params.order_ids - 订单ID列表
 * @param {number[]} params.vehicle_ids - 车辆ID列表
 * @param {boolean} params.consider_weather - 是否考虑天气
 * @param {boolean} params.consider_traffic - 是否考虑路况
 * @param {number} params.max_orders_per_vehicle - 每车最大订单数
 */
export function autoDispatch(params = {}) {
  return request({
    url: '/dispatch/auto',
    method: 'post',
    data: params
  })
}

/**
 * 智能调度 - 统一调度引擎
 * @param {Object} params - 调度参数
 * @param {number[]} params.order_ids - 订单ID列表
 * @param {number[]} params.vehicle_ids - 车辆ID列表
 * @param {Object} params.weights - 多目标权重
 * @param {number} params.weights.cost - 成本权重 (0-1)
 * @param {number} params.weights.time - 时间权重 (0-1)
 * @param {number} params.weights.satisfaction - 满意度权重 (0-1)
 * @param {boolean} params.consider_weather - 是否考虑天气
 * @param {boolean} params.consider_traffic - 是否考虑路况
 * @param {string} params.algorithm - 算法选择 ('balanced' | 'greedy' | 'capacity_first' | 'genetic')
 * @param {string} params.data_source - 订单来源 ('auto' | 'shipment_fact' | 'orders')
 */
export function smartDispatch(params = {}) {
  return request({
    url: '/dispatch/smart',
    method: 'post',
    data: params
  })
}

/**
 * 获取可用算法列表
 */
export function getAlgorithms() {
  return request({
    url: '/dispatch/algorithms',
    method: 'get'
  })
}

/**
 * 获取调度健康诊断
 */
export function getDispatchHealth() {
  return request({
    url: '/dispatch/health',
    method: 'get'
  })
}

/**
 * 创建调度波次
 */
export function createDispatchWave(params = {}) {
  return request({
    url: '/dispatch/waves',
    method: 'post',
    data: params
  })
}

/**
 * 获取调度场景
 */
export function getDispatchScenario(id) {
  return request({
    url: `/dispatch/scenarios/${id}`,
    method: 'get'
  })
}

/**
 * 获取最近调度场景
 */
export function listDispatchScenarios(params = {}) {
  return request({
    url: '/dispatch/scenarios',
    method: 'get',
    params
  })
}

/**
 * 对比求解器
 */
export function compareDispatchSolvers(params = {}) {
  return request({
    url: '/dispatch/compare-solvers',
    method: 'post',
    data: params
  })
}

/**
 * 获取调度 AI/RL shadow readiness benchmark
 */
export function getDispatchShadowBenchmark(params = {}) {
  return request({
    url: '/dispatch/shadow-benchmark',
    method: 'get',
    params: {
      ...INTERACTIVE_SHADOW_PARAMS,
      test_ratio: 0.3,
      ...params
    },
    ...shadowRequestConfig(params)
  })
}

/**
 * 获取调度 shadow benchmark 快照
 */
export function getDispatchShadowBenchmarkSnapshot(params = {}) {
  return request({
    url: '/dispatch/shadow-benchmark/snapshot',
    method: 'get',
    params: {
      ...INTERACTIVE_SHADOW_PARAMS,
      test_ratio: 0.3,
      ...params
    },
    ...shadowRequestConfig(params)
  })
}

/**
 * 获取动态重调度 shadow 模拟
 */
export function getDispatchRedispatchSimulator(params = {}) {
  return request({
    url: '/dispatch/redispatch-simulator',
    method: 'get',
    params: {
      ...INTERACTIVE_SHADOW_PARAMS,
      delay_minutes: 45,
      unavailable_vehicle_ratio: 0.1,
      cost_multiplier: 1.12,
      ...params
    },
    ...shadowRequestConfig(params)
  })
}

/**
 * 获取 RL shadow runner
 */
export function getDispatchRlShadowRunner(params = {}) {
  return request({
    url: '/dispatch/rl-shadow-runner',
    method: 'get',
    params: {
      ...INTERACTIVE_SHADOW_PARAMS,
      episode_limit: 50,
      ...params
    },
    ...shadowRequestConfig(params)
  })
}

/**
 * 获取 Fitted-Q shadow model
 */
export function getDispatchFittedQShadowModel(params = {}) {
  return request({
    url: '/dispatch/fitted-q-shadow-model',
    method: 'get',
    params: {
      ...INTERACTIVE_SHADOW_PARAMS,
      test_ratio: 0.3,
      ...params
    },
    ...shadowRequestConfig(params)
  })
}

/**
 * 创建调度 AI/RL shadow 策略后台任务
 */
export function createDispatchPolicyJob(params = {}) {
  return request({
    url: '/dispatch/policy/jobs',
    method: 'post',
    data: {
      runtime_profile: 'full',
      policy_family: 'fitted_q',
      scenario_limit: 50,
      row_limit: 200,
      top_k: 10,
      use_ml: false,
      ...params
    },
    timeout: 10000
  })
}

/**
 * 查询调度 AI/RL shadow 策略任务
 */
export function getDispatchPolicyJob(jobId) {
  return request({
    url: `/dispatch/policy/jobs/${jobId}`,
    method: 'get'
  })
}

/**
 * 获取已落库调度场景学习数据集
 */
export function getDispatchLearningDataset(params = {}) {
  return request({
    url: '/dispatch/learning-dataset',
    method: 'get',
    params: {
      ...INTERACTIVE_SHADOW_PARAMS,
      ...params
    },
    ...shadowRequestConfig(params)
  })
}

/**
 * 获取调度 shadow policy scorer
 */
export function getDispatchPolicyScorer(params = {}) {
  return request({
    url: '/dispatch/policy-scorer',
    method: 'get',
    params: {
      ...INTERACTIVE_SHADOW_PARAMS,
      ...params
    },
    ...shadowRequestConfig(params)
  })
}

/**
 * 获取调度 reward model 基线
 */
export function getDispatchRewardModel(params = {}) {
  return request({
    url: '/dispatch/reward-model',
    method: 'get',
    params: {
      ...INTERACTIVE_SHADOW_PARAMS,
      test_ratio: 0.3,
      ...params
    },
    ...shadowRequestConfig(params)
  })
}

/**
 * 预览调度结果
 * @param {Object} params - 调度参数
 */
export function previewDispatch(params = {}) {
  return request({
    url: '/dispatch/preview',
    method: 'post',
    data: params
  })
}

/**
 * 获取可合并订单建议
 * @param {Object} params - 参数
 * @param {string} params.order_ids - 订单ID列表（逗号分隔）
 * @param {number} params.max_distance - 最大合并距离
 */
export function getMergeSuggestions(params = {}) {
  return request({
    url: '/dispatch/merge-suggestions',
    method: 'get',
    params
  })
}

/**
 * 应用调度计划
 * @param {Object|Object[]} payload - 调度场景或计划列表
 */
export function applyDispatch(payload) {
  return request({
    url: '/dispatch/apply',
    method: 'post',
    data: Array.isArray(payload) ? { plans: payload } : payload
  })
}
