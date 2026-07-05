import request from './request'

const PREFIX = '/cases/food-supply'

export function getFoodSupplySummary() {
  return request.get(`${PREFIX}/summary`)
}

export function validateFoodSupplyImport(payload = {}) {
  return request.post(`${PREFIX}/import/validate`, payload)
}

export function applyFoodSupplyImport(payload = {}) {
  return request.post(`${PREFIX}/import/apply`, payload)
}

export function getFoodSupplyNetwork() {
  return request.get(`${PREFIX}/network`)
}

export function buildFoodSupplyDistanceMatrix(payload = {}) {
  return request.post(`${PREFIX}/distance-matrix/build`, payload)
}

export function getFoodSupplyOsmCacheStatus() {
  return request.get(`${PREFIX}/osm-cache/status`)
}

export function buildFoodSupplyOsmCache(payload = {}) {
  return request.post(`${PREFIX}/osm-cache/build`, payload)
}

export function previewFoodSupplyRoute(payload = {}) {
  return request.post(`${PREFIX}/routes/preview`, payload)
}

export function compareFoodSupplyRoutes(payload = {}) {
  return request.post(`${PREFIX}/routes/compare`, payload)
}

export function getFoodSupplyRouteCompareHistory(params = {}) {
  return request.get(`${PREFIX}/routes/compare/history`, { params })
}

export function optimizeFoodSupplyNetwork(payload = {}) {
  return request.post(`${PREFIX}/optimize/network-design`, payload)
}

export function optimizeFoodSupplyDispatch(payload = {}) {
  return request.post(`${PREFIX}/optimize/dispatch`, payload)
}

export function optimizeFoodSupplyPareto(payload = {}) {
  return request.post(`${PREFIX}/optimize/pareto`, payload)
}

export function compareFoodSupplySolvers(payload = {}) {
  return request.post(`${PREFIX}/optimize/solver-compare`, payload)
}

export function createFoodSupplyScenario(payload = {}) {
  return request.post(`${PREFIX}/scenarios`, payload)
}

export function explainFoodSupplyCase(payload = {}) {
  return request.post(`${PREFIX}/agent/explain`, payload, { timeout: 120000 })
}

export function getFoodSupplyC2cClusters(params = {}) {
  return request.get(`${PREFIX}/c2c/clusters`, { params })
}

export function geocodeFoodSupplyC2c(payload = {}) {
  return request.post(`${PREFIX}/c2c/geocode`, payload)
}

export function getFoodSupplyC2cGeocodeStatus() {
  return request.get(`${PREFIX}/c2c/geocode/status`)
}

export function optimizeFoodSupplyLastMile(payload = {}) {
  return request.post(`${PREFIX}/optimize/last-mile`, payload)
}

export function getFoodSupplyOrchardTimeseries() {
  return request.get(`${PREFIX}/orchards/timeseries`)
}

export function getFoodSupplyOrchardForecast(params = {}) {
  return request.get(`${PREFIX}/orchards/forecast`, { params })
}

export function optimizeFoodSupplyMultimodal(payload = {}) {
  return request.post(`${PREFIX}/optimize/multimodal`, payload)
}

export function optimizeFoodSupplyDispatchFresh(payload = {}) {
  return request.post(`${PREFIX}/optimize/dispatch-fresh`, payload)
}

export function issueFoodSupplyTrace(payload = {}) {
  return request.post(`${PREFIX}/trace/issue`, payload)
}

export function lookupFoodSupplyTrace(traceCode) {
  return request.get(`${PREFIX}/trace/${traceCode}`)
}

export function getFoodSupplyScenarios(params = {}) {
  return request.get(`${PREFIX}/scenarios`, { params })
}

export function compareFoodSupplyScenarios(payload = {}) {
  return request.post(`${PREFIX}/scenarios/compare`, payload)
}

export function getFoodSupplyBusinessKpi() {
  return request.get(`${PREFIX}/business-kpi`)
}

export default {
  getFoodSupplySummary,
  validateFoodSupplyImport,
  applyFoodSupplyImport,
  getFoodSupplyNetwork,
  getFoodSupplyOsmCacheStatus,
  buildFoodSupplyDistanceMatrix,
  buildFoodSupplyOsmCache,
  previewFoodSupplyRoute,
  compareFoodSupplyRoutes,
  getFoodSupplyRouteCompareHistory,
  optimizeFoodSupplyNetwork,
  optimizeFoodSupplyDispatch,
  optimizeFoodSupplyPareto,
  compareFoodSupplySolvers,
  createFoodSupplyScenario,
  explainFoodSupplyCase,
  getFoodSupplyC2cClusters,
  geocodeFoodSupplyC2c,
  getFoodSupplyC2cGeocodeStatus,
  optimizeFoodSupplyLastMile,
  getFoodSupplyOrchardTimeseries,
  getFoodSupplyOrchardForecast,
  optimizeFoodSupplyMultimodal,
  optimizeFoodSupplyDispatchFresh,
  issueFoodSupplyTrace,
  lookupFoodSupplyTrace,
  getFoodSupplyScenarios,
  compareFoodSupplyScenarios,
}
