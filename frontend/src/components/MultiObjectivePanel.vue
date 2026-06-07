<template>
  <div class="multi-objective-panel">
    <section class="weights-section">
      <div class="section-header">
        <h3>🎯 优化目标权重</h3>
        <el-button type="primary" size="small" text @click="resetWeights">
          重置
        </el-button>
      </div>

      <div class="weights-grid">
        <WeightSlider
          v-for="obj in objectives"
          :key="obj.name"
          :objective="obj.name"
          :title="obj.display_name"
          :unit="obj.unit"
          v-model="weights[obj.name]"
          @change="handleWeightChange"
        />
      </div>

      <div class="weights-summary">
        <span>权重总计:</span>
        <el-tag :type="totalWeightValid ? 'success' : 'danger'">
          {{ totalWeight }}%
        </el-tag>
        <span v-if="!totalWeightValid" class="weight-warning">(请调整至100%)</span>
      </div>
    </section>

    <section class="algorithm-section">
      <h3>⚙️ 优化算法</h3>
      <el-radio-group v-model="algorithm" size="small">
        <el-radio-button value="all">智能推荐</el-radio-button>
        <el-radio-button value="weighted_sum">加权最优</el-radio-button>
        <el-radio-button value="pareto">Pareto前沿</el-radio-button>
        <el-radio-button value="nsga2">NSGA-II</el-radio-button>
        <el-radio-button value="nsga3">NSGA-III</el-radio-button>
      </el-radio-group>

      <div v-if="algorithm === 'nsga2' || algorithm === 'nsga3'" class="algo-extra">
        <el-form-item label="迭代次数" size="small">
          <el-input-number v-model="nGen" :min="50" :max="300" :step="50" size="small" />
        </el-form-item>
      </div>
    </section>

    <section class="action-section">
      <el-button
        type="primary"
        size="large"
        :loading="loading"
        :disabled="!canOptimize"
        @click="startOptimize"
      >
        <el-icon><Promotion /></el-icon>
        开始优化
      </el-button>
    </section>

    <section v-if="result" class="result-section">
      <div class="section-header">
        <h3>📊 优化结果</h3>
        <el-tag type="success" effect="dark">
          {{ algorithm === 'nsga2' || algorithm === 'nsga3' ? '真实 Pareto 求解' : '推荐结果已生成' }}
        </el-tag>
      </div>

      <div v-if="algorithm === 'nsga2' || algorithm === 'nsga3'" class="result-overview result-overview--nsga">
        <div class="overview-card overview-card--primary">
          <span class="overview-label">问题上下文</span>
          <strong>{{ result.depot?.name || '默认仓库' }}</strong>
          <p>
            待配送订单 {{ result.n_orders || 0 }} 个 · 配送点 {{ result.n_customers || 0 }} 个 · 可用车辆 {{ result.n_vehicles || 0 }} 辆
          </p>
        </div>
        <div class="overview-card">
          <span class="overview-label">总距离</span>
          <strong>{{ nsgaObjectives[0]?.toFixed(1) || '-' }}</strong>
          <small>km</small>
        </div>
        <div class="overview-card">
          <span class="overview-label">总时间</span>
          <strong>{{ nsgaObjectives[1]?.toFixed(1) || '-' }}</strong>
          <small>min</small>
        </div>
        <div class="overview-card">
          <span class="overview-label">车辆数</span>
          <strong>{{ Math.round(nsgaObjectives[2] || 0) }}</strong>
          <small>条路线</small>
        </div>
      </div>

      <div v-else class="result-overview">
        <div class="overview-card overview-card--primary">
          <span class="overview-label">当前选中方案</span>
          <strong>{{ selectedRecommendationDetail?.title || '待选择' }}</strong>
          <p>{{ selectedRecommendationDetail?.description || '请从候选方案中选择一个重点查看。' }}</p>
        </div>
        <div class="overview-card">
          <span class="overview-label">候选方案数</span>
          <strong>{{ result.recommendations?.length || 0 }}</strong>
          <small>个</small>
        </div>
        <div class="overview-card">
          <span class="overview-label">距离</span>
          <strong>{{ selectedRecommendationDetail ? formatObjectiveMetric('distance', selectedRecommendationDetail.objectives?.distance) : '-' }}</strong>
        </div>
        <div class="overview-card">
          <span class="overview-label">时间</span>
          <strong>{{ selectedRecommendationDetail ? formatObjectiveMetric('time', selectedRecommendationDetail.objectives?.time) : '-' }}</strong>
        </div>
      </div>

      <div v-if="algorithm === 'nsga2' || algorithm === 'nsga3'" class="nsga-visual-block">
        <el-alert type="success" :closable="false" class="nsga-alert">
          <template #title>📍 基于选定起终点的本地数据库优化</template>
          <div style="font-size: 12px; line-height: 1.8;">
            <div>
              <strong>起点(仓库):</strong> {{ result.depot?.name || '默认' }} |
              <strong>待配送订单:</strong> {{ result.n_orders || 0 }} 个 |
              <strong>配送点:</strong> {{ result.n_customers || 0 }} 个 |
              <strong>可用车辆:</strong> {{ result.n_vehicles || 0 }} 辆
            </div>
            <div v-if="result.n_orders === 0 && result.n_customers > 0" class="nsga-warning">
              ⚠️ 没有待配送订单，已使用节点数据进行优化
            </div>
          </div>
        </el-alert>

        <div v-if="result.order_info?.length" class="order-info-tags">
          <el-tag
            v-for="order in result.order_info.slice(0, 6)"
            :key="order.id"
            size="small"
            style="margin: 2px;"
          >
            {{ order.node_name || order.order_number }}
          </el-tag>
          <span v-if="result.order_info.length > 6" class="more-text">+{{ result.order_info.length - 6 }} 更多...</span>
        </div>

        <div class="pareto-section" v-if="paretoSolutions.length > 0">
          <div class="section-header">
            <h3>📈 Pareto 前沿 - 非支配解集</h3>
            <el-radio-group v-model="displayMode" size="small">
              <el-radio-button value="3d">3D</el-radio-button>
              <el-radio-button value="2d">2D</el-radio-button>
            </el-radio-group>
          </div>
          <el-alert
            :type="nsgaParetoMeta.alertType"
            :closable="false"
            class="pareto-quality-alert"
          >
            <template #title>前沿质量：{{ nsgaParetoMeta.label }}</template>
            <div>{{ nsgaParetoMeta.message }}</div>
          </el-alert>
          <div ref="paretoChartRef" class="pareto-chart"></div>
          <div class="pareto-summary-text">
            共 {{ paretoSolutions.length }} 个{{ nsgaParetoMeta.isProjection ? '代表性解' : '非支配解' }}
          </div>
        </div>

        <div class="routes-list">
          <div v-for="(route, i) in nsgaRoutes" :key="i" class="route-item">
            <span class="route-label">路线 {{ i + 1 }}:</span>
            <span class="route-path">{{ route.join(' → ') }}</span>
          </div>
        </div>
      </div>

      <div v-else class="recommendation-flow">
        <div class="section-header">
          <h3>🧭 当前选中方案解读</h3>
        </div>

        <div v-if="selectedRecommendationDetail" class="selected-recommendation-card">
          <div class="selected-header">
            <div>
              <span class="selected-kicker">{{ getTypeLabel(selectedRecommendationDetail.type) }}</span>
              <h4>{{ selectedRecommendationDetail.title }}</h4>
            </div>
          </div>
          <p class="selected-desc">{{ selectedRecommendationDetail.description }}</p>
          <div v-if="recommendationReasonFor(selectedRecommendationDetail)" class="explanation-block">
            <span class="explanation-label">推荐理由</span>
            <p>{{ recommendationReasonFor(selectedRecommendationDetail) }}</p>
          </div>
          <div v-if="hasTradeoffSummary(selectedRecommendationDetail)" class="tradeoff-summary">
            <div v-if="tradeoffStrengthsFor(selectedRecommendationDetail).length" class="tradeoff-column">
              <span class="tradeoff-label">优势</span>
              <span
                v-for="item in tradeoffStrengthsFor(selectedRecommendationDetail)"
                :key="item"
                class="tradeoff-pill tradeoff-pill--strong"
              >
                {{ item }}
              </span>
            </div>
            <div v-if="tradeoffCompromisesFor(selectedRecommendationDetail).length" class="tradeoff-column">
              <span class="tradeoff-label">取舍</span>
              <span
                v-for="item in tradeoffCompromisesFor(selectedRecommendationDetail)"
                :key="item"
                class="tradeoff-pill tradeoff-pill--soft"
              >
                {{ item }}
              </span>
            </div>
          </div>
          <div v-if="hasSelectionMetrics(selectedRecommendationDetail)" class="selection-metrics">
            <span>候选 {{ selectionMetricsFor(selectedRecommendationDetail).candidate_count || '-' }}</span>
            <span>前沿 {{ frontQualityLabel(selectionMetricsFor(selectedRecommendationDetail).front_quality) }}</span>
            <span v-if="selectionMetricsFor(selectedRecommendationDetail).route_strategy">
              策略 {{ selectionMetricsFor(selectedRecommendationDetail).route_strategy }}
            </span>
          </div>
          <div class="selected-objectives">
            <span
              v-for="(value, key) in selectedRecommendationDetail.objectives"
              :key="key"
              class="obj-tag"
            >
              {{ getObjectiveLabel(key) }}: {{ formatValue(key, value) }}
            </span>
          </div>
          <div v-if="hasTruthFields(selectedRecommendationDetail)" class="truth-tags">
            <span class="truth-tag">真实性: {{ truthLevelFor(selectedRecommendationDetail) }}</span>
            <span class="truth-tag">距离: {{ distanceSourceFor(selectedRecommendationDetail) }}</span>
            <span class="truth-tag">路径: {{ pathSourceFor(selectedRecommendationDetail) }}</span>
            <span v-if="fallbackReasonFor(selectedRecommendationDetail)" class="truth-tag truth-tag--warning">
              降级: {{ fallbackReasonFor(selectedRecommendationDetail) }}
            </span>
          </div>
        </div>

        <div class="recommendation-list">
          <div
            v-for="(rec, index) in result.recommendations"
            :key="index"
            class="recommendation-card"
            :class="{ active: selectedRecommendation === index }"
            @click="selectRecommendation(index)"
          >
            <div class="rec-header">
              <span class="rec-type">{{ getTypeLabel(rec.type) }}</span>
              <span class="rec-title">{{ rec.title }}</span>
            </div>
            <div class="rec-desc">{{ rec.description }}</div>
            <div v-if="recommendationReasonFor(rec)" class="rec-reason">
              {{ recommendationReasonFor(rec) }}
            </div>
            <div v-if="hasTradeoffSummary(rec)" class="rec-tradeoffs">
              <span
                v-for="item in tradeoffStrengthsFor(rec).slice(0, 2)"
                :key="`s-${item}`"
                class="tradeoff-pill tradeoff-pill--strong"
              >
                {{ item }}
              </span>
              <span
                v-for="item in tradeoffCompromisesFor(rec).slice(0, 2)"
                :key="`c-${item}`"
                class="tradeoff-pill tradeoff-pill--soft"
              >
                {{ item }}
              </span>
            </div>
            <div class="rec-objectives">
              <span
                v-for="(value, key) in rec.objectives"
                :key="key"
                class="obj-tag"
              >
                {{ getObjectiveLabel(key) }}: {{ formatValue(key, value) }}
              </span>
            </div>
            <div v-if="hasTruthFields(rec)" class="truth-tags">
              <span class="truth-tag">真实性: {{ truthLevelFor(rec) }}</span>
              <span class="truth-tag">距离: {{ distanceSourceFor(rec) }}</span>
              <span class="truth-tag">路径: {{ pathSourceFor(rec) }}</span>
              <span v-if="fallbackReasonFor(rec)" class="truth-tag truth-tag--warning">
                降级: {{ fallbackReasonFor(rec) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'
import WeightSlider from './WeightSlider.vue'
import { getObjectives, optimizeRoute } from '../api/multiObjective'
import { buildParetoFrontMeta, extractParetoSolutions } from '../utils/paretoTruthMeta'
import axios from 'axios'
import * as echarts from 'echarts'
import 'echarts-gl'

const props = defineProps({
  originId: {
    type: [Number, String],
    default: null
  },
  destinationId: {
    type: [Number, String],
    default: null
  }
})

const emit = defineEmits(['result', 'select'])

const loading = ref(false)
const objectives = ref([])
const weights = ref({})
const algorithm = ref('all')
const result = ref(null)
const selectedRecommendation = ref(0)
const nGen = ref(100)
const paretoFront = ref([])
const nsgaObjectives = ref([])
const nsgaRoutes = ref([])
const paretoChartRef = ref(null)
let paretoChart = null

const demoData = ref(null)
const paretoSolutions = ref([])
const nsgaParetoMeta = ref(buildParetoFrontMeta({}))
const displayMode = ref('3d')

const defaultWeights = {
  distance: 25,
  time: 30,
  cost: 20,
  traffic: 15,
  weather_risk: 10
}

const totalWeight = computed(() => {
  return Object.values(weights.value).reduce((sum, w) => sum + w, 0)
})

const totalWeightValid = computed(() => totalWeight.value === 100)

const canOptimize = computed(() => {
  return props.originId && props.destinationId && totalWeightValid.value
})

const selectedRecommendationDetail = computed(() => {
  return result.value?.recommendations?.[selectedRecommendation.value] || null
})

async function fetchObjectives() {
  try {
    const res = await getObjectives()
    if (res.success) {
      objectives.value = res.objectives
      res.objectives.forEach(obj => {
        weights.value[obj.name] = obj.default_weight * 100
      })
    }
  } catch (error) {
    console.error('获取优化目标失败:', error)
    weights.value = { ...defaultWeights }
  }
}

function resetWeights() {
  weights.value = { ...defaultWeights }
  ElMessage.success('权重已重置')
}

function handleWeightChange() {}

async function startOptimize() {
  if (!canOptimize.value) {
    ElMessage.warning('请先选择起点和终点')
    return
  }

  loading.value = true

  try {
    if (algorithm.value === 'nsga2' || algorithm.value === 'nsga3') {
      await runNsgaOptimize()
      return
    }

    const normalizedWeights = {}
    Object.entries(weights.value).forEach(([key, value]) => {
      normalizedWeights[key] = value / 100
    })

    const requestData = {
      origin_id: Number(props.originId),
      destination_id: Number(props.destinationId),
      weights: normalizedWeights,
      algorithm: algorithm.value
    }

    const res = await optimizeRoute(requestData)

    if (res.success) {
      result.value = res
      selectedRecommendation.value = 0
      emit('result', res)
      ElMessage.success(`优化完成！找到 ${res.recommendations?.length || 0} 个方案`)
    } else {
      ElMessage.error(res.error || '优化失败')
    }
  } catch (error) {
    const errorMsg = error.response?.data?.error || error.response?.data?.message || error.message || '优化失败，请稍后重试'
    ElMessage.error(errorMsg)
  } finally {
    loading.value = false
  }
}

async function runNsgaOptimize() {
  try {
    const solver = algorithm.value === 'nsga2' ? 'pymoo_nsga2' : 'pymoo_nsga3'

    const requestData = {
      origin_id: Number(props.originId),
      destination_id: Number(props.destinationId),
      solver,
      n_gen: nGen.value,
      use_local_data: true
    }

    const res = await axios.post('/api/multi-objective/nsga-optimize', requestData)

    if (res.data.success) {
      nsgaObjectives.value = res.data.objectives || []
      nsgaRoutes.value = res.data.routes || []
      paretoFront.value = res.data.pareto_front || []
      result.value = {
        ...res.data,
        success: true
      }

      generateParetoSolutions(res.data)
      emit('result', result.value)
      ElMessage.success(`NSGA优化完成！使用 ${res.data.n_orders || 0} 个订单，Pareto前沿: ${paretoSolutions.value.length} 个解`)
      nextTick(() => drawParetoChart())
    } else {
      ElMessage.error(res.data.error || 'NSGA优化失败')
    }
  } catch (error) {
    ElMessage.error('NSGA优化出错: ' + (error.response?.data?.error || error.message))
  } finally {
    loading.value = false
  }
}

async function loadDemoData() {
  try {
    const res = await axios.get('/api/optimization/demo')
    demoData.value = res.data
  } catch (e) {
    console.error('加载演示数据失败', e)
  }
}

function generateParetoSolutions(data) {
  paretoSolutions.value = extractParetoSolutions(data)
  nsgaParetoMeta.value = buildParetoFrontMeta(data, paretoSolutions.value)
}

function drawParetoChart() {
  if (!paretoChartRef.value || paretoSolutions.value.length === 0) return

  try {
    if (paretoChart) {
      paretoChart.dispose()
    }
    paretoChart = echarts.init(paretoChartRef.value)

    if (displayMode.value === '3d') {
      draw3DChart()
    } else {
      draw2DChart()
    }
  } catch (e) {
    console.error('图表绘制失败', e)
    if (displayMode.value === '3d') {
      displayMode.value = '2d'
      nextTick(() => drawParetoChart())
    }
  }
}

function draw3DChart() {
  const option = {
    title: {
      text: 'Pareto 前沿 - 三维解集空间',
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'item',
      formatter(params) {
        return `解 #${params.dataIndex + 1}<br/>
                距离: ${params.value[0]?.toFixed(1)} km<br/>
                时间: ${params.value[1]?.toFixed(1)} min<br/>
                车辆: ${Math.round(params.value[2])}`
      }
    },
    visualMap: {
      show: true,
      min: 1,
      max: 5,
      inRange: {
        color: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de']
      },
      dimension: 2,
      seriesIndex: 0
    },
    xAxis3D: {
      type: 'value',
      name: '距离 (km)',
      nameTextStyle: { fontSize: 11 }
    },
    yAxis3D: {
      type: 'value',
      name: '时间 (min)',
      nameTextStyle: { fontSize: 11 }
    },
    zAxis3D: {
      type: 'value',
      name: '车辆数',
      nameTextStyle: { fontSize: 11 }
    },
    grid3D: {
      viewControl: {
        autoRotate: true,
        autoRotateSpeed: 3,
        distance: 180
      }
    },
    series: [
      {
        type: 'scatter3D',
        name: '非支配解',
        data: paretoSolutions.value.map((s, i) => ({
          value: s,
          itemStyle: {
            color: i === 0 ? '#ee6666' : null
          }
        })),
        symbolSize: 16,
        label: {
          show: false
        }
      }
    ]
  }

  paretoChart.setOption(option)
}

function draw2DChart() {
  const option = {
    title: {
      text: 'Pareto 前沿 (距离 vs 时间)',
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'item',
      formatter(params) {
        return `距离: ${params.value[0]?.toFixed(1)} km<br/>
                时间: ${params.value[1]?.toFixed(1)} min<br/>
                车辆: ${Math.round(params.value[2])}`
      }
    },
    xAxis: {
      type: 'value',
      name: '距离 (km)',
      nameTextStyle: { fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: '时间 (min)',
      nameTextStyle: { fontSize: 11 }
    },
    series: [
      {
        name: 'Pareto 前沿',
        type: 'line',
        data: paretoSolutions.value,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { color: '#91cc75', width: 2 },
        itemStyle: { color: '#91cc75' }
      },
      {
        name: '最优解',
        type: 'scatter',
        data: paretoSolutions.value.length ? [paretoSolutions.value[0]] : [],
        symbolSize: 15,
        itemStyle: { color: '#ee6666' },
        label: {
          show: true,
          formatter: '最优解',
          position: 'top',
          color: '#ee6666'
        }
      }
    ]
  }

  paretoChart.setOption(option)
}

function selectRecommendation(index) {
  selectedRecommendation.value = index
  const rec = result.value?.recommendations?.[index]
  if (rec) {
    emit('select', rec)
  }
}

function getTypeLabel(type) {
  const labels = {
    weighted_best: '🏆 综合',
    pareto: '⚖️ 均衡',
    single_objective: '📌 单项'
  }
  return labels[type] || type
}

function getObjectiveLabel(key) {
  const labels = {
    distance: '距离',
    time: '时间',
    cost: '成本',
    traffic: '路况',
    weather_risk: '天气风险'
  }
  return labels[key] || key
}

function formatValue(key, value) {
  const units = {
    distance: 'km',
    time: 'min',
    cost: '元',
    traffic: '分',
    weather_risk: '%'
  }
  return `${value.toFixed(1)}${units[key] || ''}`
}

function formatObjectiveMetric(key, value) {
  if (value == null) return '-'
  const units = {
    distance: ' km',
    time: ' min',
    cost: ' 元',
    traffic: ' 分',
    weather_risk: '%'
  }
  return `${Number(value).toFixed(1)}${units[key] || ''}`
}

function truthLevelFor(item) {
  return item?.authenticity_level || item?.authenticity?.level || result.value?.authenticity_level || result.value?.authenticity?.level || '-'
}

function distanceSourceFor(item) {
  return item?.distance_source || item?.distance_precision?.source || result.value?.distance_source || result.value?.distance_precision?.source || '-'
}

function pathSourceFor(item) {
  return item?.path_source || result.value?.path_source || '-'
}

function fallbackReasonFor(item) {
  return item?.fallback_reason || item?.authenticity?.fallback_reason || result.value?.fallback_reason || result.value?.authenticity?.fallback_reason || ''
}

function recommendationReasonFor(item) {
  return item?.recommendation_reason || item?.selection_metrics?.recommendation_reason || ''
}

function tradeoffStrengthsFor(item) {
  const strengths = item?.tradeoff_summary?.strengths
  return Array.isArray(strengths) ? strengths.filter(Boolean) : []
}

function tradeoffCompromisesFor(item) {
  const compromises = item?.tradeoff_summary?.compromises
  return Array.isArray(compromises) ? compromises.filter(Boolean) : []
}

function hasTradeoffSummary(item) {
  return tradeoffStrengthsFor(item).length > 0 || tradeoffCompromisesFor(item).length > 0
}

function selectionMetricsFor(item) {
  return item?.selection_metrics || {}
}

function hasSelectionMetrics(item) {
  const metrics = selectionMetricsFor(item)
  return Boolean(metrics.candidate_count || metrics.front_quality || metrics.route_strategy)
}

function frontQualityLabel(value) {
  const labels = {
    reported_front: '真实前沿',
    degenerate_front: '退化前沿',
    single_solution_projection: '单解投影',
    empty_front: '空前沿'
  }
  return labels[value] || value || '-'
}

function hasTruthFields(item) {
  return Boolean(
    item?.authenticity_level ||
    item?.authenticity?.level ||
    item?.distance_source ||
    item?.distance_precision?.source ||
    item?.path_source ||
    item?.fallback_reason ||
    result.value?.authenticity_level ||
    result.value?.authenticity?.level ||
    result.value?.distance_source ||
    result.value?.path_source ||
    result.value?.fallback_reason
  )
}

onMounted(() => {
  fetchObjectives()
  loadDemoData()
})

watch([() => props.originId, () => props.destinationId], () => {
  result.value = null
  selectedRecommendation.value = 0
  paretoFront.value = []
  nsgaObjectives.value = []
  nsgaRoutes.value = []
  paretoSolutions.value = []
  nsgaParetoMeta.value = buildParetoFrontMeta({})
})

watch(displayMode, () => {
  nextTick(() => drawParetoChart())
})
</script>

<style scoped>
.multi-objective-panel {
  padding: 18px;
  background: rgba(8, 19, 34, 0.95);
  border-radius: 18px;
  border: 1px solid rgba(0, 212, 255, 0.12);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.2);
  color: #ecf7ff;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h3,
.algorithm-section h3,
.result-section h3,
.pareto-section h3 {
  font-size: 15px;
  font-weight: 600;
  color: #ecf7ff;
  margin: 0;
}

.weights-section {
  margin-bottom: 20px;
}

.weights-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.weights-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed rgba(255, 255, 255, 0.14);
  font-size: 14px;
  color: rgba(236, 247, 255, 0.74);
}

.weight-warning {
  color: #ff7f8f;
  font-size: 12px;
}

.algorithm-section {
  margin-bottom: 20px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 14px;
}

.algo-extra {
  margin-top: 12px;
}

.action-section {
  margin-bottom: 20px;
  text-align: center;
}

.action-section .el-button {
  width: 100%;
}

.result-section {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 18px;
}

.result-overview {
  display: grid;
  grid-template-columns: 1.2fr repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.overview-card {
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.overview-card--primary {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.14), rgba(17, 224, 183, 0.08));
  border-color: rgba(0, 212, 255, 0.18);
}

.overview-label {
  font-size: 12px;
  color: rgba(236, 247, 255, 0.54);
}

.overview-card strong {
  font-size: 18px;
  color: #ffffff;
  font-weight: 700;
}

.overview-card p,
.overview-card small {
  margin: 0;
  color: rgba(236, 247, 255, 0.7);
  line-height: 1.75;
}

.nsga-visual-block {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.nsga-alert {
  margin-bottom: 0;
}

.nsga-warning {
  margin-top: 8px;
  color: #ffbf47;
}

.order-info-tags {
  margin-top: 2px;
}

.more-text,
.pareto-summary-text {
  color: rgba(236, 247, 255, 0.52);
  font-size: 12px;
}

.pareto-section {
  padding: 16px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 14px;
}

.pareto-chart {
  width: 100%;
  height: 280px;
}

.pareto-quality-alert {
  margin-bottom: 10px;
  line-height: 1.7;
}

.routes-list {
  margin-top: 4px;
}

.route-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.route-label {
  font-weight: 600;
  color: #7bdfff;
  margin-right: 8px;
}

.route-path {
  color: rgba(236, 247, 255, 0.74);
  font-size: 13px;
}

.recommendation-flow {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.selected-recommendation-card {
  padding: 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.12), rgba(17, 224, 183, 0.08));
  border: 1px solid rgba(0, 212, 255, 0.18);
}

.selected-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.selected-kicker {
  display: inline-block;
  margin-bottom: 6px;
  font-size: 11px;
  color: rgba(236, 247, 255, 0.58);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.selected-header h4 {
  margin: 0;
  color: #ffffff;
  font-size: 20px;
}

.selected-desc {
  margin: 10px 0 12px;
  color: rgba(236, 247, 255, 0.76);
  line-height: 1.75;
}

.explanation-block {
  margin: 12px 0;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(0, 212, 255, 0.08);
  border: 1px solid rgba(0, 212, 255, 0.14);
}

.explanation-block p {
  margin: 6px 0 0;
  color: rgba(236, 247, 255, 0.82);
  line-height: 1.7;
  font-size: 13px;
}

.explanation-label,
.tradeoff-label {
  font-size: 11px;
  color: rgba(236, 247, 255, 0.56);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.tradeoff-summary,
.rec-tradeoffs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tradeoff-summary {
  margin: 10px 0 12px;
}

.tradeoff-column {
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.tradeoff-pill {
  max-width: 100%;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.tradeoff-pill--strong {
  color: #baf7e7;
  background: rgba(17, 224, 183, 0.12);
  border: 1px solid rgba(17, 224, 183, 0.2);
}

.tradeoff-pill--soft {
  color: #ffe3ad;
  background: rgba(255, 191, 71, 0.12);
  border: 1px solid rgba(255, 191, 71, 0.22);
}

.selection-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 8px 0 12px;
}

.selection-metrics span {
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  color: rgba(236, 247, 255, 0.78);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.selected-objectives,
.rec-objectives,
.truth-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.truth-tags {
  margin-top: 8px;
}

.recommendation-list,
.recommendations {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recommendation-card {
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.recommendation-card:hover {
  border-color: rgba(0, 212, 255, 0.28);
  box-shadow: 0 8px 24px rgba(0, 212, 255, 0.08);
}

.recommendation-card.active {
  border-color: #00d4ff;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.12) 0%, rgba(255,255,255,0.05) 100%);
}

.rec-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.rec-type {
  font-size: 12px;
  color: #7bdfff;
  font-weight: 600;
}

.rec-title {
  font-size: 14px;
  font-weight: 600;
  color: #ecf7ff;
}

.rec-desc {
  font-size: 13px;
  color: rgba(236, 247, 255, 0.72);
  margin-bottom: 8px;
}

.rec-reason {
  margin-bottom: 8px;
  padding: 8px 10px;
  border-radius: 9px;
  background: rgba(0, 212, 255, 0.06);
  color: rgba(236, 247, 255, 0.8);
  font-size: 12px;
  line-height: 1.65;
}

.rec-tradeoffs {
  margin-bottom: 8px;
}

.obj-tag {
  font-size: 12px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.07);
  border-radius: 999px;
  color: #cfefff;
}

.truth-tag {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  color: #b9e8ff;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.18);
}

.truth-tag--warning {
  color: #ffe1a3;
  background: rgba(255, 191, 71, 0.12);
  border-color: rgba(255, 191, 71, 0.26);
}

@media (max-width: 1200px) {
  .result-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .result-overview {
    grid-template-columns: 1fr;
  }

  .selected-header {
    flex-direction: column;
  }
}
</style>
