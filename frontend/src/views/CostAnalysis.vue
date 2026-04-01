<template>
  <div class="cost-analysis">
    <!-- 背景动效 -->
    <div class="bg-effects">
      <div class="grid-lines"></div>
      <div class="hex-pattern"></div>
      <div class="floating-dots">
        <span v-for="i in 30" :key="i" class="dot" :style="getDotStyle(i)"></span>
      </div>
    </div>

    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <div class="title-group">
          <h1 class="glow-title">💰 成本监控中心</h1>
          <span class="subtitle">COST MONITORING CENTER</span>
        </div>
      </div>
      <div class="header-center">
        <div class="realtime-stats">
          <div class="stat-pulse"></div>
          <span class="stat-label">实时监控中</span>
          <span class="stat-time">{{ currentTime }}</span>
        </div>
      </div>
      <div class="header-right">
        <div class="cost-alert" v-if="costAlert">
          <span class="alert-icon">⚠️</span>
          <span class="alert-text">{{ costAlert }}</span>
        </div>
        <el-button type="primary" size="small" @click="refreshAll">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 核心成本指标 -->
    <div class="kpi-row">
      <div v-for="(kpi, index) in costKpis" :key="index" class="kpi-card" :class="kpi.type">
        <div class="kpi-bg"></div>
        <div class="kpi-ring">
          <svg viewBox="0 0 100 100">
            <circle class="ring-bg" cx="50" cy="50" r="45"/>
            <circle class="ring-progress" cx="50" cy="50" r="45" 
              :style="{ strokeDashoffset: 283 - (283 * kpi.percent / 100) }"/>
          </svg>
          <div class="kpi-center">
            <span class="kpi-value">{{ animatedValues[kpi.key] }}</span>
            <span class="kpi-unit">{{ kpi.unit }}</span>
          </div>
        </div>
        <div class="kpi-info">
          <span class="kpi-label">{{ kpi.label }}</span>
          <div class="kpi-trend" :class="kpi.trend > 0 ? 'up' : 'down'">
            <span class="trend-icon">{{ kpi.trend > 0 ? '↑' : '↓' }}</span>
            <span>{{ Math.abs(kpi.trend) }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 主图表区域 -->
    <div class="main-grid">
      <!-- 左侧面板 -->
      <div class="left-panel">
        <!-- 成本趋势 -->
        <div class="panel-card">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">📈 成本趋势监控</span>
            <el-radio-group v-model="trendDays" size="small" @change="loadCostTrend">
              <el-radio-button :value="7">7天</el-radio-button>
              <el-radio-button :value="30">30天</el-radio-button>
              <el-radio-button :value="90">90天</el-radio-button>
            </el-radio-group>
          </div>
          <div ref="trendChart" class="chart-area"></div>
          <div class="trend-stats">
            <div class="stat-item">
              <span class="stat-label">日均成本</span>
              <span class="stat-value">¥{{ trendStats.avgDaily }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">最高日</span>
              <span class="stat-value">{{ trendStats.maxDay }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">增长趋势</span>
              <span class="stat-value" :class="trendStats.trend > 0 ? 'up' : 'down'">
                {{ trendStats.trend > 0 ? '+' : '' }}{{ trendStats.trend }}%
              </span>
            </div>
          </div>
        </div>

        <!-- 成本构成 -->
        <div class="panel-card">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">🥧 成本构成分析</span>
          </div>
          <div ref="composeChart" class="chart-area"></div>
          <div class="compose-legend">
            <div v-for="(item, i) in composeData" :key="i" class="legend-item">
              <span class="legend-dot" :style="{ background: item.color }"></span>
              <span class="legend-name">{{ item.name }}</span>
              <span class="legend-value">¥{{ item.value.toLocaleString() }}</span>
              <span class="legend-percent">{{ item.percent }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 中间面板 -->
      <div class="center-panel">
        <!-- 路线成本排行 -->
        <div class="panel-card large">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">🛣️ 路线成本排行 TOP10</span>
            <el-tag size="small" effect="dark">实时</el-tag>
          </div>
          <div ref="routeChart" class="chart-area large"></div>
        </div>

        <!-- 高德 vs 本地算法对比 -->
        <div class="panel-card">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">⚖️ 算法成本对比</span>
          </div>
          <div ref="compareChart" class="chart-area"></div>
          <div class="compare-summary">
            <div class="compare-item local">
              <span class="compare-label">本地算法节省</span>
              <span class="compare-value">¥{{ compareStats.saving }}</span>
              <span class="compare-percent">节省率 {{ compareStats.rate }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧面板 -->
      <div class="right-panel">
        <!-- 节点成本分析 -->
        <div class="panel-card">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">📍 节点成本分布</span>
          </div>
          <div ref="nodeChart" class="chart-area"></div>
        </div>

        <!-- 成本优化建议 -->
        <div class="panel-card">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">💡 智能优化建议</span>
            <el-badge :value="suggestions.length" type="success" />
          </div>
          <div class="suggestions-list">
            <div 
              v-for="(item, index) in suggestions" 
              :key="index"
              class="suggestion-item"
              :class="'priority-' + item.priority"
            >
              <div class="suggestion-icon">
                {{ item.icon }}
              </div>
              <div class="suggestion-content">
                <div class="suggestion-title">{{ item.title }}</div>
                <div class="suggestion-desc">{{ item.description }}</div>
                <div class="suggestion-saving">
                  <span class="saving-label">预计节省</span>
                  <span class="saving-value">¥{{ item.saving }}</span>
                </div>
              </div>
              <div class="suggestion-priority" :class="item.priority">
                {{ item.priority === 'high' ? '紧急' : item.priority === 'medium' ? '重要' : '一般' }}
              </div>
            </div>
          </div>
        </div>

        <!-- 成本预警 -->
        <div class="panel-card">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">🚨 成本预警</span>
            <el-badge :value="warnings.length" type="danger" />
          </div>
          <div class="warnings-list">
            <div 
              v-for="(item, index) in warnings" 
              :key="index"
              class="warning-item"
              :class="item.level"
            >
              <div class="warning-icon">
                {{ item.level === 'high' ? '🔴' : item.level === 'medium' ? '🟡' : '🟢' }}
              </div>
              <div class="warning-content">
                <div class="warning-type">{{ item.type }}</div>
                <div class="warning-detail">{{ item.detail }}</div>
              </div>
              <div class="warning-time">{{ item.time }}</div>
            </div>
            <el-empty v-if="warnings.length === 0" description="暂无预警" :image-size="50" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  getCostOverview,
  getCostTrend,
  getCostDistribution,
  getCostByNode,
  getCostComponents,
  getRouteComparison,
  getOptimizationSuggestions
} from '@/api/cost'

// 时间
const currentTime = ref('')
const costAlert = ref('')

// 动画值
const animatedValues = reactive({
  total_cost: 0,
  monthly_cost: 0,
  avg_cost: 0,
  saving_rate: 0
})

// KPI 数据
const costKpis = ref([
  { key: 'total_cost', label: '总运输成本', unit: '万', type: 'primary', percent: 78, trend: 5.2 },
  { key: 'monthly_cost', label: '本月成本', unit: '万', type: 'success', percent: 65, trend: -2.1 },
  { key: 'avg_cost', label: '平均成本', unit: '元', type: 'warning', percent: 82, trend: 3.5 },
  { key: 'saving_rate', label: '成本节省率', unit: '%', type: 'info', percent: 92, trend: 8.7 }
])

// 趋势数据
const trendDays = ref(30)
const trendStats = ref({ avgDaily: '2,450', maxDay: '03-22', trend: -3.2 })

// 成本构成
const composeData = ref([
  { name: '燃油成本', value: 125000, percent: 35, color: '#00d4ff' },
  { name: '过路费', value: 82000, percent: 23, color: '#00ff88' },
  { name: '人工成本', value: 95000, percent: 27, color: '#ffd93d' },
  { name: '折旧维护', value: 55000, percent: 15, color: '#ff6b6b' }
])

// 对比统计
const compareStats = ref({ saving: '12,350', rate: 18.5 })

// 优化建议
const suggestions = ref([
  { icon: '🛣️', title: '路线优化', description: '北京-上海线路可合并订单配送', saving: '3,200', priority: 'high' },
  { icon: '🚛', title: '车辆调度', description: '建议增加2辆新能源车', saving: '2,800', priority: 'medium' },
  { icon: '⛽', title: '燃油优化', description: '错峰加油可降低成本', saving: '1,500', priority: 'low' }
])

// 预警
const warnings = ref([
  { level: 'high', type: '成本超标', detail: '华南区域本月成本超预算15%', time: '10分钟前' },
  { level: 'medium', type: '油价波动', detail: '92号汽油价格上涨0.3元/升', time: '2小时前' },
  { level: 'low', type: '效率下降', detail: '京A12345车辆利用率下降10%', time: '昨天' }
])

// 图表引用
const trendChart = ref(null)
const composeChart = ref(null)
const routeChart = ref(null)
const compareChart = ref(null)
const nodeChart = ref(null)

let charts = []

// 安全初始化图表（防止重复初始化）
const initChart = (domRef) => {
  if (!domRef) return null
  
  // 检查是否已存在实例
  const existingInstance = echarts.getInstanceByDom(domRef)
  if (existingInstance) {
    existingInstance.dispose()
  }
  
  const chart = echarts.init(domRef)
  charts.push(chart)
  return chart
}

// 更新时间
const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', { hour12: false })
}

// 动画数字
const animateValue = (key, target, isPercent = false) => {
  const duration = 2000
  const start = animatedValues[key] || 0
  const increment = (target - start) / (duration / 16)
  let current = start
  const timer = setInterval(() => {
    current += increment
    if ((increment > 0 && current >= target) || (increment < 0 && current <= target) || increment === 0) {
      animatedValues[key] = isPercent ? target.toFixed(1) : (target >= 10000 ? (target / 10000).toFixed(1) : target.toFixed(0))
      clearInterval(timer)
    } else {
      animatedValues[key] = isPercent ? current.toFixed(1) : (current >= 10000 ? (current / 10000).toFixed(1) : Math.round(current))
    }
  }, 16)
}

// 随机点样式
const getDotStyle = (i) => ({
  left: `${Math.random() * 100}%`,
  top: `${Math.random() * 100}%`,
  animationDelay: `${Math.random() * 3}s`,
  animationDuration: `${2 + Math.random() * 3}s`
})

// 加载数据
const loadCostOverview = async () => {
  try {
    const res = await getCostOverview()
    animateValue('total_cost', res.total_cost || 156800)
    animateValue('monthly_cost', res.monthly_cost || 45600)
    animateValue('avg_cost', res.avg_cost || 2450)
    animateValue('saving_rate', res.cost_saving_rate || 18.5, true)
  } catch (e) {
    animateValue('total_cost', 156800)
    animateValue('monthly_cost', 45600)
    animateValue('avg_cost', 2450)
    animateValue('saving_rate', 18.5, true)
  }
}

const loadCostTrend = async () => {
  try {
    const res = await getCostTrend(trendDays.value)
    initTrendChart(res.trend || [])
  } catch (e) {
    initTrendChart([])
  }
}

const loadCostComponents = async () => {
  try {
    const res = await getCostComponents()
    if (res.components) {
      composeData.value = res.components.map((c, i) => ({
        ...c,
        color: ['#00d4ff', '#00ff88', '#ffd93d', '#ff6b6b'][i]
      }))
    }
    initComposeChart()
  } catch (e) {
    initComposeChart()
  }
}

const loadCostDistribution = async () => {
  try {
    const res = await getCostDistribution()
    initRouteChart(res.distribution || [])
  } catch (e) {
    initRouteChart([])
  }
}

const loadCostByNode = async () => {
  try {
    const res = await getCostByNode()
    initNodeChart(res.origin_costs || [], res.dest_costs || [])
  } catch (e) {
    initNodeChart([], [])
  }
}

const loadRouteComparison = async () => {
  try {
    const res = await getRouteComparison()
    initCompareChart(res.comparison || [])
  } catch (e) {
    initCompareChart([])
  }
}

const loadOptimizationSuggestions = async () => {
  try {
    const res = await getOptimizationSuggestions()
    if (res.suggestions) {
      suggestions.value = res.suggestions.map(s => ({
        icon: s.type === 'route' ? '🛣️' : s.type === 'vehicle' ? '🚛' : '⛽',
        title: s.title,
        description: s.description,
        saving: s.potential_saving?.toLocaleString() || '0',
        priority: s.priority || 'low'
      }))
    }
  } catch (e) {
    // 使用默认数据
  }
}

// 初始化图表
const initTrendChart = (data) => {
  const chart = initChart(trendChart.value)
  if (!chart) return
  
  const chartData = data.length > 0 ? data : Array.from({ length: trendDays.value }, (_, i) => ({
    date: new Date(Date.now() - (trendDays.value - i - 1) * 86400000).toISOString().split('T')[0],
    cost: 2000 + Math.random() * 1000
  }))
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'axis',
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: '#00d4ff',
      textStyle: { color: '#fff' },
      formatter: (params) => `${params[0].axisValue}<br/>成本: ¥${params[0].value.toFixed(0)}`
    },
    grid: { left: '5%', right: '5%', bottom: '10%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: chartData.map(d => d.date?.slice(5) || ''),
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 9, rotate: 45 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
    },
    series: [{
      type: 'line',
      data: chartData.map(d => d.cost),
      smooth: true,
      symbol: 'none',
      lineStyle: { 
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#00d4ff' },
          { offset: 1, color: '#00ff88' }
        ]),
        width: 3,
        shadowBlur: 10,
        shadowColor: 'rgba(0, 212, 255, 0.5)'
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(0, 212, 255, 0.4)' },
          { offset: 1, color: 'rgba(0, 212, 255, 0.02)' }
        ])
      }
    }]
  })
}

const initComposeChart = () => {
  const chart = initChart(composeChart.value)
  if (!chart) return
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'item',
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: '#00d4ff',
      textStyle: { color: '#fff' }
    },
    series: [{
      type: 'pie',
      radius: ['50%', '75%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 6,
        borderColor: 'rgba(0,0,0,0.3)',
        borderWidth: 3
      },
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#fff' }
      },
      data: composeData.value.map(d => ({
        name: d.name,
        value: d.value,
        itemStyle: { color: d.color }
      }))
    }]
  })
}

const initRouteChart = (data) => {
  const chart = initChart(routeChart.value)
  if (!chart) return
  
  const chartData = data.length > 0 ? data : [
    { name: '北京→上海', cost: 12500 },
    { name: '广州→深圳', cost: 9800 },
    { name: '成都→重庆', cost: 8500 },
    { name: '杭州→南京', cost: 7200 },
    { name: '武汉→长沙', cost: 6500 },
    { name: '西安→郑州', cost: 5800 },
    { name: '天津→石家庄', cost: 4500 },
    { name: '苏州→无锡', cost: 3800 },
    { name: '青岛→济南', cost: 3200 },
    { name: '厦门→福州', cost: 2800 }
  ]
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: '#00d4ff',
      textStyle: { color: '#fff' }
    },
    grid: { left: '3%', right: '8%', bottom: '5%', top: '5%', containLabel: true },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10, formatter: '¥{value}' }
    },
    yAxis: {
      type: 'category',
      data: chartData.map(d => d.name).reverse(),
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.7)', fontSize: 11 }
    },
    series: [{
      type: 'bar',
      data: chartData.map((d, i) => ({
        value: d.cost,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: 'rgba(0, 212, 255, 0.3)' },
            { offset: 1, color: ['#00d4ff', '#00ff88', '#ffd93d', '#ff6b6b', '#a855f7'][i % 5] }
          ]),
          borderRadius: [0, 4, 4, 0]
        }
      })),
      barWidth: '60%',
      label: { show: true, position: 'right', formatter: '¥{c}', color: 'rgba(255,255,255,0.7)', fontSize: 10 }
    }]
  })
}

const initCompareChart = (data) => {
  const chart = initChart(compareChart.value)
  if (!chart) return
  
  const chartData = data.length > 0 ? data : [
    { route_name: '北京→上海', amap_cost: 15000, local_cost: 12500, saving_rate: 17 },
    { route_name: '广州→深圳', amap_cost: 12000, local_cost: 9800, saving_rate: 18 },
    { route_name: '成都→重庆', amap_cost: 10000, local_cost: 8500, saving_rate: 15 },
    { route_name: '杭州→南京', amap_cost: 9000, local_cost: 7200, saving_rate: 20 }
  ]
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'axis',
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: '#00d4ff',
      textStyle: { color: '#fff' }
    },
    legend: { 
      data: ['高德地图', '本地算法'],
      textStyle: { color: 'rgba(255,255,255,0.7)' },
      bottom: 0
    },
    grid: { left: '5%', right: '5%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: chartData.map(d => d.route_name),
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 9, rotate: 20 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
    },
    series: [
      {
        name: '高德地图',
        type: 'bar',
        data: chartData.map(d => d.amap_cost),
        itemStyle: { 
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#ff6b6b' },
            { offset: 1, color: 'rgba(255, 107, 107, 0.3)' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        name: '本地算法',
        type: 'bar',
        data: chartData.map(d => d.local_cost),
        itemStyle: { 
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#00ff88' },
            { offset: 1, color: 'rgba(0, 255, 136, 0.3)' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  })
}

const initNodeChart = (originData, destData) => {
  const chart = initChart(nodeChart.value)
  if (!chart) return
  
  const nodes = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安']
  const origins = originData.length > 0 ? originData : nodes.map(n => ({ name: n, cost: 3000 + Math.random() * 5000 }))
  const dests = destData.length > 0 ? destData : nodes.map(n => ({ name: n, cost: 2000 + Math.random() * 4000 }))
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'axis',
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: '#00d4ff',
      textStyle: { color: '#fff' }
    },
    legend: { 
      data: ['发货成本', '收货成本'],
      textStyle: { color: 'rgba(255,255,255,0.7)' },
      bottom: 0
    },
    grid: { left: '5%', right: '5%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: nodes,
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
    },
    series: [
      {
        name: '发货成本',
        type: 'bar',
        data: origins.map(o => o.cost),
        itemStyle: { 
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#00d4ff' },
            { offset: 1, color: 'rgba(0, 212, 255, 0.3)' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        name: '收货成本',
        type: 'bar',
        data: dests.map(d => d.cost),
        itemStyle: { 
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#00ff88' },
            { offset: 1, color: 'rgba(0, 255, 136, 0.3)' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  })
}

// 刷新
const refreshAll = async () => {
  ElMessage.info('正在刷新...')
  await Promise.all([
    loadCostOverview(),
    loadCostTrend(),
    loadCostComponents(),
    loadCostDistribution(),
    loadCostByNode(),
    loadRouteComparison(),
    loadOptimizationSuggestions()
  ])
  ElMessage.success('刷新完成')
}

// 窗口调整
const handleResize = () => charts.forEach(c => c.resize())

let timeInterval = null

onMounted(async () => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
  
  await Promise.all([
    loadCostOverview(),
    loadCostTrend(),
    loadCostComponents(),
    loadCostDistribution(),
    loadCostByNode(),
    loadRouteComparison(),
    loadOptimizationSuggestions()
  ])
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
  window.removeEventListener('resize', handleResize)
  charts.forEach(c => c.dispose())
})
</script>

<style scoped>
.cost-analysis {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #0d1033 100%);
  padding: 16px;
  color: #fff;
  position: relative;
  overflow: hidden;
}

/* 背景效果 */
.bg-effects {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.grid-lines {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
}

.hex-pattern {
  position: absolute;
  inset: 0;
  opacity: 0.03;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='28' height='49' viewBox='0 0 28 49'%3E%3Cg fill-rule='evenodd'%3E%3Cg fill='%2300d4ff' fill-opacity='1'%3E%3Cpath d='M13.99 9.25l13 7.5v15l-13 7.5L1 31.75v-15l12.99-7.5zM3 17.9v12.7l10.99 6.34 11-6.35V17.9l-11-6.34L3 17.9zM0 15l12.98-7.5V0h-2v6.35L0 12.69v2.3zm0 18.5L12.98 41v8h-2v-6.85L0 35.81v-2.3zM15 0v7.5L27.99 15H28v-2.31h-.01L17 6.35V0h-2zm0 49v-8l12.99-7.5H28v2.31h-.01L17 42.15V49h-2z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}

.floating-dots .dot {
  position: absolute;
  width: 2px;
  height: 2px;
  background: #00d4ff;
  border-radius: 50%;
  animation: float-dot 4s infinite ease-in-out;
  opacity: 0.6;
}

@keyframes float-dot {
  0%, 100% { transform: translateY(0); opacity: 0.3; }
  50% { transform: translateY(-30px); opacity: 0.8; }
}

/* 顶部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px 20px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
  backdrop-filter: blur(10px);
}

.glow-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(90deg, #ffd93d, #ff6b6b);
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

.realtime-stats {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: rgba(0, 255, 136, 0.1);
  border-radius: 20px;
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.stat-pulse {
  width: 8px;
  height: 8px;
  background: #00ff88;
  border-radius: 50%;
  animation: pulse-glow 2s infinite;
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.5); }
  50% { box-shadow: 0 0 0 10px rgba(0, 255, 136, 0); }
}

.stat-label {
  font-size: 12px;
  color: #00ff88;
}

.stat-time {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  font-family: 'Courier New', monospace;
}

.cost-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(255, 107, 107, 0.15);
  border-radius: 8px;
  border: 1px solid rgba(255, 107, 107, 0.3);
  margin-right: 12px;
}

.alert-text {
  font-size: 12px;
  color: #ff6b6b;
}

/* KPI 卡片 */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.kpi-card {
  position: relative;
  padding: 20px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s;
}

.kpi-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 212, 255, 0.4);
  box-shadow: 0 12px 40px rgba(0, 212, 255, 0.2);
}

.kpi-card.primary { border-top: 3px solid #00d4ff; }
.kpi-card.success { border-top: 3px solid #00ff88; }
.kpi-card.warning { border-top: 3px solid #ffd93d; }
.kpi-card.info { border-top: 3px solid #a855f7; }

.kpi-bg {
  position: absolute;
  top: -50%;
  right: -50%;
  width: 150%;
  height: 150%;
  background: radial-gradient(circle, rgba(0, 212, 255, 0.1) 0%, transparent 60%);
  opacity: 0;
  transition: opacity 0.3s;
}

.kpi-card:hover .kpi-bg { opacity: 1; }

.kpi-ring {
  position: relative;
  width: 100px;
  height: 100px;
  margin: 0 auto 12px;
}

.kpi-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-bg {
  fill: none;
  stroke: rgba(0, 212, 255, 0.1);
  stroke-width: 8;
}

.ring-progress {
  fill: none;
  stroke: #00d4ff;
  stroke-width: 8;
  stroke-linecap: round;
  stroke-dasharray: 283;
  transition: stroke-dashoffset 2s ease;
}

.kpi-card.success .ring-progress { stroke: #00ff88; }
.kpi-card.warning .ring-progress { stroke: #ffd93d; }
.kpi-card.info .ring-progress { stroke: #a855f7; }

.kpi-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.kpi-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #fff;
}

.kpi-unit {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
}

.kpi-info {
  text-align: center;
}

.kpi-label {
  display: block;
  font-size: 13px;
  color: rgba(255,255,255,0.6);
  margin-bottom: 6px;
}

.kpi-trend {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.kpi-trend.up {
  background: rgba(0, 255, 136, 0.15);
  color: #00ff88;
}

.kpi-trend.down {
  background: rgba(255, 107, 107, 0.15);
  color: #ff6b6b;
}

/* 主网格 */
.main-grid {
  display: grid;
  grid-template-columns: 300px 1fr 300px;
  gap: 12px;
}

/* 面板卡片 */
.panel-card {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 12px;
  padding: 12px;
  backdrop-filter: blur(5px);
  margin-bottom: 12px;
}

.panel-card.large {
  margin-bottom: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.header-deco {
  display: flex;
  align-items: center;
  gap: 4px;
}

.deco-line {
  width: 16px;
  height: 2px;
  background: linear-gradient(90deg, #ffd93d, transparent);
}

.deco-dot {
  width: 5px;
  height: 5px;
  background: #ffd93d;
  border-radius: 50%;
}

.card-title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.chart-area {
  height: 180px;
}

.chart-area.large {
  height: 280px;
}

/* 趋势统计 */
.trend-stats {
  display: flex;
  justify-content: space-around;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.stat-item {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 10px;
  color: rgba(255,255,255,0.5);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.stat-value.up { color: #00ff88; }
.stat-value.down { color: #ff6b6b; }

/* 成本构成图例 */
.compose-legend {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 11px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-name {
  flex: 1;
  color: rgba(255,255,255,0.7);
}

.legend-value {
  color: #fff;
  font-weight: 500;
}

.legend-percent {
  width: 40px;
  text-align: right;
  color: rgba(255,255,255,0.5);
}

/* 对比汇总 */
.compare-summary {
  margin-top: 12px;
  padding: 12px;
  background: rgba(0, 255, 136, 0.1);
  border-radius: 8px;
  border: 1px solid rgba(0, 255, 136, 0.2);
}

.compare-item {
  text-align: center;
}

.compare-label {
  display: block;
  font-size: 11px;
  color: rgba(255,255,255,0.5);
  margin-bottom: 4px;
}

.compare-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #00ff88;
}

.compare-percent {
  font-size: 12px;
  color: #00ff88;
}

/* 优化建议 */
.suggestions-list {
  max-height: 260px;
  overflow-y: auto;
}

.suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px;
  margin-bottom: 8px;
  background: rgba(0, 212, 255, 0.03);
  border-radius: 8px;
  border-left: 3px solid rgba(0, 212, 255, 0.3);
  transition: all 0.3s;
}

.suggestion-item:hover {
  background: rgba(0, 212, 255, 0.08);
}

.suggestion-item.priority-high { border-left-color: #ff6b6b; }
.suggestion-item.priority-medium { border-left-color: #ffd93d; }
.suggestion-item.priority-low { border-left-color: #00d4ff; }

.suggestion-icon {
  font-size: 20px;
}

.suggestion-content {
  flex: 1;
}

.suggestion-title {
  font-size: 12px;
  font-weight: 500;
  color: #fff;
  margin-bottom: 4px;
}

.suggestion-desc {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
  margin-bottom: 6px;
}

.suggestion-saving {
  font-size: 10px;
}

.saving-label {
  color: rgba(255,255,255,0.4);
  margin-right: 6px;
}

.saving-value {
  color: #00ff88;
  font-weight: 600;
}

.suggestion-priority {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
}

.suggestion-priority.high { background: #ff6b6b; color: #fff; }
.suggestion-priority.medium { background: #ffd93d; color: #000; }
.suggestion-priority.low { background: rgba(255,255,255,0.1); color: #fff; }

/* 预警列表 */
.warnings-list {
  max-height: 200px;
  overflow-y: auto;
}

.warning-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  margin-bottom: 8px;
  background: rgba(255, 107, 107, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(255, 107, 107, 0.2);
}

.warning-item.medium {
  background: rgba(255, 217, 61, 0.05);
  border-color: rgba(255, 217, 61, 0.2);
}

.warning-item.low {
  background: rgba(0, 255, 136, 0.05);
  border-color: rgba(0, 255, 136, 0.2);
}

.warning-icon {
  font-size: 16px;
}

.warning-content {
  flex: 1;
}

.warning-type {
  font-size: 11px;
  font-weight: 500;
  color: #fff;
}

.warning-detail {
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

.warning-time {
  font-size: 10px;
  color: rgba(255,255,255,0.4);
}

/* Element Plus 覆盖 */
:deep(.el-tag) {
  background: rgba(255, 217, 61, 0.2);
  border-color: rgba(255, 217, 61, 0.3);
  color: #ffd93d;
}

:deep(.el-radio-button__inner) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  color: rgba(255,255,255,0.6);
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #ffd93d;
  border-color: #ffd93d;
  color: #000;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #ffd93d, #ff6b6b);
  border: none;
  color: #000;
}

:deep(.el-badge__content) {
  background: #ff6b6b;
  border-color: #ff6b6b;
}

:deep(.el-empty__description p) {
  color: rgba(255,255,255,0.4);
}
</style>