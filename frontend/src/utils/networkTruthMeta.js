const NAVIGATION_PATH_SOURCES = new Set(['amap_navigation'])
const APPROXIMATE_PATH_SOURCES = new Set([
  'facility_assignment',
  'coverage_assignment',
  'facility_flow_assignment',
  'facility_assignment_weighted',
  'dynamic_facility_plan',
  'scenario_index',
  'scenario_snapshot',
  'scenario_create',
  'scenario_update',
  'scenario_delete',
  'scenario_comparison',
  'visualization_projection',
  'node_import_dataset',
  'synthetic_sampling',
  'solver_node_sequence',
  'tracking_simulation',
  'synthetic_preview'
])

export function isNavigationPathSource(pathSource) {
  return NAVIGATION_PATH_SOURCES.has(pathSource)
}

export function isApproximateNetworkTruth(truth = {}) {
  const level = truth.authenticity_level || truth.level
  const pathSource = truth.path_source || truth.pathSource

  if (level === 'C' || level === 'D') return true
  if (APPROXIMATE_PATH_SOURCES.has(pathSource)) return true

  return !isNavigationPathSource(pathSource)
}

export function buildNetworkTruthMeta(payload = {}) {
  const level = payload.authenticity_level || payload.authenticity?.level || 'unknown'
  const distanceSource = payload.distance_source || payload.authenticity?.distance_source || 'unknown'
  const pathSource = payload.path_source || payload.authenticity?.path_source || 'unknown'
  const fallbackReason = payload.fallback_reason || payload.authenticity?.fallback_reason || ''
  const isNavigationPath = isNavigationPathSource(pathSource)
  const isApproximate = isApproximateNetworkTruth({
    authenticity_level: level,
    path_source: pathSource
  })

  return {
    level,
    distanceSource,
    pathSource,
    fallbackReason,
    isNavigationPath,
    isApproximate,
    alertType: level === 'A' && isNavigationPath ? 'success' : 'warning',
    message: buildNetworkTruthMessage({ level, distanceSource, pathSource, fallbackReason, isNavigationPath })
  }
}

function buildNetworkTruthMessage({ level, distanceSource, pathSource, fallbackReason, isNavigationPath }) {
  if (pathSource === 'synthetic_sampling' || distanceSource === 'synthetic_generator' || level === 'D') {
    return `测试/模拟数据：${fallbackReason || 'synthetic data'}`
  }

  if (pathSource === 'visualization_projection') {
    return '当前连线是可视化投影，不代表真实道路导航路径'
  }

  if (!isNavigationPath) {
    return `当前路径语义为 ${pathSource}，距离来源为 ${distanceSource}，不可按真实导航路径解读`
  }

  return `真实导航路径：距离来源 ${distanceSource}`
}
