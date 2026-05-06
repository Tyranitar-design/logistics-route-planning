export function formatNumber(value, digits = 2, fallback = '-') {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return fallback
  return Number(value).toFixed(digits)
}

export function formatPercent(value, digits = 2, fallback = '-') {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return fallback
  return `${(Number(value) * 100).toFixed(digits)}%`
}

export function formatGap(value, digits = 2, fallback = '-') {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return fallback
  return `${(Number(value) * 100).toFixed(digits)}%`
}

export function formatSeconds(value, digits = 3, fallback = '-') {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return fallback
  return `${Number(value).toFixed(digits)} s`
}

export function formatSolverName(name) {
  const map = {
    ortools: 'OR-Tools',
    gurobi: 'Gurobi',
    gurobi_vrptw: 'Gurobi VRPTW',
    pyvrp: 'PyVRP',
    pymoo_nsga2: 'pymoo NSGA-II',
    pymoo_nsga3: 'pymoo NSGA-III',
    genetic: 'Genetic',
    alns: 'ALNS',
    column_generation: 'Column Generation',
    lagrangian: 'Lagrangian',
    drl_vrp: 'DRL VRP'
  }
  return map[name] || name || '-'
}

export function formatObjectiveVector(values, digits = 2) {
  if (!Array.isArray(values) || values.length === 0) return '-'
  return values.map(v => formatNumber(v, digits)).join(' / ')
}

export function summarizeMode(problemSummary = {}) {
  const flags = []
  if (problemSummary.require_high_accuracy) flags.push('高精度')
  if (problemSummary.prefer_fast_response) flags.push('快速响应')
  if (problemSummary.realtime) flags.push('实时')
  return flags.length ? flags.join(' / ') : '标准'
}
