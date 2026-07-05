/**
 * 高级求解器与 Gurobi 能力 API。
 */

import request from './request'

export function getGurobiHealth() {
  return request.get('/optimization/gurobi/health')
}

export function getSolverBenchmarkDemo() {
  return request.get('/optimization/solver-benchmark-demo')
}

export function getOptimizationCapabilities(params = {}) {
  return request.get('/optimization/capabilities', { params })
}

export function runSolverBenchmark(params = {}) {
  return request.post('/optimization/solver-benchmark', params)
}

export default {
  getGurobiHealth,
  getOptimizationCapabilities,
  getSolverBenchmarkDemo,
  runSolverBenchmark
}
