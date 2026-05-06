export function buildObjectiveOptionsFromSolutions(solutions = [], objectiveLabels = {}) {
  const first = solutions.find(item => item?.objectives)?.objectives || {}
  return Object.keys(first).map(key => ({
    value: key,
    label: objectiveLabels[key] || key
  }))
}

export function normalizeParetoSolutions(solutions = [], objectiveLabels = {}) {
  return (solutions || [])
    .filter(item => item?.objectives)
    .map((item, index) => ({
      type: item.type || 'pareto',
      title: item.title || item.name || `方案 ${index + 1}`,
      description: item.description || '',
      objectives: { ...item.objectives },
      objectiveLabels,
      raw: item
    }))
}

export function buildScatterSeries(solutions = [], xKey, yKey) {
  return (solutions || [])
    .filter(item => item?.objectives && item.objectives[xKey] != null && item.objectives[yKey] != null)
    .map((item, index) => ({
      name: item.title || item.name || `方案 ${index + 1}`,
      type: item.type || 'pareto',
      description: item.description || '',
      x: Number(item.objectives[xKey]),
      y: Number(item.objectives[yKey]),
      objectives: item.objectives,
      raw: item
    }))
}

export function getParetoPointColor(type) {
  if (type === 'weighted_best') return '#67C23A'
  if (type === 'single_objective') return '#E6A23C'
  return '#409EFF'
}

export function buildParallelRows(solutions = [], objectiveKeys = []) {
  return (solutions || [])
    .filter(item => item?.objectives)
    .map((item, index) => {
      const row = {
        __name: item.title || item.name || `方案 ${index + 1}`,
        __type: item.type || 'pareto',
        __raw: item
      }
      objectiveKeys.forEach((key) => {
        row[key] = Number(item.objectives[key] ?? 0)
      })
      return row
    })
}

export function extractDistanceSourceSummary(sourceSummary = {}) {
  return {
    cacheExact: sourceSummary.cache_exact ?? 0,
    cacheApprox: sourceSummary.cache_approx ?? 0,
    amap: sourceSummary.amap ?? 0,
    fallback: (sourceSummary.haversine_corrected ?? 0) + (sourceSummary.fallback ?? 0)
  }
}
