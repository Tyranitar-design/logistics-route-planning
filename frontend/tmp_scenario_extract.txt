<template>
  <div class="scenario-compare-container">
    <!-- 页面标题 -->
    <el-page-header @back="goBack" class="page-header">
      <template #content>
        <span class="text-large font-600 mr-3">场景对比分析</span>
        <el-tag type="warning" size="small">多方案评估</el-tag>
      </template>
    </el-page-header>

    <!-- 选择场景 -->
    <el-row :gutter="20" class="scenario-selector">
      <el-col :span="12">
        <el-card class="selector-card">
          <template #header>
            <span>📊 方案 A</span>
          </template>
          <el-select v-model="scenarioA" placeholder="选择场景" style="width: 100%" @change="loadScenarioA">
            <el-option
              v-for="s in scenarios"
              :key="s.id"
              :label="s.name"
              :value="s.id"
            >
              <span>{{ s.name }}</span>
              <el-tag size="small" style="margin-left: 10px">{{ s.algorithm }}</el-tag>
            </el-option>
          </el-select>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="selector-card">
          <template #header>
            <span>📊 方案 B</span>
          </template>
          <el-select v-model="scenarioB" placeholder="选择场景" style="width: 100%" @change="loadScenarioB">
            <el-option
              v-for="s in scenarios"
              :key="s.id"
              :label="s.name"
              :value="s.id"
            >
              <span>{{ s.name }}</span>
              <el-tag size="small" style="margin-left: 10px">{{ s.algorithm }}</el-tag>
            </el-option>
          </el-select>
        </el-card>
      </el-col>
    </el-row>

    <!-- 对比结果 -->
    <el-row :gutter="20" class="compare-content" v-if="dataA && dataB">
      <!-- 关键指标对比 -->
      <el-card class="metrics-card">
        <template #header>
          <span>📈 关键指标对比</span>
        </template>
        
        <el-row :gutter="40">
          <el-col :span="6" v-for="metric in compareMetrics" :key="metric.key">
            <div class="metric-item">
              <div class="metric-label">{{ metric.label }}</div>
              <div class="metric-values">
                <div class="metric-value" :class="{ better: metric.aBetter }">
                  <span class="label">A</span>
                  <span class="value">{{ formatValue(dataA[metric.key], metric.unit) }}</span>
                </div>
                <div class="metric-diff" :class="metric.diffClass">
                  {{ metric.diffText }}
                </div>
                <div class="metric-value" :class="{ better: !metric.aBetter }">
                  <span class="label">B</span>
                  <span class="value">{{ formatValue(dataB[metric.key], metric.unit) }}</span>
                </div>
              </div>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <!-- 雷达图对比 -->
      <el-row :gutter="20" class="chart-row">
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <span>🎯 综合评分对比</span>
            </template>
            <div ref="radarChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card class="chart-card">
            <template #header>
              <span>📊 成本构成对比</span>
            </template>
            <div ref="barChartRef" class="chart-container"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 设施列表对比 -->
      <el-row :gutter="20" class="table-row">
        <el-col :span="12">
          <el-card>
            <template #header>
              <span>🏢 方案 A 设施 ({{ dataA.selected_facilities?.length || 0 }} 个)</span>
            </template>
            <el-table :data="dataA.selected_facilities" border stripe size="small">
              <el-table-column prop="name" label="名称" />
              <el-table-column prop="city" label="城市" width="80" />
              <el-table-column prop="capacity" label="容量" width="80" />
              <el-table-column prop="fixed_cost" label="固定成本" width="100">
                <template #default="{ row }">
                  ¥{{ row.fixed_cost?.toLocaleString() }}
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>
              <span>🏢 方案 B 设施 ({{ dataB.selected_facilities?.length || 0 }} 个)</span>
            </template>
            <el-table :data="dataB.selected_facilities" border stripe size="small">
              <el-table-column prop="name" label="名称" />
              <el-table-column prop="city" label="城市" width="80" />
              <el-table-column prop="capacity" label="容量" width="80" />
              <el-table-column prop="fixed_cost" label="固定成本" width="100">
                <template #default="{ row }">
                  ¥{{ row.fixed_cost?.toLocaleString() }}
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <!-- 推荐结论 -->
      <el-card class="conclusion-card">
        <template #header>
          <span>💡 分析结论</span>
        </template>
        <el-alert
          :title="recommendation.title"
          :type="recommendation.type"
          :description="recommendation.description"
          show-icon
          :closable="false"
        />
      </el-card>
    </el-row>

    <!-- 空状态 -->
    <el-empty v-else description="请选择两个场景进行对比" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

const router = useRouter()

// 数据
const scenarios = ref([])
const scenarioA = ref(null)
const scenarioB = ref(null)
const dataA = ref(null)
const dataB = ref(null)

// 图表
const radarChartRef = ref(null)
const barChartRef = ref(null)
let radarChart = null
let barChart = null

// 加载场景列表
async function loadScenarios() {
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch('http://localhost:5000/api/network/scenarios', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await response.json()
    
    if (data.status === 'success') {
      scenarios.value = data.scenarios
    }
  } catch (error) {
    ElMessage.error('加载场景失败: ' + error.message)
  }
}

// 加载场景详情
async function loadScenarioA(id) {
  if (!id) return
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(`http://localhost:5000/api/network/scenarios/${id}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await response.json()
    if (data.status === 'success') {
      dataA.value = data.scenario
      updateCharts()
    }
  } catch (error) {
    ElMessage.error('加载场景失败')
  }
}

async function loadScenarioB(id) {
  if (!id) return
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(`http://localhost:5000/api/network/scenarios/${id}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await response.json()
    if (data.status === 'success') {
      dataB.value = data.scenario
      updateCharts()
    }
  } catch (error) {
    ElMessage.error('加载场景失败')
  }
}

// 对比指标
const compareMetrics = computed(() => {
  if (!dataA.value || !dataB.value) return []
  
  const metrics = [
    { key: 'total_cost', label: '总成本', unit: '¥', lowerBetter: true },
    { key: 'total_distance', label: '总距离', unit: 'km', lowerBetter: true },
    { key: 'service_level', label: '服务水平', unit: '%', lowerBetter: false },
    { key: 'avg_distance', label: '平均距离', unit: 'km', lowerBetter: true },
  ]
  
  return metrics.map(m => {
    const aVal = dataA.value[m.key] || 0
    const bVal = dataB.value[m.key] || 0
    const diff = aVal - bVal
    const aBetter = m.lowerBetter ? diff < 0 : diff > 0
    
    return {
      ...m,
      aBetter,
      diffText: diff > 0 ? `+${formatValue(Math.abs(diff), m.unit)}` : `-${formatValue(Math.abs(diff), m.unit)}`,
      diffClass: aBetter ? 'text-success' : 'text-danger'
    }
  })
})

// 推荐结论
const recommendation = computed(() => {
  if (!dataA.value || !dataB.value) return { title: '', description: '', type: 'info' }
  
  const scoreA = calculateScore(dataA.value)
  const scoreB = calculateScore(dataB.value)
  
  if (scoreA > scoreB * 1.1) {
    return {
      title: '推荐方案 A',
      description: `方案 A 综合得分 ${scoreA.toFixed(1)}，比方案 B 高 ${((scoreA - scoreB) / scoreB * 100).toFixed(1)}%。主要优势：成本更低、服务覆盖更好。`,
      type: 'success'
    }
  } else if (scoreB > scoreA * 1.1) {
    return {
      title: '推荐方案 B',
      description: `方案 B 综合得分 ${scoreB.toFixed(1)}，比方案 A 高 ${((scoreB - scoreA) / scoreA * 100).toFixed(1)}%。主要优势：成本更低、服务覆盖更好。`,
      type: 'success'
    }
  } else {
    return {
      title: '两方案相近',
      description: `两方案综合得分接近（A: ${scoreA.toFixed(1)} vs B: ${scoreB.toFixed(1)}），可根据其他因素（如实施难度、风险）进行选择。`,
      type: 'warning'
    }
  }
})

function calculateScore(data) {
  const costScore = Math.max(0, 100 - (data.total_cost || 0) / 10000)
  const serviceScore = (data.service_level || 0) * 100
  const distanceScore = Math.max(0, 100 - (data.avg_distance || 0))
  
  return costScore * 0.4 + serviceScore * 0.4 + distanceScore * 0.2
}

// 格式化值
function formatValue(val, unit) {
  if (unit === '¥') {
    return '¥' + (val || 0).toLocaleString()
  } else if (unit === '%') {
    return ((val || 0) * 100).toFixed(1) + '%'
  } else {
    return (val || 0).toFixed(1) + unit
  }
}

// 更新图表
function updateCharts() {
  if (!dataA.value || !dataB.value) return
  
  nextTick(() => {
    renderRadarChart()
    renderBarChart()
  })
}

// 渲染雷达图
function renderRadarChart() {
  if (!radarChartRef.value) return
  
  if (!radarChart) {
    radarChart = echarts.init(radarChartRef.value)
  }
  
  const scoreA = calculateScore(dataA.value)
  const scoreB = calculateScore(dataB.value)
  
  const maxCost = Math.max(dataA.value.total_cost, dataB.value.total_cost, 1)
  const maxDist = Math.max(dataA.value.total_distance, dataB.value.total_distance, 1)
  
  const option = {
    title: {
      text: '综合评分对比',
      left: 'center'
    },
    tooltip: {
      trigger: 'item'
    },
    legend: {
      data: [dataA.value.name, dataB.value.name],
      bottom: 10
    },
    radar: {
      indicator: [
        { name: '成本', max: 100 },
        { name: '距离', max: 100 },
        { name: '服务水平', max: 100 },
        { name: '均衡性', max: 100 },
        { name: '综合得分', max: 100 }
      ]
    },
    series: [{
      type: 'radar',
      data: [
        {
          value: [
            Math.max(0, 100 - dataA.value.total_cost / maxCost * 100),
            Math.max(0, 100 - dataA.value.total_distance / maxDist * 100),
            (dataA.value.service_level || 0) * 100,
            Math.max(0, 100 - (dataA.value.avg_distance || 0)),
            scoreA
          ],
          name: dataA.value.name,
          itemStyle: { color: '#409EFF' },
          areaStyle: { color: 'rgba(64, 158, 255, 0.3)' }
        },
        {
          value: [
            Math.max(0, 100 - dataB.value.total_cost / maxCost * 100),
            Math.max(0, 100 - dataB.value.total_distance / maxDist * 100),
            (dataB.value.service_level || 0) * 100,
            Math.max(0, 100 - (dataB.value.avg_distance || 0)),
            scoreB
          ],
          name: dataB.value.name,
          itemStyle: { color: '#67C23A' },
          areaStyle: { color: 'rgba(103, 194, 58, 0.3)' }
        }
      ]
    }]
  }
  
  radarChart.setOption(option, true)
}

// 渲染柱状图
function renderBarChart() {
  if (!barChartRef.value) return
  
  if (!barChart) {
    barChart = echarts.init(barChartRef.value)
  }
  
  const option = {
    title: {
      text: '成本构成对比',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: [dataA.value.name, dataB.value.name],
      bottom: 10
    },
    xAxis: {
      type: 'category',
      data: ['固定成本', '运输成本', '总成本']
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: '¥{value}'
      }
    },
    series: [
      {
        name: dataA.value.name,
        type: 'bar',
        data: [
          dataA.value.total_fixed_cost || 0,
          dataA.value.transport_cost || 0,
          dataA.value.total_cost || 0
        ],
        itemStyle: { color: '#409EFF' }
      },
      {
        name: dataB.value.name,
        type: 'bar',
        data: [
          dataB.value.total_fixed_cost || 0,
          dataB.value.transport_cost || 0,
          dataB.value.total_cost || 0
        ],
        itemStyle: { color: '#67C23A' }
      }
    ]
  }
  
  barChart.setOption(option, true)
}

// 返回
function goBack() {
  router.push('/network-design')
}

// 初始化
onMounted(() => {
  loadScenarios()
})
</script>

<style scoped>
.scenario-compare-container {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}

.page-header {
  margin-bottom: 20px;
  background: white;
  padding: 15px 20px;
  border-radius: 8px;
}

.scenario-selector {
  margin-bottom: 20px;
}

.selector-card {
  background: white;
}

.compare-content {
  margin-top: 20px;
}

.metrics-card {
  margin-bottom: 20px;
}

.metric-item {
  text-align: center;
  padding: 15px;
  background: #f9f9f9;
  border-radius: 8px;
}

.metric-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.metric-values {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.metric-value {
  padding: 5px 10px;
  border-radius: 4px;
  background: #fff;
}

.metric-value.better {
  background: #e8f5e9;
  border: 1px solid #67C23A;
}

.metric-value .label {
  font-size: 12px;
  color: #999;
  margin-right: 5px;
}

.metric-value .value {
  font-size: 14px;
  font-weight: bold;
  color: #333;
}

.metric-diff {
  font-size: 12px;
  font-weight: bold;
}

.text-success {
  color: #67C23A;
}

.text-danger {
  color: #F56C6C;
}

.chart-row {
  margin-bottom: 20px;
}

.chart-card {
  background: white;
}

.chart-container {
  height: 300px;
}

.table-row {
  margin-bottom: 20px;
}

.conclusion-card {
  margin-top: 20px;
}

.text-large {
  font-size: 18px;
}

.font-600 {
  font-weight: 600;
}

.mr-3 {
  margin-right: 12px;
}
</style>
