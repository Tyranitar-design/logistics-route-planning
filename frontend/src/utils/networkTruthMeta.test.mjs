import assert from 'node:assert/strict'
import {
  buildNetworkTruthMeta,
  isNavigationPathSource,
  isApproximateNetworkTruth
} from './networkTruthMeta.js'

const synthetic = buildNetworkTruthMeta({
  distance_source: 'synthetic_generator',
  path_source: 'synthetic_sampling',
  authenticity_level: 'D',
  fallback_reason: 'generated_test_data'
})

assert.equal(synthetic.level, 'D')
assert.equal(synthetic.distanceSource, 'synthetic_generator')
assert.equal(synthetic.pathSource, 'synthetic_sampling')
assert.equal(synthetic.isNavigationPath, false)
assert.equal(synthetic.isApproximate, true)
assert.equal(synthetic.alertType, 'warning')
assert.match(synthetic.message, /测试|模拟|合成/)

const projection = buildNetworkTruthMeta({
  distance_source: 'derived_from_input',
  path_source: 'visualization_projection',
  authenticity_level: 'C'
})

assert.equal(projection.level, 'C')
assert.equal(projection.isNavigationPath, false)
assert.equal(projection.isApproximate, true)
assert.match(projection.message, /投影/)

const importedNodes = buildNetworkTruthMeta({
  distance_source: 'derived_from_input',
  path_source: 'node_import_dataset',
  authenticity_level: 'C',
  fallback_reason: 'imported_nodes_are_coordinate_dataset_not_navigation_path'
})

assert.equal(importedNodes.isNavigationPath, false)
assert.equal(importedNodes.isApproximate, true)
assert.match(importedNodes.message, /node_import_dataset|真实导航路径/)

const realNavigation = buildNetworkTruthMeta({
  distance_source: 'amap',
  path_source: 'amap_navigation',
  authenticity_level: 'A'
})

assert.equal(realNavigation.isNavigationPath, true)
assert.equal(realNavigation.isApproximate, false)
assert.equal(realNavigation.alertType, 'success')

assert.equal(isNavigationPathSource('amap_navigation'), true)
assert.equal(isNavigationPathSource('facility_assignment'), false)
assert.equal(isApproximateNetworkTruth({ authenticity_level: 'C' }), true)
assert.equal(isApproximateNetworkTruth({ authenticity_level: 'A', path_source: 'amap_navigation' }), false)
