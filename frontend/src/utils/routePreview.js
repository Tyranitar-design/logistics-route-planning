export function buildRoutePreviewGeometry(path = []) {
  const points = []
  const invalidNodes = []

  for (const node of path) {
    const longitude = Number(Array.isArray(node) ? node[0] : node?.longitude ?? node?.lng)
    const latitude = Number(Array.isArray(node) ? node[1] : node?.latitude ?? node?.lat)

    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) {
      invalidNodes.push({
        id: node?.id ?? null,
        name: node?.name || '未知节点'
      })
      continue
    }

    points.push({
      name: node?.name || '未知节点',
      coord: [longitude, latitude]
    })
  }

  const valid = invalidNodes.length === 0 && points.length >= 2

  return {
    valid,
    points,
    lineCoords: points.map(point => point.coord),
    invalidNodes,
    reason: valid
      ? null
      : (invalidNodes.length > 0 ? 'NODE_COORDINATES_MISSING' : 'INSUFFICIENT_ROUTE_POINTS')
  }
}

export function buildRoutePreviewGeometryForRoute(route = {}) {
  const providerPaths = [
    route?.preview_path,
    route?.polyline,
    route?.route_polyline,
    route?.geometry
  ]

  for (const candidate of providerPaths) {
    if (!Array.isArray(candidate) || candidate.length === 0) continue
    const geometry = buildRoutePreviewGeometry(candidate)
    if (geometry.valid) {
      return {
        ...geometry,
        source: 'provider_polyline'
      }
    }
  }

  const pathGeometry = buildRoutePreviewGeometry(route?.path || [])
  if (pathGeometry.valid) {
    return {
      ...pathGeometry,
      source: 'node_sequence_projection',
      reason: 'ENDPOINT_PROJECTION'
    }
  }

  return pathGeometry
}
