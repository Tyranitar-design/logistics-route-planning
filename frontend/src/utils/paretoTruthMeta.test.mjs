import assert from 'node:assert/strict'
import {
  buildParetoFrontMeta,
  extractParetoSolutions,
  frontQualityLabel
} from './paretoTruthMeta.js'

const multiPoint = {
  pareto_front: [
    [10, 20, 1],
    { objectives: { distance: 12, time: 18, vehicles: 2 } }
  ],
  pareto_summary: {
    front_quality: 'multi_point_front'
  }
}

const multiSolutions = extractParetoSolutions(multiPoint)
assert.deepEqual(multiSolutions, [[10, 20, 1], [12, 18, 2]])

const multiMeta = buildParetoFrontMeta(multiPoint, multiSolutions)
assert.equal(multiMeta.quality, 'multi_point_front')
assert.equal(multiMeta.count, 2)
assert.equal(multiMeta.hasReportedFront, true)
assert.equal(multiMeta.isProjection, false)

const representativeOnly = {
  objectives: [30, 45, 3],
  pareto_front_size: 20
}

const singleSolutions = extractParetoSolutions(representativeOnly)
assert.deepEqual(singleSolutions, [[30, 45, 3]])

const singleMeta = buildParetoFrontMeta(representativeOnly, singleSolutions)
assert.equal(singleMeta.quality, 'single_solution_projection')
assert.equal(singleMeta.count, 1)
assert.equal(singleMeta.hasReportedFront, false)
assert.equal(singleMeta.isProjection, true)
assert.match(singleMeta.message, /不再扩展为伪前沿/)

assert.equal(frontQualityLabel('degenerate_front'), '退化前沿')

console.log('paretoTruthMeta tests passed')
