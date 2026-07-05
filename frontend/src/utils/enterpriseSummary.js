const CITY_COORDS = {
  北京: [116.46, 39.92],
  上海: [121.48, 31.22],
  广州: [113.23, 23.16],
  深圳: [114.07, 22.62],
  杭州: [120.19, 30.26],
  南京: [118.78, 32.04],
  成都: [104.06, 30.67],
  武汉: [114.31, 30.52],
  西安: [108.95, 34.27],
  重庆: [106.55, 29.56],
  天津: [117.2, 39.13],
  苏州: [120.62, 31.32],
  郑州: [113.65, 34.76],
  长沙: [113.0, 28.21],
  青岛: [120.33, 36.07],
  宁波: [121.56, 29.86],
  厦门: [118.1, 24.46],
  福州: [119.3, 26.08]
}

export const toNumber = (value, fallback = 0) => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : fallback
}

export const round = (value, digits = 0) => {
  const factor = 10 ** digits
  return Math.round(toNumber(value) * factor) / factor
}

export const asPercent = (value, digits = 0) => {
  const numeric = toNumber(value)
  const percent = numeric <= 1 ? numeric * 100 : numeric
  return round(percent, digits)
}

export const compactNumber = (value) => {
  const numeric = toNumber(value)
  if (numeric >= 100000000) return `${round(numeric / 100000000, 1)}亿`
  if (numeric >= 10000) return `${round(numeric / 10000, 1)}万`
  return Math.round(numeric).toLocaleString()
}

export const currencyText = (value) => `¥${compactNumber(value)}`

export const emptyEnterpriseSummary = () => ({
  success: false,
  data_source: 'shipment_fact',
  provider_status: 'degraded',
  fallback_reason: 'ENTERPRISE_SUMMARY_NOT_LOADED',
  authenticity_level: 'C',
  runtime_profile: 'interactive',
  summary: {},
  kpis: {},
  trend: [],
  top_lanes: [],
  city_breakdown: [],
  cost_components: [],
  prediction: { predictions: [], forecast: [], series_summary: {} },
  anomaly: { summary: {}, components: [] },
  capabilities: { summary: {}, capabilities: [] },
  recommendations: []
})

export const normalizeEnterpriseSummary = (summary) => ({
  ...emptyEnterpriseSummary(),
  ...(summary || {}),
  summary: summary?.summary || {},
  kpis: summary?.kpis || {},
  trend: summary?.trend || [],
  top_lanes: summary?.top_lanes || [],
  city_breakdown: summary?.city_breakdown || [],
  cost_components: summary?.cost_components || [],
  prediction: {
    predictions: [],
    forecast: [],
    series_summary: {},
    ...(summary?.prediction || {})
  },
  anomaly: {
    summary: {},
    components: [],
    ...(summary?.anomaly || {})
  },
  capabilities: {
    summary: {},
    capabilities: [],
    ...(summary?.capabilities || {})
  },
  recommendations: summary?.recommendations || []
})

export const enterpriseTruthItems = (summary) => {
  const normalized = normalizeEnterpriseSummary(summary)
  const meta = normalized.summary || {}
  const caps = normalized.capabilities?.summary || {}
  return [
    `数据源 ${normalized.data_source || 'shipment_fact'}`,
    `扫描 ${compactNumber(meta.records_scanned || meta.total_orders || 0)} 条`,
    `预测 ${normalized.prediction?.forecast_status || 'baseline'}`,
    `能力 ${caps.available ?? meta.capability_available ?? 0}/${caps.total ?? meta.capability_total ?? 0}`,
    normalized.fallback_reason ? `降级 ${normalized.fallback_reason}` : null
  ].filter(Boolean)
}

const laneLabel = (lane) => lane?.lane || `${lane?.origin_city || '未知'} -> ${lane?.destination_city || '未知'}`

const riskLevelFromScore = (score) => {
  if (score >= 0.75) return 'critical'
  if (score >= 0.55) return 'high'
  if (score >= 0.3) return 'medium'
  return 'low'
}

const statusFromRisk = (score) => {
  if (score >= 0.65) return 'heavy'
  if (score >= 0.35) return 'moderate'
  return 'light'
}

export const laneRiskScore = (lane, summary) => {
  const meta = normalizeEnterpriseSummary(summary).summary || {}
  const exceptionRate = toNumber(meta.exception_rate)
  const onTimePenalty = lane?.on_time_rate == null ? 0.18 : Math.max(0, 1 - toNumber(lane.on_time_rate))
  const concentration = Math.min(0.4, toNumber(lane?.freight_share) * 1.6)
  const transitPenalty = lane?.avg_transit_hours ? Math.min(0.25, toNumber(lane.avg_transit_hours) / 240) : 0.08
  return Math.min(0.98, Math.max(0.02, exceptionRate + onTimePenalty + concentration + transitPenalty))
}

export const buildDataAnalyticsModel = (rawSummary) => {
  const summary = normalizeEnterpriseSummary(rawSummary)
  const meta = summary.summary || {}
  const lanes = summary.top_lanes || []
  const cities = summary.city_breakdown || []
  const topCityTotal = Math.max(...cities.map(item => toNumber(item.shipment_count)), 1)
  const totalOrders = toNumber(meta.total_orders || meta.shipment_facts_total)
  const totalCost = toNumber(meta.total_cost || meta.total_freight)
  const carbonEstimate = round(toNumber(summary.kpis?.total_weight_kg) * 0.00012 || totalOrders * 0.7, 1)

  const predictions = lanes.slice(0, 8).map((lane, index) => {
    const risk = laneRiskScore(lane, summary)
    return {
      route_id: lane.lane || index,
      route_name: laneLabel(lane),
      current_status: statusFromRisk(risk),
      congestion_probability: risk,
      recommendation: lane.on_time_rate == null
        ? '缺少完整 ETA 记录，建议补齐时间戳后再做深度时效建模'
        : `准时率 ${asPercent(lane.on_time_rate)}%，建议做 provider 路径校验与运力冗余评估`
    }
  })

  const profiles = cities.slice(0, 10).map((city, index) => {
    const volumeShare = toNumber(city.shipment_count) / topCityTotal
    const revenue = toNumber(city.total_freight)
    const valueLevel = volumeShare > 0.65 ? 'high' : volumeShare > 0.3 ? 'medium' : 'low'
    return {
      customer_id: city.city || index,
      customer_name: `${city.city || '未知城市'} 客群`,
      value_level: valueLevel,
      total_orders: city.shipment_count || 0,
      total_revenue: round(revenue, 2),
      satisfaction_score: Math.max(0.5, Math.min(0.99, 1 - toNumber(meta.exception_rate) - 0.08)),
      recommendations: [
        `入库 ${city.inbound_count || 0} / 出库 ${city.outbound_count || 0}`,
        `运费 ${currencyText(revenue)}`
      ]
    }
  })

  const valueDistribution = profiles.reduce((acc, item) => {
    acc[item.value_level] = (acc[item.value_level] || 0) + 1
    return acc
  }, { high: 0, medium: 0, low: 0 })

  const supplyNodes = cities.slice(0, 8).map((city, index) => ({
    id: city.city || index,
    name: city.city || '未知城市',
    type: city.outbound_count >= city.inbound_count ? 'warehouse' : 'distribution',
    status: laneRiskScore(lanes[index] || {}, summary) > 0.55 ? 'watch' : 'active',
    performance: Math.max(0.45, Math.min(0.99, 1 - laneRiskScore(lanes[index] || {}, summary)))
  }))

  return {
    dashboard: {
      predictive_maintenance: {
        high_risk_count: predictions.filter(item => item.congestion_probability >= 0.55).length,
        predictions
      },
      customer_analysis: {
        high_value_count: valueDistribution.high,
        total_customers: cities.length,
        avg_satisfaction: profiles.length
          ? profiles.reduce((sum, item) => sum + item.satisfaction_score, 0) / profiles.length
          : 0
      },
      supply_chain: {
        fulfillment_rate: asPercent(meta.completion_rate),
        on_time_delivery: toNumber(meta.on_time_rate),
        bottleneck_nodes: predictions
          .filter(item => item.congestion_probability >= 0.55)
          .slice(0, 3)
          .map(item => item.route_name)
      },
      carbon_footprint: {
        total_emission_kg: carbonEstimate,
        potential_saving_kg: round(carbonEstimate * 0.08, 1),
        avg_emission_per_order: totalOrders ? round(carbonEstimate / totalOrders, 4) : 0
      }
    },
    trafficPredictions: predictions,
    customerData: {
      profiles,
      value_distribution: valueDistribution,
      summary: { total_customers: cities.length, high_value_count: valueDistribution.high }
    },
    supplyChainData: {
      chain: {
        nodes: supplyNodes,
        connections: lanes.slice(0, 8)
      },
      metrics: {
        fulfillment_rate: asPercent(meta.completion_rate),
        on_time_delivery: toNumber(meta.on_time_rate),
        avg_lead_time: round(toNumber(summary.kpis?.avg_transit_hours) / 24, 1),
        total_nodes: cities.length
      }
    },
    carbonReport: {
      summary: {
        total_emission_kg: carbonEstimate,
        potential_saving_kg: round(carbonEstimate * 0.08, 1),
        avg_emission_per_order: totalOrders ? round(carbonEstimate / totalOrders, 4) : 0,
        total_cost_yuan: round(totalCost, 2)
      }
    }
  }
}

export const buildRiskModel = (rawSummary) => {
  const summary = normalizeEnterpriseSummary(rawSummary)
  const meta = summary.summary || {}
  const lanes = summary.top_lanes || []
  const items = lanes.slice(0, 20).map((lane, index) => {
    const risk = laneRiskScore(lane, summary)
    const impact = Math.min(100, Math.max(5, round(toNumber(lane.freight_share) * 100 || toNumber(lane.total_freight) / Math.max(toNumber(meta.total_cost), 1) * 100, 0)))
    const category = risk >= 0.55 && impact >= 35
      ? 'strategic'
      : risk < 0.55 && impact >= 35
        ? 'leverage'
        : risk >= 0.55
          ? 'bottleneck'
          : 'routine'
    return {
      item_id: lane.lane || index,
      item_name: laneLabel(lane),
      profit_impact: impact,
      supply_risk: asPercent(risk),
      category,
      color: category === 'strategic' ? '#ff6b6b' : category === 'leverage' ? '#00d4ff' : category === 'bottleneck' ? '#ffd93d' : '#00ff88',
      source: 'shipment_fact_top_lane'
    }
  })

  const stats = items.reduce((acc, item) => {
    acc[item.category] = (acc[item.category] || 0) + 1
    if (item.supply_risk >= 55) acc.high_risk_count += 1
    acc.avg_profit_impact += item.profit_impact
    acc.avg_supply_risk += item.supply_risk
    return acc
  }, { total: items.length, strategic: 0, leverage: 0, bottleneck: 0, routine: 0, high_risk_count: 0, avg_profit_impact: 0, avg_supply_risk: 0 })
  if (items.length) {
    stats.avg_profit_impact = round(stats.avg_profit_impact / items.length, 0)
    stats.avg_supply_risk = round(stats.avg_supply_risk / items.length, 0)
  }

  const matrix = Array.from({ length: 5 }, () => Array.from({ length: 5 }, () => 0))
  const riskItems = items.map((item, index) => {
    const probability = Math.min(4, Math.max(0, Math.floor(item.supply_risk / 20)))
    const impact = Math.min(4, Math.max(0, Math.floor(item.profit_impact / 20)))
    matrix[4 - impact][probability] += 1
    const score = (item.supply_risk / 100) * (item.profit_impact / 100)
    return {
      id: item.item_id || index,
      name: item.item_name,
      score,
      level: riskLevelFromScore(score),
      source: item.source
    }
  })

  return {
    kraljicStats: stats,
    kraljicItems: items,
    riskMatrixData: matrix,
    riskItems,
    crisisZones: [],
    anomalySummary: summary.anomaly?.summary || {}
  }
}

export const cityCoord = (city) => CITY_COORDS[city] || null

export const buildDataScreenModel = (rawSummary) => {
  const summary = normalizeEnterpriseSummary(rawSummary)
  const meta = summary.summary || {}
  const trend = summary.trend || []
  const lanes = summary.top_lanes || []
  const cities = summary.city_breakdown || []
  const latestTrend = trend.filter(item => toNumber(item.shipment_count) > 0).at(-1) || trend.at(-1) || {}
  const totalOrders = toNumber(meta.total_orders || meta.shipment_facts_total)
  const completed = Math.round(totalOrders * toNumber(meta.completion_rate))
  const transit = Math.max(0, totalOrders - completed - toNumber(meta.anomaly_count))
  const estimatedVehicles = Math.max(2, Math.ceil(toNumber(latestTrend.shipment_count || totalOrders / 30) / 25))
  const cityNodes = cities
    .map(city => ({ ...city, coord: cityCoord(city.city) }))
    .filter(city => city.coord)

  return {
    targetData: {
      totalOrders,
      todayOrders: toNumber(latestTrend.shipment_count),
      transitOrders: transit,
      completedOrders: completed,
      totalVehicles: estimatedVehicles,
      nodes: cities.length,
      routes: lanes.length,
      activeVehicles: Math.max(1, Math.ceil(estimatedVehicles * 0.65)),
      totalCost: Math.round(toNumber(meta.total_cost || meta.total_freight)),
      savedCost: Math.round(toNumber(meta.total_cost || meta.total_freight) * 0.052)
    },
    vehicleStatus: {
      running: Math.max(1, Math.ceil(estimatedVehicles * 0.6)),
      idle: Math.max(0, Math.floor(estimatedVehicles * 0.3)),
      maintenance: Math.max(0, estimatedVehicles - Math.ceil(estimatedVehicles * 0.6) - Math.floor(estimatedVehicles * 0.3))
    },
    alerts: [
      ...((summary.recommendations || []).slice(0, 3).map((message, index) => ({
        level: index === 0 ? 'warning' : 'info',
        message,
        time: '真实摘要'
      }))),
      ...(toNumber(meta.high_risk_count) > 0 ? [{
        level: 'warning',
        message: `检测到 ${meta.high_risk_count} 个高风险信号，建议进入风险管理页面复核`,
        time: '真实异常'
      }] : [])
    ],
    scrollMessages: [
      `真实 shipment_facts 已扫描 ${compactNumber(meta.records_scanned || totalOrders)} 条`,
      `Top 线路 ${lanes[0]?.lane || '待补充'}，运费 ${currencyText(lanes[0]?.total_freight || 0)}`,
      `预测粒度 ${summary.prediction?.time_granularity || 'auto'}，状态 ${summary.prediction?.forecast_status || 'baseline'}`,
      `优化运行时能力 ${summary.capabilities?.summary?.available || 0}/${summary.capabilities?.summary?.total || 0} 可用`,
      summary.truth_contract?.rl_boundary || 'RL policy 当前保持 shadow rerank，不直接写业务状态'
    ],
    orderTrend: trend,
    costTrend: trend,
    cityNodes,
    laneRoutes: lanes
      .map(lane => ({
        from: cityCoord(lane.origin_city),
        to: cityCoord(lane.destination_city),
        value: lane.shipment_count || 0
      }))
      .filter(route => route.from && route.to)
  }
}

export const buildBigDataModel = (rawSummary) => {
  const summary = normalizeEnterpriseSummary(rawSummary)
  const meta = summary.summary || {}
  const predictions = summary.prediction?.predictions || summary.prediction?.forecast || []
  const cities = summary.city_breakdown || []
  const lanes = summary.top_lanes || []
  const latestTrend = (summary.trend || []).filter(item => toNumber(item.shipment_count) > 0).at(-1) || {}
  const estimatedVehicles = Math.max(2, Math.ceil(toNumber(latestTrend.shipment_count || meta.total_orders / 30) / 25))

  return {
    stats: {
      totalOrders: toNumber(meta.total_orders || meta.shipment_facts_total),
      todayOrders: toNumber(latestTrend.shipment_count),
      totalVehicles: estimatedVehicles,
      totalCost: round(meta.total_cost || meta.total_freight, 2)
    },
    chartData: {
      orders: {
        status_distribution: {
          pending: toNumber(meta.anomaly_count),
          in_transit: Math.max(0, toNumber(meta.total_orders) - Math.round(toNumber(meta.total_orders) * toNumber(meta.completion_rate))),
          delivered: Math.round(toNumber(meta.total_orders) * toNumber(meta.completion_rate))
        },
        weekly_trend: summary.trend || []
      },
      vehicles: {
        status_distribution: {
          in_use: Math.ceil(estimatedVehicles * 0.6),
          available: Math.floor(estimatedVehicles * 0.3),
          maintenance: Math.max(0, estimatedVehicles - Math.ceil(estimatedVehicles * 0.6) - Math.floor(estimatedVehicles * 0.3))
        }
      }
    },
    demandPredictions: (predictions.length ? predictions : cities).slice(0, 5).map((item, index) => {
      const demand = toNumber(item.value || item.predicted_orders || item.shipment_count)
      return {
        region: item.city || item.date || item.bucket_start || `T+${index + 1}`,
        avg_demand: Math.round(demand),
        status: demand > 150 ? 'high' : demand > 50 ? 'medium' : 'normal'
      }
    }),
    vehicleSuggestions: cities.slice(0, 5).map(city => ({
      region: city.city,
      vehicles_suggested: Math.max(1, Math.ceil(toNumber(city.shipment_count) / 25)),
      note: `基于 ${city.shipment_count || 0} 条城市运单估算`
    })),
    bottlenecks: lanes.slice(0, 5).map((lane, index) => ({
      id: lane.lane || index,
      name: laneLabel(lane),
      score: laneRiskScore(lane, summary),
      utilization: Math.min(0.99, Math.max(0.2, toNumber(lane.freight_share) * 2 || 0.35))
    }))
  }
}
