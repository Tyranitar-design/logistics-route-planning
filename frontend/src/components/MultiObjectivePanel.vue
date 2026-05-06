<template>
  <div class="multi-objective-panel">
    <!-- 权重调节区 -->
    <div class="weights-section">
      <div class="section-header">
        <h3>🎯 优化目标权重</h3>
        <el-button 
          type="primary" 
          size="small" 
          text
          @click="resetWeights"
        >
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
        <span>权重总计: </span>
        <el-tag :type="totalWeightValid ? 'success' : 'danger'">
          {{ totalWeight }}%
        </el-tag>
        <span v-if="!totalWeightValid" class="weight-warning">
          (请调整至100%)
        </span>
      </div>
    </div>
    
    <!-- 优化算法选择 -->
    <div class="algorithm-section">
      <h3>⚙️ 优化算法</h3>
      <el-radio-group v-model="algorithm" size="small">
        <el-radio-button value="all">智能推荐</el-radio-button>
        <el-radio-button value="weighted_sum">加权最优</el-radio-button>
        <el-radio-button value="pareto">Pareto前沿</el-radio-button>
        <el-radio-button value="nsga2">NSGA-II</el-radio-button>
        <el-radio-button value="nsga3">NSGA-III</el-radio-button>
      </el-radio-group>
      
      <div v-if="algorithm === 'nsga2' || algorithm === 'nsga3'" style="margin-top: 12px">
        <el-form-item label="迭代次数" size="small">
          <el-input-number v-model="nGen" :min="50" :max="300" :step="50" size="small" />
        </el-form-item>
      </div>
    </div>
    
    <!-- 开始优化按钮 -->
    <div class="action-section">
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
    </div>
    
    <!-- Pareto 前沿图 -->
    <div v-if="paretoSolutions.length > 0" class="pareto-section">
      <div class="section-header">
        <h3>📈 Pareto 前沿 - 非支配解集</h3>
        <el-radio-group v-model="displayMode" size="small">
          <el-radio-button value="3d">3D</el-radio-button>
          <el-radio-button value="2d">2D</el-radio-button>
        </el-radio-group>
      </div>
      <div ref="paretoChartRef" style="width: 100%; height: 280px;"></div>
      <div style="margin-top: 10px; font-size: 12px; color: #909399;">
        共 {{ paretoSolutions.length }} 个非支配解
      </div>
    </div>
    
    <!-- 优化结果 -->
    <div v-if="result" class="result-section">
      <h3>📊 优化结果</h3>
      
      <!-- NSGA 结果 -->
      <div v-if="algorithm === 'nsga2' || algorithm === 'nsga3'" class="nsga-result">
        <el-alert type="success" :closable="false" style="margin-bottom: 12px;">
          <template #title>
            📍 基于选定起终点的本地数据库优化
          </template>
          <div style="font-size: 12px;">
            <strong>起点(仓库):</strong> {{ result.depot?.name || '默认' }} | 
            <strong>待配送订单:</strong> {{ result.n_orders || 0 }} 个 | 
            <strong>配送点:</strong> {{ result.n_customers || 0 }} 个 | 
            <strong>可用车辆:</strong> {{ result.n_vehicles || 0 }} 辆
          </div>
          <div v-if="result.n_orders === 0 && result.n_customers > 0" style="margin-top: 8px; color: #E6A23C;">
            ⚠️ 没有待配送订单，已使用节点数据进行优化
          </div>
        </el-alert>
        
        <div v-if="result.order_info && result.order_info.length > 0" style="margin-bottom: 12px;">
          <el-tag v-for="order in result.order_info.slice(0, 5)" :key="order.id" 
                  size="small" style="margin: 2px;">
            {{ order.node_name || order.order_number }}
          </el-tag>
          <span v-if="result.order_info.length > 5" style="color: #909399; font-size: 12px;">
            +{{ result.order_info.length - 5 }} 更多...
          </span>
        </div>
        
        <el-row :gutter="10">
          <el-col :span="8">
            <el-statistic title="总距离" :value="nsgaObjectives[0]?.toFixed(1)" suffix=" km" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="总时间" :value="nsgaObjectives[1]?.toFixed(1)" suffix=" min" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="车辆数" :value="Math.round(nsgaObjectives[2] || 0)" />
          </el-col>
        </el-row>
        
        <el-divider />
        
        <div class="routes-list">
          <div v-for="(route, i) in nsgaRoutes" :key="i" class="route-item">
            <span class="route-label">路线 {{ i + 1 }}:</span>
            <span class="route-path">{{ route.join(' → ') }}</span>
          </div>
        </div>
      </div>
      
      <!-- 推荐方案列表 -->
      <div v-else class="recommendations">
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
          <div class="rec-objectives">
            <span
              v-for="(value, key) in rec.objectives"
              :key="key"
              class="obj-tag"
            >
              {{ getObjectiveLabel(key) }}: {{ formatValue(key, value) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'
import WeightSlider from './WeightSlider.vue'
import { getObjectives, optimizeRoute } from '../api/multiObjective'
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

// 状态
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

// 新增变量
const demoData = ref(null)
const paretoSolutions = ref([])
const displayMode = ref('3d')
const params = ref({ nCustomers: 10 })

// 默认权重
const defaultWeights = {
  distance: 25,
  time: 30,
  cost: 20,
  traffic: 15,
  weather_risk: 10
}

// 权重总计
const totalWeight = computed(() => {
  return Object.values(weights.value).reduce((sum, w) => sum + w, 0)
})

const totalWeightValid = computed(() => {
  return totalWeight.value === 100
})

const canOptimize = computed(() => {
  return props.originId && props.destinationId && totalWeightValid.value
})

// 获取优化目标列表
async function fetchObjectives() {
  try {
    const res = await getObjectives()
    if (res.success) {
      objectives.value = res.objectives
      
      // 初始化权重
      res.objectives.forEach(obj => {
        weights.value[obj.name] = obj.default_weight * 100
      })
    }
  } catch (error) {
    console.error('获取优化目标失败:', error)
    weights.value = { ...defaultWeights }
  }
}

// 重置权重
function resetWeights() {
  weights.value = { ...defaultWeights }
  ElMessage.success('权重已重置')
}

// 权重变化处理
function handleWeightChange({ objective, value }) {
  // 可以在这里添加权重自动调整逻辑
}

// 开始优化
async function startOptimize() {
  if (!canOptimize.value) {
    ElMessage.warning('请先选择起点和终点')
    return
  }
  
  loading.value = true
  
  try {
    // NSGA 算法
    if (algorithm.value === 'nsga2' || algorithm.value === 'nsga3') {
      await runNsgaOptimize()
      return
    }
    
    // 原有算法
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

// NSGA 优化 - 使用本地数据库的真实数据
async function runNsgaOptimize() {
  try {
    const solver = algorithm.value === 'nsga2' ? 'pymoo_nsga2' : 'pymoo_nsga3'
    
    // 使用本地数据库数据进行优化
    const requestData = {
      origin_id: Number(props.originId),
      destination_id: Number(props.destinationId),
      solver: solver,
      n_gen: nGen.value,
      use_local_data: true  // 标记使用本地数据
    }
    
    const res = await axios.post('/api/multi-objective/nsga-optimize', requestData)
    
    if (res.data.success) {
      nsgaObjectives.value = res.data.objectives || []
      nsgaRoutes.value = res.data.routes || []
      paretoFront.value = res.data.pareto_front || []
      result.value = { success: true, n_orders: res.data.n_orders, n_vehicles: res.data.n_vehicles }
      
      // 生成 Pareto 解集
      generateParetoSolutions(res.data)
      
      ElMessage.success(`NSGA优化完成！使用 ${res.data.n_orders || 0} 个订单，Pareto前沿: ${paretoSolutions.value.length} 个解`)
      
      // 绘制 Pareto 前沿图
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

// 加载演示数据
async function loadDemoData() {
  try {
    const res = await axios.get('/api/optimization/demo')
    demoData.value = res.data
  } catch (e) {
    console.error('加载演示数据失败', e)
  }
}

// 生成 Pareto 解集
function generateParetoSolutions(data) {
  // 后端已透传真实 Pareto 前沿，直接使用
  if (data.pareto_front && data.pareto_front.length > 0) {
    // 确保数据是数字数组
    paretoSolutions.value = data.pareto_front.map(s => 
      Array.isArray(s) ? s.map(v => parseFloat(v)) : [parseFloat(s)]
    )
    return
  }
  
  // 如果只有一个最优解，构建单点
  if (data.objectives && data.objectives.length > 0) {
    paretoSolutions.value = [data.objectives.map(v => parseFloat(v))]
    return
  }
  
  paretoSolutions.value = []
}

// 绘制 Pareto 前沿图
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
    // 如果 3D 失败，回退到 2D
    if (displayMode.value === '3d') {
      displayMode.value = '2d'
      nextTick(() => drawParetoChart())
    }
  }
}

// 绘制 3D 图
function draw3DChart() {
  const option = {
    title: {
      text: 'Pareto 前沿 - 三维解集空间',
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
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

// 绘制 2D 图
function draw2DChart() {
  const option = {
    title: {
      text: 'Pareto 前沿 (距离 vs 时间)',
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
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

// 选择推荐方案
function selectRecommendation(index) {
  selectedRecommendation.value = index
  const rec = result.value?.recommendations?.[index]
  if (rec) {
    emit('select', rec)
  }
}

// 获取类型标签
function getTypeLabel(type) {
  const labels = {
    weighted_best: '🏆 综合',
    pareto: '⚖️ 均衡',
    single_objective: '📌 单项'
  }
  return labels[type] || type
}

// 获取目标标签
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

// 格式化数值
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

onMounted(() => {
  fetchObjectives()
  loadDemoData()
})

// 监听起终点变化
watch([() => props.originId, () => props.destinationId], () => {
  result.value = null
  selectedRecommendation.value = 0
  paretoFront.value = []
  nsgaObjectives.value = []
  nsgaRoutes.value = []
  paretoSolutions.value = []
})

// 监听显示模式变化
watch(displayMode, () => {
  nextTick(() => drawParetoChart())
})
</script>

<style scoped>
.multi-objective-panel {
  padding: 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
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
  color: #303133;
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
  border-top: 1px dashed #e4e7ed;
  font-size: 14px;
  color: #606266;
}

.weight-warning {
  color: #F56C6C;
  font-size: 12px;
}

.algorithm-section {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.algorithm-section h3 {
  margin-bottom: 12px;
}

.action-section {
  margin-bottom: 20px;
  text-align: center;
}

.action-section .el-button {
  width: 100%;
}

.pareto-section {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.pareto-section h3 {
  margin-bottom: 12px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h3 {
  margin: 0;
}

.result-section {
  border-top: 1px solid #e4e7ed;
  padding-top: 16px;
}

.result-section h3 {
  margin-bottom: 12px;
}

.nsga-result {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.routes-list {
  margin-top: 12px;
}

.route-item {
  padding: 8px 12px;
  margin-bottom: 8px;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e4e7ed;
}

.route-label {
  font-weight: 600;
  color: #409EFF;
  margin-right: 8px;
}

.route-path {
  color: #606266;
  font-size: 13px;
}

.recommendations {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recommendation-card {
  padding: 12px 16px;
  background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%);
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.recommendation-card:hover {
  border-color: #409EFF;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}

.recommendation-card.active {
  border-color: #409EFF;
  background: linear-gradient(135deg, #ecf5ff 0%, #fff 100%);
}

.rec-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.rec-type {
  font-size: 12px;
  color: #409EFF;
  font-weight: 500;
}

.rec-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.rec-desc {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.rec-objectives {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.obj-tag {
  font-size: 12px;
  padding: 2px 8px;
  background: #f0f2f5;
  border-radius: 4px;
  color: #606266;
}
</style>
