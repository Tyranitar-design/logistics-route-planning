const OBJECTIVE_KEYS = ['distance', 'time', 'vehicles', 'cost', 'traffic', 'weather_risk']

export function normalizeObjectiveMap(objectives) {
  if (Array.isArray(objectives)) {
    return {
      distance: Number(objectives[0] ?? 0),
      time: Number(objectives[1] ?? 0),
      vehicles: Number(objectives[2] ?? 0)
    }
  }

  if (!objectives || typeof objectives !== 'object') return {}

  return Object.fromEntries(
    Object.entries(objectives)
      .filter(([, value]) => value != null && Number.isFinite(Number(value)))
      .map(([key, value]) => [key, Number(value)])
  )
}

export function buildDecisionSolutions(result = {}) {
  const recommendations = Array.isArray(result.recommendations) ? result.recommendations : []
  const normalizedRecommendations = recommendations
    .map((item, index) => normalizeRecommendation(item, index, result))
    .filter(item => Object.keys(item.objectives).length > 0)

  if (normalizedRecommendations.length > 0) {
    return normalizedRecommendations
  }

  const frontRows = Array.isArray(result.pareto_front) ? result.pareto_front : []
  const frontSolutions = frontRows
    .map((row, index) => {
      const objectives = normalizeObjectiveMap(row?.objectives || row)
      const rowFields = row && typeof row === 'object' && !Array.isArray(row) ? row : {}
      return {
        ...rowFields,
        type: index === 0 ? 'weighted_best' : 'pareto',
        title: index === 0 ? '推荐最优' : `Pareto 方案 ${index + 1}`,
        description: rowFields.description || describeObjectives(objectives),
        objectives,
        path: normalizePath(row, result, index),
        preview_path: normalizePreviewPath(row, result, index),
        front_quality: row?.front_quality || result.front_quality || result.pareto_summary?.front_quality,
        path_source: row?.path_source || result.path_source || 'solver_node_sequence',
        distance_source: row?.distance_source || result.distance_source || result.distance_precision?.source,
        authenticity_level: row?.authenticity_level || result.authenticity_level || result.authenticity?.level,
        fallback_reason: row?.fallback_reason || result.fallback_reason || result.authenticity?.fallback_reason
      }
    })
    .filter(item => Object.keys(item.objectives).length > 0)

  if (frontSolutions.length > 0) {
    return frontSolutions
  }

  const objectives = normalizeObjectiveMap(result.objectives)
  if (Object.keys(objectives).length === 0) return []

  return [{
    type: 'weighted_best',
    title: '代表性方案',
    description: describeObjectives(objectives),
    objectives,
    path: normalizePath(result, result, 0),
    preview_path: normalizePreviewPath(result, result, 0),
    front_quality: result.front_quality || result.pareto_summary?.front_quality || 'single_solution_projection',
    path_source: result.path_source || 'single_solution_projection',
    distance_source: result.distance_source || result.distance_precision?.source,
    authenticity_level: result.authenticity_level || result.authenticity?.level,
    fallback_reason: result.fallback_reason || result.authenticity?.fallback_reason || 'backend_returned_single_objective_vector'
  }]
}

function normalizeRecommendation(item, index, result) {
  const objectives = normalizeObjectiveMap(item?.objectives)
  return {
    ...item,
    type: item?.type || (index === 0 ? 'weighted_best' : 'pareto'),
    title: item?.title || `方案 ${index + 1}`,
    description: item?.description || describeObjectives(objectives),
    objectives,
    path: normalizePath(item, result, index),
    preview_path: normalizePreviewPath(item, result, index),
    front_quality: item?.front_quality || result.front_quality || result.pareto_summary?.front_quality,
    path_source: item?.path_source || result.path_source || 'solver_node_sequence',
    distance_source: item?.distance_source || result.distance_source || result.distance_precision?.source,
    authenticity_level: item?.authenticity_level || result.authenticity_level || result.authenticity?.level,
    fallback_reason: item?.fallback_reason || result.fallback_reason || result.authenticity?.fallback_reason
  }
}

function normalizePath(item = {}, result = {}, index = 0) {
  const candidates = [
    item?.path,
    item?.route,
    item?.route_path,
    item?.path_points,
    item?.nodes,
    result?.paths?.[index],
    result?.routes?.[index],
    result?.routes?.[0],
    result?.path,
    result?.route,
    result?.route_path,
    result?.path_points
  ]

  const path = candidates.find(candidate => Array.isArray(candidate) && candidate.length > 0)
  return Array.isArray(path) ? path : []
}

function normalizePreviewPath(item = {}, result = {}, index = 0) {
  const candidates = [
    item?.preview_path,
    item?.polyline,
    item?.route_polyline,
    item?.geometry,
    result?.previews?.[index],
    result?.polylines?.[index],
    result?.routes?.[index]?.polyline,
    result?.polyline,
    normalizePath(item, result, index)
  ]

  const path = candidates.find(candidate => Array.isArray(candidate) && candidate.length > 0)
  return Array.isArray(path) ? path : []
}

function describeObjectives(objectives) {
  const parts = OBJECTIVE_KEYS
    .filter(key => objectives[key] != null)
    .map(key => `${key}: ${formatNumber(objectives[key])}`)
  return parts.length ? parts.join(' / ') : '后端返回的目标向量'
}

function formatNumber(value) {
  return Number(value).toFixed(1)
}
