import assert from 'node:assert/strict'
import { buildDecisionSolutions, normalizeObjectiveMap } from './multiObjectiveDisplay.js'
import { buildRoutePreviewGeometry, buildRoutePreviewGeometryForRoute } from './routePreview.js'

assert.deepEqual(normalizeObjectiveMap([12, 34, 2]), {
  distance: 12,
  time: 34,
  vehicles: 2
})

const recommendationResult = {
  distance_source: 'amap_driving',
  authenticity: { level: 'B' },
  recommendations: [{
    title: '真实道路优先',
    objectives: { distance: '12.5', time: 20 },
    path: [{ id: 1 }, { id: 2 }],
    recommendation_reason: '距离排名第1，时间排名第2',
    recommendation_reason_source: 'backend_multi_objective_governance',
    tradeoff_summary: {
      strengths: ['距离最优'],
      compromises: ['时间不是最优']
    },
    selection_metrics: {
      candidate_count: 3,
      front_quality: 'reported_front'
    }
  }]
}

const recSolutions = buildDecisionSolutions(recommendationResult)
assert.equal(recSolutions.length, 1)
assert.equal(recSolutions[0].distance_source, 'amap_driving')
assert.equal(recSolutions[0].authenticity_level, 'B')
assert.deepEqual(recSolutions[0].objectives, { distance: 12.5, time: 20 })
assert.equal(recSolutions[0].recommendation_reason, '距离排名第1，时间排名第2')
assert.equal(recSolutions[0].recommendation_reason_source, 'backend_multi_objective_governance')
assert.deepEqual(recSolutions[0].tradeoff_summary.strengths, ['距离最优'])
assert.equal(recSolutions[0].selection_metrics.candidate_count, 3)

const polylineResult = {
  distance_source: 'amap_driving_route',
  path_source: 'amap_driving_route',
  recommendations: [{
    title: 'AMap真实路线',
    objectives: { distance: 2268.6, time: 1480.8 },
    path: [
      { id: 1, name: '北京仓库', longitude: 116.4, latitude: 39.9 },
      { id: 7, name: '澳门节点', longitude: 113.5, latitude: 22.2 }
    ],
    polyline: [
      [116.4, 39.9],
      [114.3, 30.6],
      [113.5, 22.2]
    ]
  }]
}

const polylineSolutions = buildDecisionSolutions(polylineResult)
assert.deepEqual(polylineSolutions[0].path, polylineResult.recommendations[0].path)
assert.deepEqual(polylineSolutions[0].preview_path, polylineResult.recommendations[0].polyline)
const previewGeometry = buildRoutePreviewGeometry(polylineSolutions[0].preview_path)
assert.equal(previewGeometry.valid, true)
assert.deepEqual(previewGeometry.lineCoords, polylineResult.recommendations[0].polyline)
const routePreviewGeometry = buildRoutePreviewGeometryForRoute(polylineSolutions[0])
assert.equal(routePreviewGeometry.valid, true)
assert.deepEqual(routePreviewGeometry.lineCoords, polylineResult.recommendations[0].polyline)

const missingPolylineGeometry = buildRoutePreviewGeometryForRoute({
  path_source: 'amap_driving_route',
  path: polylineResult.recommendations[0].path
})
assert.equal(missingPolylineGeometry.valid, true)
assert.equal(missingPolylineGeometry.reason, 'ENDPOINT_PROJECTION')

const paretoResult = {
  pareto_front: [
    {
      objectives: [10, 30, 1],
      path_points: [{ name: '北京', longitude: 116.4, latitude: 39.9 }, { name: '澳门', longitude: 113.5, latitude: 22.2 }],
      route_candidate_id: 'amap-route-0',
      route_strategy: '速度最快',
      recommendation_reason: '非支配候选，距离排名第1',
      recommendation_reason_source: 'backend_multi_objective_governance',
      tradeoff_summary: {
        strengths: ['距离当前最优'],
        compromises: ['成本排名第2/3']
      },
      selection_metrics: {
        candidate_count: 3,
        front_quality: 'reported_front'
      }
    },
    [13, 24, 2]
  ],
  front_quality: 'single_solution_projection',
  path_source: 'solver_node_sequence'
}

const paretoSolutions = buildDecisionSolutions(paretoResult)
assert.equal(paretoSolutions.length, 2)
assert.equal(paretoSolutions[1].type, 'pareto')
assert.deepEqual(paretoSolutions[0].objectives, { distance: 10, time: 30, vehicles: 1 })
assert.equal(paretoSolutions[0].path.length, 2)
assert.equal(paretoSolutions[0].front_quality, 'single_solution_projection')
assert.equal(paretoSolutions[0].route_candidate_id, 'amap-route-0')
assert.equal(paretoSolutions[0].route_strategy, '速度最快')
assert.equal(paretoSolutions[0].recommendation_reason, '非支配候选，距离排名第1')
assert.equal(paretoSolutions[0].recommendation_reason_source, 'backend_multi_objective_governance')
assert.deepEqual(paretoSolutions[0].tradeoff_summary.compromises, ['成本排名第2/3'])
assert.equal(paretoSolutions[0].selection_metrics.candidate_count, 3)

const singleResult = {
  objectives: [20, 40, 2]
}

const singleSolutions = buildDecisionSolutions(singleResult)
assert.equal(singleSolutions.length, 1)
assert.equal(singleSolutions[0].path_source, 'single_solution_projection')
assert.equal(singleSolutions[0].fallback_reason, 'backend_returned_single_objective_vector')

console.log('multiObjectiveDisplay tests passed')
