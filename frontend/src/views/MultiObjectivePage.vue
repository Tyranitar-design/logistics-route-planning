<template>
  <div class="multi-objective-page">
    <div class="page-header">
      <span class="page-kicker">Decision Center</span>
      <h1>🎯 多目标路径优化</h1>
      <p class="subtitle">把推荐结论、真实性、质量看板、权衡分析和路线预览放进同一条可读的企业级决策链。</p>
    </div>

    <div class="main-content">
      <div class="left-panel">
        <el-card class="location-card">
          <template #header>
            <div class="card-header">
              <span>📍 起终点选择</span>
            </div>
          </template>

          <el-form label-width="60px">
            <el-form-item label="起点">
              <el-select
                v-model="originId"
                placeholder="选择起点"
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="node in nodes"
                  :key="node.id"
                  :label="node.name"
                  :value="node.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="终点">
              <el-select
                v-model="destinationId"
                placeholder="选择终点"
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="node in nodes"
                  :key="node.id"
                  :label="node.name"
                  :value="node.id"
                />
              </el-select>
            </el-form-item>
          </el-form>
        </el-card>

        <MultiObjectivePanel
          :origin-id="originId"
          :destination-id="destinationId"
          @result="handleResult"
          @select="handleSelectRoute"
        />
      </div>

      <div class="right-panel">
        <el-card v-if="result" class="decision-shell">
          <div class="decision-shell__top">
            <div class="decision-top-card decision-top-card--primary">
              <span class="decision-label">当前决策状态</span>
              <strong>{{ selectedRoute?.title || result.recommendation?.recommended_solver || '结果已生成' }}</strong>
              <p>{{ selectedRoute?.recommendation_reason || selectedRoute?.description || result.recommendation?.reason || '请选择一个方案查看路线与目标权衡。' }}</p>
            </div>
            <div class="decision-top-card">
              <span class="decision-label">候选方案</span>
              <strong>{{ result.candidate_generation?.candidate_count || decisionSolutions.length }}</strong>
              <small>{{ candidateSourceText(result) }}</small>
            </div>
            <div class="decision-top-card">
              <span class="decision-label">真实性</span>
              <strong>{{ result.authenticity_level || result.authenticity?.level || result.distance_precision?.level || '未标注' }}</strong>
              <small>{{ truthSourceText(result) }}</small>
            </div>
            <div class="decision-top-card">
              <span class="decision-label">前沿质量</span>
              <strong>{{ frontQualityLabel(result.front_quality || result.pareto_summary?.front_quality) }}</strong>
              <small>{{ selectedRoute?.selection_metrics?.route_strategy || result.candidate_generation?.strategies?.[0] || '候选路线权衡' }}</small>
            </div>
          </div>

          <div class="decision-stack">
            <SolverRecommendationCard
              v-if="result.recommendation"
              :recommendation="result.recommendation"
            />

            <DistancePrecisionCard
              v-if="result.distance_precision"
              :distance-precision="result.distance_precision"
              :source-summary="result.source_summary"
              :distance-metadata="result.distance_metadata"
            />

            <QualityReportPanel
              v-if="result.quality_report"
              :report="result.quality_report"
            />

            <div class="analysis-grid" v-if="decisionSolutions.length">
              <ParetoScatterPlot
                :solutions="decisionSolutions"
                :front-quality="result.front_quality || result.pareto_summary?.front_quality"
                :reported-front-count="result.pareto_front_size || result.pareto_front?.length || decisionSolutions.length"
                @solution-click="handleRecommendationChartSelect"
              />

              <ParallelCoordinatesChart
                :solutions="decisionSolutions"
              />
            </div>

            <RouteCompareChart
              :routes="decisionSolutions"
              :selected-indices="selectedIndices"
            />
          </div>
        </el-card>

        <el-empty v-else description="请选择起终点并开始优化" />
      </div>
    </div>

    <div v-if="selectedRoute" class="map-preview">
      <el-card class="map-card">
        <template #header>
          <div class="map-card__header">
            <div>
              <span class="page-kicker">Route Preview</span>
              <h3>🗺️ 路线预览</h3>
            </div>
            <el-tag type="info" effect="plain">
              {{ selectedRoute.title || '当前选中方案' }}
            </el-tag>
          </div>
        </template>
        <div ref="mapRef" class="map-container"></div>
        <el-alert
          v-if="mapPreviewState.reason"
          class="map-preview-alert"
          type="warning"
          :closable="false"
          show-icon
          :title="mapPreviewState.title"
          :description="mapPreviewState.description"
        />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import MultiObjectivePanel from '../components/MultiObjectivePanel.vue'
import RouteCompareChart from '../components/RouteCompareChart.vue'
import SolverRecommendationCard from '../components/SolverRecommendationCard.vue'
import DistancePrecisionCard from '../components/DistancePrecisionCard.vue'
import QualityReportPanel from '../components/QualityReportPanel.vue'
import ParetoScatterPlot from '../components/ParetoScatterPlot.vue'
import ParallelCoordinatesChart from '../components/ParallelCoordinatesChart.vue'
import { getAllNodes } from '../api/nodes'
import { buildRoutePreviewGeometry, buildRoutePreviewGeometryForRoute } from '../utils/routePreview'
import { buildDecisionSolutions } from '../utils/multiObjectiveDisplay'
import * as echarts from 'echarts'

const nodes = ref([])
const originId = ref(null)
const destinationId = ref(null)
const result = ref(null)
const decisionSolutions = ref([])
const selectedRoute = ref(null)
const selectedIndices = ref([])
const mapRef = ref(null)
const mapPreviewState = ref({
  reason: null,
  title: '',
  description: ''
})
let mapChart = null
let chinaMapPromise = null

async function fetchNodes() {
  try {
    const res = await getAllNodes()
    nodes.value = res.nodes || []
    if (selectedRoute.value && mapPreviewState.value.reason === 'INSUFFICIENT_ROUTE_POINTS') {
      nextTick(() => renderMap(selectedRoute.value))
    }
  } catch (error) {
    console.error('获取节点失败:', error)
  }
}

function handleResult(res) {
  result.value = res
  decisionSolutions.value = buildDecisionSolutions(res)
  selectedIndices.value = []
  if (decisionSolutions.value.length) {
    selectedRoute.value = decisionSolutions.value[0]
    selectedIndices.value = [0]
    nextTick(() => renderMap(selectedRoute.value))
  }
}

function handleRecommendationChartSelect(solution, index) {
  const exactIndex = decisionSolutions.value.findIndex(item => item === solution)
  const selectedIndex = exactIndex >= 0 ? exactIndex : index

  if (decisionSolutions.value?.[selectedIndex]) {
    selectedRoute.value = decisionSolutions.value[selectedIndex]
    selectedIndices.value = [selectedIndex]
    nextTick(() => renderMap(selectedRoute.value))
  }
}

function handleSelectRoute(route) {
  selectedRoute.value = route
  if (decisionSolutions.value?.length) {
    const idx = decisionSolutions.value.findIndex(item => item === route)
    selectedIndices.value = idx >= 0 ? [idx] : []
  }
  nextTick(() => renderMap(route))
}

async function renderMap(route) {
  if (!mapRef.value) return

  const geometry = buildPreviewGeometry(route)

  if (!geometry.valid) {
    if (mapChart) {
      mapChart.dispose()
      mapChart = null
    }

    mapPreviewState.value = {
      reason: geometry.reason,
      title: geometry.reason === 'NODE_COORDINATES_MISSING' ? '路线预览已降级' : '路线预览数据不足',
      description: geometry.reason === 'NODE_COORDINATES_MISSING'
        ? `以下节点缺少真实经纬度，系统已停止绘制误导性路线：${geometry.invalidNodes.map(node => node.name).join('、')}`
        : '当前方案缺少足够的有效坐标点，暂不绘制路线。'
    }
    return
  }

  if (mapChart) {
    mapChart.dispose()
  }

  try {
    await ensureChinaMap()
  } catch (error) {
    console.error('加载中国地图失败:', error)
    mapPreviewState.value = {
      reason: 'MAP_RESOURCE_UNAVAILABLE',
      title: '地图资源不可用',
      description: '路线已有可用坐标，但中国地图底图加载失败，暂不绘制避免误导。'
    }
    return
  }

  mapChart = echarts.init(mapRef.value)
  mapPreviewState.value = {
    reason: null,
    title: '',
    description: ''
  }

  const pathCoords = geometry.lineCoords

  const option = {
    backgroundColor: 'transparent',
    geo: {
      map: 'china',
      roam: true,
      zoom: 5,
      center: pathCoords[0] || [116.4, 39.9],
      itemStyle: {
        areaColor: '#10233d',
        borderColor: 'rgba(0, 212, 255, 0.26)'
      },
      emphasis: {
        itemStyle: {
          areaColor: '#16304f'
        }
      }
    },
    series: [
      {
        type: 'lines',
        coordinateSystem: 'geo',
        data: [{
          coords: pathCoords,
          lineStyle: {
            color: '#00d4ff',
            width: 3,
            curveness: 0.2
          }
        }],
        effect: {
          show: true,
          period: 4,
          trailLength: 0.2,
          color: '#ff7f8f',
          symbolSize: 8
        }
      },
      {
        type: 'scatter',
        coordinateSystem: 'geo',
        data: geometry.points.map((point, i) => ({
          name: point.name || `节点${i + 1}`,
          value: point.coord,
          itemStyle: {
            color: i === 0 ? '#11e0b7' : (i === pathCoords.length - 1 ? '#ff5b6e' : '#00d4ff')
          }
        })),
        symbolSize: 12,
        label: {
          show: true,
          position: 'right',
          color: '#ecf7ff',
          formatter: '{b}'
        }
      }
    ]
  }

  mapChart.setOption(option)

  if (geometry.reason === 'ENDPOINT_PROJECTION') {
    mapPreviewState.value = {
      reason: geometry.reason,
      title: '路线预览为端点投影',
      description: '当前推荐结果未携带完整可验证路径坐标，页面仅使用真实起终点坐标绘制连线，不能解读为真实导航轨迹。'
    }
  }
}

function ensureChinaMap() {
  if (!chinaMapPromise) {
    chinaMapPromise = fetch('/china.json')
      .then(response => {
        if (!response.ok) throw new Error(`china.json ${response.status}`)
        return response.json()
      })
      .then(chinaJson => {
        echarts.registerMap('china', chinaJson)
        return true
      })
  }

  return chinaMapPromise
}

function buildPreviewGeometry(route) {
  const pathGeometry = buildRoutePreviewGeometryForRoute(route || {})
  if (pathGeometry.valid) return pathGeometry

  const originNode = nodes.value.find(node => String(node.id) === String(originId.value))
  const destinationNode = nodes.value.find(node => String(node.id) === String(destinationId.value))
  const endpointGeometry = buildRoutePreviewGeometry([originNode, destinationNode])

  if (endpointGeometry.valid) {
    return {
      ...endpointGeometry,
      reason: 'ENDPOINT_PROJECTION'
    }
  }

  return pathGeometry
}

function candidateSourceText(payload = {}) {
  const counts = payload.candidate_generation?.source_counts || {}
  const labels = {
    amap_multi_route: 'AMap 多路线',
    amap_strategy_route: 'AMap 策略补充',
    specified_origin_destination: '指定起终点投影'
  }
  const parts = Object.entries(counts)
    .filter(([, value]) => Number(value) > 0)
    .map(([key, value]) => `${labels[key] || key} ${value}`)

  if (parts.length) return parts.join(' / ')
  if (payload.candidate_generation?.candidate_count) return '真实候选路线池'
  return '个可对比方案'
}

function truthSourceText(payload = {}) {
  const distanceSource = payload.distance_source || payload.distance_precision?.source || '-'
  const pathSource = payload.path_source || '-'
  const fallbackReason = payload.fallback_reason || payload.authenticity?.fallback_reason
  if (fallbackReason) return `${distanceSource} / ${pathSource} · 降级 ${fallbackReason}`
  return `${distanceSource} / ${pathSource}`
}

function frontQualityLabel(value) {
  const labels = {
    reported_front: '真实前沿',
    degenerate_front: '退化前沿',
    single_solution_projection: '单解投影',
    empty_front: '空前沿'
  }
  return labels[value] || value || '未标注'
}

onMounted(() => {
  fetchNodes()
})
</script>

<style scoped>
.multi-objective-page {
  padding: 20px;
  background: linear-gradient(180deg, #091322 0%, #0c1830 100%);
  min-height: calc(100vh - 60px);
  color: #ecf7ff;
}

.page-header {
  margin-bottom: 20px;
}

.page-kicker {
  display: inline-block;
  font-size: 11px;
  color: rgba(236, 247, 255, 0.54);
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: #ffffff;
  margin: 6px 0 8px 0;
}

.subtitle {
  color: rgba(236, 247, 255, 0.7);
  margin: 0;
  line-height: 1.7;
}

.main-content {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.location-card {
  margin-bottom: 0;
  border-radius: 18px;
  background: rgba(8, 19, 34, 0.94);
  border: 1px solid rgba(0, 212, 255, 0.12);
}

.card-header,
.map-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.right-panel {
  min-height: 500px;
}

.decision-shell {
  border-radius: 18px;
  background: rgba(8, 19, 34, 0.94);
  border: 1px solid rgba(0, 212, 255, 0.12);
}

.decision-shell__top {
  display: grid;
  grid-template-columns: 1.2fr repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.decision-top-card {
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.decision-top-card--primary {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.14), rgba(17, 224, 183, 0.08));
  border-color: rgba(0, 212, 255, 0.18);
}

.decision-label {
  font-size: 12px;
  color: rgba(236, 247, 255, 0.54);
}

.decision-top-card strong {
  font-size: 18px;
  color: #ffffff;
}

.decision-top-card p,
.decision-top-card small {
  margin: 0;
  line-height: 1.7;
  color: rgba(236, 247, 255, 0.72);
}

.decision-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.analysis-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.map-preview {
  margin-top: 20px;
}

.map-card {
  border-radius: 18px;
  background: rgba(8, 19, 34, 0.94);
  border: 1px solid rgba(0, 212, 255, 0.12);
}

.map-card__header h3 {
  margin: 6px 0 0;
  color: #ffffff;
}

.map-container {
  width: 100%;
  height: 420px;
}

.map-preview-alert {
  margin-top: 14px;
}

@media (max-width: 1200px) {
  .main-content,
  .decision-shell__top {
    grid-template-columns: 1fr;
  }
}
</style>
