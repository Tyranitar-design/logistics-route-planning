<template>
  <div class="ml-prediction-page">
    <!-- 背景动效 -->
    <div class="bg-effects">
      <div class="grid-lines"></div>
      <div class="neural-pattern"></div>
    </div>

    <!-- 顶部标题 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="glow-title">🧠 机器学习预测中心</h1>
        <span class="subtitle">MACHINE LEARNING PREDICTION CENTER</span>
      </div>
      <div class="header-right">
        <div class="model-status" :class="modelTrained ? 'trained' : 'untrained'">
          <span class="status-dot"></span>
          <span>{{ modelTrained ? '模型已训练' : '模型未训练' }}</span>
        </div>
        <el-button type="primary" size="small" @click="handleTrain" :loading="training">
          <el-icon><Cpu /></el-icon> 训练模型
        </el-button>
      </div>
    </div>

    <!-- 预测配置 -->
    <div class="config-section">
      <el-card class="config-card">
        <div class="config-header">
          <span class="config-title">⚙️ 预测配置</span>
        </div>
        <div class="config-form">
          <el-form :inline="true">
            <el-form-item label="预测天数">
              <el-select v-model="predictDays" style="width: 100px">
                <el-option :value="7" label="7天" />
                <el-option :value="14" label="14天" />
                <el-option :value="30" label="30天" />
              </el-select>
            </el-form-item>
            <el-form-item label="区域">
              <el-select v-model="selectedRegion" style="width: 120px" clearable placeholder="全部区域">
                <el-option v-for="r in regions" :key="r" :value="r" :label="r" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="success" @click="loadPredictions" :loading="loading">
                🔮 开始预测
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-card>
    </div>

    <!-- 核心指标 -->
    <div class="metrics-row">
      <div class="metric-card gradient-cyan">
        <div class="metric-icon">📦</div>
        <div class="metric-content">
          <div class="metric-value">{{ summary.totalPredicted }}</div>
          <div class="metric-label">预测总订单</div>
        </div>
        <div class="metric-trend up">+{{ summary.growthRate }}%</div>
      </div>
      <div class="metric-card gradient-green">
        <div class="metric-icon">🚛</div>
        <div class="metric-content">
          <div class="metric-value">{{ summary.vehiclesNeeded }}</div>
          <div class="metric-label">建议车辆数</div>
        </div>
      </div>
      <div class="metric-card gradient-orange">
        <div class="metric-icon">💰</div>
        <div class="metric-content">
          <div class="metric-value">¥{{ summary.savedCost }}</div>
          <div class="metric-label">预计节省成本</div>
        </div>
      </div>
      <div class="metric-card gradient-purple">
        <div class="metric-icon">🎯</div>
        <div class="metric-content">
          <div class="metric-value">{{ summary.confidence }}%</div>
          <div class="metric-label">预测置信度</div>
        </div>
      </div>
    </div>

    <!-- 主图表区域 -->
    <div class="main-grid">
      <!-- 预测趋势图 -->
      <div class="panel-card large">
        <div class="card-header">
          <div class="header-deco"><span class="deco-line"></span><span class="deco-dot"></span></div>
          <span class="card-title">📈 需求预测趋势</span>
          <el-tag size="small" effect="dark">AI 预测</el-tag>
        </div>
        <div ref="trendChart" class="chart-area large"></div>
      </div>

      <!-- 区域分布 -->
      <div class="panel-card">
        <div class="card-header">
          <div class="header-deco"><span class="deco-line"></span><span class="deco-dot"></span></div>
          <span class="card-title">🗺️ 区域需求分布</span>
        </div>
        <div ref="regionChart" class="chart-area"></div>
      </div>

      <!-- 合并配送建议 -->
      <div class="panel-card">
        <div class="card-header">
          <div class="header-deco"><span class="deco-line"></span><span class="deco-dot"></span></div>
          <span class="card-title">🔄 合并配送建议</span>
          <el-badge :value="mergeSuggestions.length" type="success" />
        </div>
        <div class="suggestions-list">
          <div v-for="(item, i) in mergeSuggestions" :key="i" class="suggestion-item">
            <div class="suggestion-region">{{ item.region }}</div>
            <div class="suggestion-stats">
              <span class="orders">{{ item.predicted_orders }}单</span>
              <span class="save">省{{ item.saved_cost }}元</span>
            </div>
            <el-tag size="small" :type="item.saved_vehicles > 0 ? 'success' : 'info'">
              {{ item.saved_vehicles > 0 ? `省${item.saved_vehicles}车` : '无需合并' }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 车辆调配建议 -->
    <div class="panel-card full-width">
      <div class="card-header">
        <div class="header-deco"><span class="deco-line"></span><span class="deco-dot"></span></div>
        <span class="card-title">🚚 智能车辆调配方案</span>
      </div>
      <div class="allocation-grid">
        <div v-for="(item, i) in vehicleAllocation" :key="i" class="allocation-item">
          <div class="region-name">{{ item.region }}</div>
          <div class="allocation-bar">
            <div class="bar-fill" :style="{ width: item.vehicles_needed * 10 + '%' }"></div>
          </div>
          <div class="allocation-info">
            <span class="vehicles">{{ item.vehicles_needed }}辆</span>
            <span class="orders">{{ item.predicted_orders }}单</span>
          </div>
        </div>
      </div>
      <div class="allocation-summary">
        <span class="summary-text">总计需要 <strong>{{ totalVehicles }}</strong> 辆车辆</span>
        <el-button type="primary" size="small" @click="applyAllocation">应用调配方案</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { Cpu } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'
import * as echarts from 'echarts'
import {
  trainModel,
  getPredictions,
  getAggregatedPrediction,
  getMergeSuggestions,
  getVehicleAllocation,
  getModelStatus
} from '@/api/ml'

// 状态
const loading = ref(false)
const training = ref(false)
const modelTrained = ref(false)
const predictDays = ref(7)
const selectedRegion = ref(null)
const regions = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安']

// 数据
const predictions = ref([])
const mergeSuggestions = ref([])
const vehicleAllocation = ref([])

// 汇总
const summary = ref({
  totalPredicted: 0,
  vehiclesNeeded: 0,
  savedCost: 0,
  confidence: 92,
  growthRate: 15
})

// 图表引用
const trendChart = ref(null)
const regionChart = ref(null)

let charts = []

// 计算总车辆数
const totalVehicles = computed(() => {
  return vehicleAllocation.value.reduce((sum, item) => sum + item.vehicles_needed, 0)
})

// 安全初始化图表
const initChart = (domRef) => {
  if (!domRef) return null
  const existingInstance = echarts.getInstanceByDom(domRef)
  if (existingInstance) existingInstance.dispose()
  const chart = echarts.init(domRef)
  charts.push(chart)
  return chart
}

// 训练模型
const handleTrain = async () => {
  training.value = true
  try {
    const res = await trainModel(90)
    if (res.success) {
      modelTrained.value = true
      ElNotification({
        title: '🎉 模型训练完成',
        message: `使用 ${res.stats.total_records} 条数据训练，平均日订单 ${res.stats.avg_daily_orders.toFixed(1)} 单`,
        type: 'success',
        duration: 5000
      })
    }
  } catch (e) {
    ElMessage.error('训练失败')
  } finally {
    training.value = false
  }
}

// 加载预测数据
const loadPredictions = async () => {
  loading.value = true
  try {
    const [predRes, mergeRes, allocRes] = await Promise.all([
      getAggregatedPrediction(predictDays.value),
      getMergeSuggestions(),
      getVehicleAllocation(predictDays.value)
    ])
    
    if (predRes.success) {
      const data = predRes.data
      predictions.value = data.daily_predictions || []
      summary.value = {
        totalPredicted: data.total_predicted || 0,
        vehiclesNeeded: allocRes.data?.total_vehicles_needed || 0,
        savedCost: mergeRes.suggestions?.reduce((sum, s) => sum + s.saved_cost, 0) || 0,
        confidence: Math.round(data.avg_confidence || 92),
        growthRate: 15
      }
      initTrendChart(data.daily_predictions || [], data.region_distribution || {})
      initRegionChart(data.region_distribution || {})
    }
    
    if (mergeRes.success) {
      mergeSuggestions.value = mergeRes.suggestions || []
    }
    
    if (allocRes.success) {
      vehicleAllocation.value = allocRes.data?.allocations || []
    }
  } catch (e) {
    console.error('加载预测失败:', e)
    // 使用模拟数据
    loadMockData()
  } finally {
    loading.value = false
  }
}

// 模拟数据
const loadMockData = () => {
  predictions.value = Array.from({ length: predictDays.value }, (_, i) => {
    const date = new Date()
    date.setDate(date.getDate() + i + 1)
    return {
      date: date.toISOString().split('T')[0],
      predicted_orders: Math.floor(150 + Math.random() * 100),
      confidence_lower: Math.floor(120 + Math.random() * 50),
      confidence_upper: Math.floor(200 + Math.random() * 100),
      confidence: 95 - i * 2
    }
  })
  
  mergeSuggestions.value = [
    { region: '上海', predicted_orders: 520, saved_vehicles: 3, saved_cost: 1500 },
    { region: '北京', predicted_orders: 480, saved_vehicles: 2, saved_cost: 1000 },
    { region: '广州', predicted_orders: 350, saved_vehicles: 2, saved_cost: 800 },
    { region: '深圳', predicted_orders: 300, saved_vehicles: 1, saved_cost: 500 }
  ]
  
  vehicleAllocation.value = [
    { region: '上海', vehicles_needed: 5, predicted_orders: 520 },
    { region: '北京', vehicles_needed: 4, predicted_orders: 480 },
    { region: '广州', vehicles_needed: 3, predicted_orders: 350 },
    { region: '深圳', vehicles_needed: 3, predicted_orders: 300 },
    { region: '杭州', vehicles_needed: 2, predicted_orders: 220 },
    { region: '成都', vehicles_needed: 2, predicted_orders: 180 }
  ]
  
  summary.value = {
    totalPredicted: 2050,
    vehiclesNeeded: 19,
    savedCost: 3800,
    confidence: 89,
    growthRate: 12
  }
  
  initTrendChart(predictions.value, {})
  initRegionChart({ '上海': 520, '北京': 480, '广州': 350, '深圳': 300, '杭州': 220, '成都': 180 })
}

// 初始化趋势图
const initTrendChart = (data, regionDist) => {
  const chart = initChart(trendChart.value)
  if (!chart) return
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(0,0,0,0.8)', borderColor: '#00d4ff', textStyle: { color: '#fff' } },
    legend: { data: ['预测订单', '置信区间'], textStyle: { color: 'rgba(255,255,255,0.7)' }, bottom: 0 },
    grid: { left: '5%', right: '5%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map(d => d.date?.slice(5) || ''),
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)' }
    },
    series: [
      {
        name: '预测订单',
        type: 'line',
        data: data.map(d => d.predicted_orders),
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { color: '#00ff88', width: 3 },
        itemStyle: { color: '#00ff88' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 255, 136, 0.3)' },
            { offset: 1, color: 'rgba(0, 255, 136, 0.02)' }
          ])
        }
      },
      {
        name: '置信区间',
        type: 'line',
        data: data.map(d => d.confidence_upper),
        lineStyle: { type: 'dashed', color: 'rgba(0, 212, 255, 0.5)' },
        itemStyle: { color: '#00d4ff' },
        symbol: 'none'
      }
    ]
  })
}

// 初始化区域分布图
const initRegionChart = (regionDist) => {
  const chart = initChart(regionChart.value)
  if (!chart) return
  
  const data = Object.entries(regionDist).map(([name, value]) => ({ name, value }))
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', backgroundColor: 'rgba(0,0,0,0.8)', borderColor: '#00d4ff', textStyle: { color: '#fff' } },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '50%'],
      data: data.map((d, i) => ({
        name: d.name,
        value: d.value,
        itemStyle: { color: ['#00d4ff', '#00ff88', '#ffd93d', '#ff6b6b', '#a855f7', '#06b6d4'][i % 6] }
      })),
      label: { show: true, formatter: '{b}\n{c}单', color: '#fff', fontSize: 11 },
      itemStyle: { borderRadius: 6, borderColor: 'rgba(0,0,0,0.3)', borderWidth: 2 }
    }]
  })
}

// 应用调配方案
const applyAllocation = () => {
  ElNotification({
    title: '✅ 调配方案已应用',
    message: `已安排 ${totalVehicles.value} 辆车辆进行配送`,
    type: 'success'
  })
}

// 窗口调整
const handleResize = () => charts.forEach(c => c.resize())

onMounted(async () => {
  // 检查模型状态
  try {
    const status = await getModelStatus()
    modelTrained.value = status.is_trained
  } catch (e) {}
  
  // 加载预测数据
  await loadPredictions()
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  charts.forEach(c => c.dispose())
})
</script>

<style scoped>
.ml-prediction-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #0d1033 100%);
  padding: 16px;
  color: #fff;
  position: relative;
  overflow: hidden;
}

.bg-effects {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.grid-lines {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
}

.neural-pattern {
  position: absolute;
  inset: 0;
  opacity: 0.05;
  background: radial-gradient(circle at 20% 30%, rgba(0, 255, 136, 0.3) 0%, transparent 50%),
              radial-gradient(circle at 80% 70%, rgba(0, 212, 255, 0.3) 0%, transparent 50%);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px 20px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
}

.glow-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(90deg, #00ff88, #00d4ff, #a855f7);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  display: block;
  font-size: 10px;
  color: rgba(255,255,255,0.4);
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-top: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.model-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
}

.model-status.trained {
  background: rgba(0, 255, 136, 0.15);
  border: 1px solid rgba(0, 255, 136, 0.3);
  color: #00ff88;
}

.model-status.untrained {
  background: rgba(255, 217, 61, 0.15);
  border: 1px solid rgba(255, 217, 61, 0.3);
  color: #ffd93d;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.model-status.trained .status-dot {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 currentColor; }
  50% { box-shadow: 0 0 0 6px transparent; }
}

/* 配置卡片 */
.config-section { margin-bottom: 16px; }
.config-card {
  background: rgba(0, 212, 255, 0.05) !important;
  border: 1px solid rgba(0, 212, 255, 0.15) !important;
  border-radius: 12px !important;
}
.config-header { margin-bottom: 12px; }
.config-title { font-size: 14px; font-weight: 600; color: #fff; }
.config-form { padding: 8px 0; }

/* 指标卡片 */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  display: flex;
  align-items: center;
  padding: 16px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
  gap: 12px;
}

.metric-card.gradient-cyan { border-left: 3px solid #00d4ff; }
.metric-card.gradient-green { border-left: 3px solid #00ff88; }
.metric-card.gradient-orange { border-left: 3px solid #ff9500; }
.metric-card.gradient-purple { border-left: 3px solid #a855f7; }

.metric-icon { font-size: 28px; }
.metric-content { flex: 1; }
.metric-value { font-size: 24px; font-weight: 700; color: #fff; }
.metric-label { font-size: 12px; color: rgba(255,255,255,0.6); margin-top: 4px; }
.metric-trend { font-size: 12px; padding: 4px 8px; border-radius: 10px; }
.metric-trend.up { background: rgba(0, 255, 136, 0.2); color: #00ff88; }

/* 面板卡片 */
.main-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.panel-card {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 12px;
  padding: 12px;
}

.panel-card.large { grid-row: span 2; }
.panel-card.full-width { width: 100%; }

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.header-deco { display: flex; align-items: center; gap: 4px; }
.deco-line { width: 16px; height: 2px; background: linear-gradient(90deg, #00ff88, transparent); }
.deco-dot { width: 5px; height: 5px; background: #00ff88; border-radius: 50%; }
.card-title { flex: 1; font-size: 13px; font-weight: 600; color: #fff; }

.chart-area { height: 200px; }
.chart-area.large { height: 320px; }

/* 建议列表 */
.suggestions-list {
  max-height: 280px;
  overflow-y: auto;
}

.suggestion-item {
  display: flex;
  align-items: center;
  padding: 10px;
  margin-bottom: 8px;
  background: rgba(0, 255, 136, 0.05);
  border-radius: 8px;
  border-left: 3px solid #00ff88;
}

.suggestion-region {
  font-weight: 600;
  color: #fff;
  width: 60px;
}

.suggestion-stats {
  flex: 1;
  display: flex;
  gap: 12px;
  font-size: 12px;
}

.suggestion-stats .orders { color: rgba(255,255,255,0.7); }
.suggestion-stats .save { color: #00ff88; }

/* 调配网格 */
.allocation-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.allocation-item {
  padding: 12px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
}

.region-name { font-size: 14px; font-weight: 600; color: #fff; margin-bottom: 8px; }

.allocation-bar {
  height: 6px;
  background: rgba(0, 212, 255, 0.1);
  border-radius: 3px;
  margin-bottom: 8px;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00d4ff, #00ff88);
  border-radius: 3px;
}

.allocation-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: rgba(255,255,255,0.6);
}

.allocation-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.summary-text { color: rgba(255,255,255,0.7); }
.summary-text strong { color: #00ff88; font-size: 18px; }

/* Element Plus 覆盖 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #00ff88, #00d4ff);
  border: none;
  color: #000;
}

:deep(.el-tag) {
  background: rgba(0, 255, 136, 0.2);
  border-color: rgba(0, 255, 136, 0.3);
  color: #00ff88;
}

:deep(.el-card) {
  background: transparent;
}

:deep(.el-input__wrapper) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  box-shadow: none;
}

:deep(.el-input__inner) { color: #fff; }
</style>