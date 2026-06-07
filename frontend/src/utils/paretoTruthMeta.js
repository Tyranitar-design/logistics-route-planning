export function normalizeParetoRow(row) {
  if (Array.isArray(row)) {
    return row.map(value => Number(value)).filter(value => Number.isFinite(value))
  }

  const objectives = row?.objectives || row
  if (objectives && typeof objectives === 'object') {
    const values = [
      objectives.distance,
      objectives.time,
      objectives.vehicles ?? objectives.vehicle_count ?? objectives.vehicle
    ]
    return values.map(value => Number(value)).filter(value => Number.isFinite(value))
  }

  return []
}

export function extractParetoSolutions(data = {}) {
  const rawFront = Array.isArray(data.pareto_front)
    ? data.pareto_front
    : Array.isArray(data.pareto_solutions)
      ? data.pareto_solutions
      : []

  if (rawFront.length > 0) {
    return rawFront
      .map(normalizeParetoRow)
      .filter(row => row.length >= 2)
  }

  if (Array.isArray(data.objectives) && data.objectives.length > 0) {
    const row = normalizeParetoRow(data.objectives)
    return row.length >= 2 ? [row] : []
  }

  if (data.objectives && typeof data.objectives === 'object') {
    const row = normalizeParetoRow(data.objectives)
    return row.length >= 2 ? [row] : []
  }

  return []
}

export function buildParetoFrontMeta(data = {}, solutions = extractParetoSolutions(data)) {
  const reportedQuality =
    data.pareto_summary?.front_quality ||
    data.front_quality ||
    data.pareto_front_quality ||
    null
  const hasReportedFront = Array.isArray(data.pareto_front) && data.pareto_front.length > 0
  const hasOnlyRepresentative = !hasReportedFront && solutions.length === 1
  const quality = reportedQuality ||
    (hasOnlyRepresentative ? 'single_solution_projection' : solutions.length <= 1 ? 'single_solution_only' : 'reported_front')

  const isProjection = ['single_solution_projection', 'single_solution_only', 'degenerate_front', 'low_diversity_front'].includes(quality)

  return {
    quality,
    count: solutions.length,
    hasReportedFront,
    isProjection,
    alertType: isProjection ? 'warning' : 'info',
    label: frontQualityLabel(quality),
    message: frontQualityMessage(quality, solutions.length, hasReportedFront)
  }
}

export function frontQualityLabel(quality) {
  const labels = {
    reported_front: '已返回前沿',
    multi_point_front: '多点前沿',
    approximate_front: '近似前沿',
    low_diversity_front: '低多样性前沿',
    degenerate_front: '退化前沿',
    single_solution_only: '单解结果',
    single_solution_projection: '单解投影'
  }
  return labels[quality] || quality || '未标注'
}

function frontQualityMessage(quality, count, hasReportedFront) {
  if (quality === 'single_solution_projection') {
    return '后端未返回真实 Pareto 前沿，仅返回一个代表性目标向量；前端按单点展示，不再扩展为伪前沿。'
  }
  if (quality === 'single_solution_only' || quality === 'degenerate_front') {
    return '当前只包含一个可解释方案，不能解读为多方案 Pareto 前沿。'
  }
  if (quality === 'low_diversity_front') {
    return '当前前沿多样性不足，适合做候选参考，不适合宣称充分覆盖权衡空间。'
  }
  if (hasReportedFront) {
    return `后端返回 ${count} 个前沿解，按原始解集展示。`
  }
  return `当前展示 ${count} 个解，前沿质量为 ${frontQualityLabel(quality)}。`
}
