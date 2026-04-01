<template>
  <div class="analytics-page">
    <!-- 背景动效 -->
    <div class="bg-effects">
      <div class="grid-lines"></div>
      <div class="scan-line"></div>
    </div>

    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="glow-title">📊 智能数据分析中心</h1>
        <span class="subtitle">INTELLIGENT DATA ANALYTICS</span>
      </div>
      <div class="header-right">
        <div class="ai-status">
          <span class="ai-pulse"></span>
          <span class="ai-text">AI 引擎运行中</span>
        </div>
        <el-button type="primary" size="small" @click="refreshAll">
          <el-icon><Refresh /></el-icon> 刷新数据
        </el-button>
      </div>
    </div>

    <!-- KPI 核心指标 -->
    <div class="kpi-section">
      <div class="kpi-grid">
        <div v-for="(kpi, index) in kpiCards" :key="index" class="kpi-card" :class="kpi.type">
          <div class="kpi-glow"></div>
          <div class="kpi-header">
            <span class="kpi-icon">{{ kpi.icon }}</span>
            <span class="kpi-name">{{ kpi.name }}</span>
          </div>
          <div class="kpi-value">
            <span class="value-main">{{ animatedKpi[kpi.key] }}</span>
            <span class="value-unit">{{ kpi.unit }}</span>
          </div>
          <div class="kpi-trend" :class="kpi.trend > 0 ? 'up' : 'down'">
            <span class="trend-arrow">{{ kpi.trend > 0 ? '↑' : '↓' }}</span>
            <span class="trend-value">{{ Math.abs(kpi.trend) }}%</span>
            <span class="trend-label">较昨日</span>
          </div>
          <div class="kpi-sparkline">
            <svg viewBox="0 0 100 30" preserveAspectRatio="none">
              <polyline :points="kpi.sparkline" fill="none" stroke="currentColor" stroke-width="2"/>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- 主要分析区域 -->
    <div class="main-grid">
      <!-- 左侧：预测与洞察 -->
      <div class="left-panel">
        <!-- 需求预测 -->
        <div class="panel-card">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="header-title">🔮 AI 需求预测</span>
            <el-radio-group v-model="predictDays" size="small" @change="loadPrediction">
              <el-radio-button :value="7">7天</el-radio-button>
              <el-radio-button :value="14">14天</el-radio-button>
              <el-radio-button :value="30">30天</el-radio-button>
            </el-radio-group>
          </div>
          <div ref="predictChart" class="chart-area"></div>
          <div class="predict-summary">
            <div class="summary-item">
              <span class="summary-label">预测总订单</span>
              <span class="summary-value">{{ predictSummary.total }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">峰值日</span>
              <span class="summary-value">{{ predictSummary.peakDay }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">置信度</span>
              <span class="summary-value highlight">{{ predictSummary.confidence }}%</span>
            </div>
          </div>
        </div>

        <!-- AI 智能洞察 -->
        <div class="panel-card">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="header-title">💡 AI 智能洞察</span>
            <el-tag size="small" effect="dark" type="success">实时分析</el-tag>
          </div>
          <div class="insights-list">
            <div 
              v-for="(insight, index) in aiInsights" 
              :key="index" 
              class="insight-item"
              :class="insight.level"
            >
              <div class="insight-icon">
                {{ insight.icon }}
              </div>
              <div class="insight-content">
                <div class="insight-title">{{ insight.title }}</div>
                <div class="insight-desc">{{ insight.description }}</div>
              </div>
              <div class="insight-score" v-if="insight.score">
                <el-progress 
                  type="circle" 
                  :percentage="insight.score" 
                  :width="40"
                  :stroke-width="4"
                  :color="insight.score >= 80 ? '#00ff88' : insight.score >= 60 ? '#ffd93d' : '#ff6b6b'"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 中间：趋势分析 -->
      <div class="center-panel">
        <!-- 订单趋势 -->
        <div class="panel-card">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="header-title">📈 订单趋势分析</span>
            <el-radio-group v-model="trendRange" size="small" @change="loadTrend">
              <el-radio-button :value="7">7天</el-radio-button>
              <el-radio-button :value="30">30天</el-radio-button>
              <el-radio-button :value="90">90天</el-radio-button>
            </el-radio-group>
          </div>
          <div ref="trendChart" class="chart-area large"></div>
        </div>

        <!-- 车辆效率分析 -->
        <div class="panel-card half">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="header-title">🚛 车辆效率矩阵</span>
          </div>
          <div ref="vehicleChart" class="chart-area"></div>
        </div>

        <!-- 订单热力图 -->
        <div class="panel-card half">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="header-title">🔥 订单热力分布</span>
          </div>
          <div ref="heatmapChart" class="chart-area"></div>
        </div>
      </div>

      <!-- 右侧：数据质量与报表 -->
      <div class="right-panel">
        <!-- 数据质量监控 -->
        <div class="panel-card">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="header-title">✅ 数据质量监控</span>
          </div>
          <div class="quality-metrics">
            <div v-for="(metric, index) in qualityMetrics" :key="index" class="quality-item">
              <div class="quality-header">
                <span class="quality-name">{{ metric.name }}</span>
                <span class="quality-value" :class="metric.status">{{ metric.value }}%</span>
              </div>
              <el-progress 
                :percentage="metric.value" 
                :stroke-width="6"
                :color="metric.value >= 90 ? '#00ff88' : metric.value >= 70 ? '#ffd93d' : '#ff6b6b'"
                :show-text="false"
              />
              <div class="quality-bar-bg"></div>
            </div>
          </div>
        </div>

        <!-- 异常检测 -->
        <div class="panel-card">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="header-title">⚠️ 异常检测</span>
            <el-badge :value="anomalies.length" type="danger" />
          </div>
          <div class="anomaly-list">
            <div 
              v-for="(item, index) in anomalies" 
              :key="index" 
              class="anomaly-item"
            >
              <div class="anomaly-level" :class="item.level">
                {{ item.level === 'high' ? '高' : item.level === 'medium' ? '中' : '低' }}
              </div>
              <div class="anomaly-info">
                <div class="anomaly-type">{{ item.type }}</div>
                <div class="anomaly-detail">{{ item.detail }}</div>
              </div>
              <div class="anomaly-time">{{ item.time }}</div>
            </div>
            <el-empty v-if="anomalies.length === 0" description="暂无异常" :image-size="60" />
          </div>
        </div>

        <!-- 报表导出 -->
        <div class="panel-card export-card">
          <div class="card-header">
            <div class="header-deco">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="header-title">📥 智能报表导出</span>
          </div>
          <div class="export-form">
            <el-form label-position="top" size="small">
              <el-form-item label="报表类型">
                <el-select v-model="reportType" style="width: 100%">
                  <el-option label="日报表" value="daily" />
                  <el-option label="周报表" value="weekly" />
                  <el-option label="月报表" value="monthly" />
                  <el-option label="预测报告" value="prediction" />
                </el-select>
              </el-form-item>
              <el-form-item label="日期范围">
                <el-date-picker
                  v-model="reportDateRange"
                  type="daterange"
                  range-separator="至"
                  start-placeholder="开始"
                  end-placeholder="结束"
                  value-format="YYYY-MM-DD"
                  style="width: 100%"
                />
              </el-form-item>
              <el-form-item label="包含内容">
                <el-checkbox-group v-model="reportContent">
                  <el-checkbox value="orders">订单数据</el-checkbox>
                  <el-checkbox value="vehicles">车辆数据</el-checkbox>
                  <el-checkbox value="prediction">预测分析</el-checkbox>
                  <el-checkbox value="insights">AI洞察</el-checkbox>
                </el-checkbox-group>
              </el-form-item>
            </el-form>
            <div class="export-actions">
              <el-button type="success" @click="handleExportExcel" :loading="exporting">
                <el-icon><Download /></el-icon>
                导出 Excel
              </el-button>
              <el-button type="primary" @click="handleExportPDF" :loading="exporting">
                <el-icon><Download /></el-icon>
                导出 PDF
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { Refresh, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  getDashboard,
  getTrend,
  getVehiclePerformance,
  predictDemand,
  generateReport,
  exportExcel,
  exportPDF
} from '@/api/analytics'

// KPI 数据
const kpiCards = ref([
  { 
    name: '订单完成率', key: 'completion_rate', icon: '✅', unit: '%', type: 'success',
    trend: 5.2, sparkline: '0,15 10,12 20,18 30,20 40,15 50,22 60,25 70,20 80,28 90,30 100,35'
  },
  { 
    name: '准时送达率', key: 'on_time_rate', icon: '⏰', unit: '%', type: 'warning',
    trend: 2.1, sparkline: '0,20 10,22 20,18 30,25 40,20 50,28 60,22 70,30 80,25 90,32 100,30'
  },
  { 
    name: '平均配送时长', key: 'avg_delivery_time', icon: '🚀', unit: '分钟', type: 'info',
    trend: -3.5, sparkline: '0,30 10,28 20,25 30,22 40,20 50,18 60,15 70,12 80,10 90,8 100,5'
  },
  { 
    name: '客户满意度', key: 'satisfaction', icon: '😊', unit: '分', type: 'primary',
    trend: 1.8, sparkline: '0,10 10,12 20,15 30,14 40,18 50,20 60,22 70,25 80,28 90,30 100,32'
  }
])

const animatedKpi = reactive({
  completion_rate: 0,
  on_time_rate: 0,
  avg_delivery_time: 0,
  satisfaction: 0
})

// 预测
const predictDays = ref(7)
const predictions = ref([])
const predictSummary = ref({
  total: 0,
  peakDay: '-',
  confidence: 92
})

// 趋势
const trendRange = ref(7)
const trendData = ref([])

// AI 洞察
const aiInsights = ref([
  { icon: '🎯', title: '配送效率优化建议', description: '建议增加北京-上海线路车辆配置，可提升15%效率', level: 'info', score: 85 },
  { icon: '⚡', title: '高峰时段预警', description: '明日10:00-12:00预计订单量激增30%，建议提前调度', level: 'warning', score: 78 },
  { icon: '💡', title: '成本节约机会', description: '合并相似路线可节省约 ¥2,500/天', level: 'success', score: 92 }
])

// 数据质量
const qualityMetrics = ref([
  { name: '数据完整性', value: 98, status: 'good' },
  { name: '数据准确性', value: 95, status: 'good' },
  { name: '数据及时性', value: 92, status: 'good' },
  { name: '数据一致性', value: 88, status: 'warning' }
])

// 异常检测
const anomalies = ref([
  { level: 'high', type: '订单异常', detail: '订单 #12345 配送延迟超过2小时', time: '10分钟前' },
  { level: 'medium', type: '车辆告警', detail: '京A12345 油量低于20%', time: '30分钟前' },
  { level: 'low', type: '数据波动', detail: '华南区域订单量下降10%', time: '1小时前' }
])

// 报表导出
const reportType = ref('daily')
const reportDateRange = ref([])
const reportContent = ref(['orders', 'prediction'])
const exporting = ref(false)

// 图表引用
const predictChart = ref(null)
const trendChart = ref(null)
const vehicleChart = ref(null)
const heatmapChart = ref(null)

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

// 加载数据
const loadDashboard = async () => {
  try {
    const res = await getDashboard()
    if (res.success) {
      // 更新 KPI
      animateKpi('completion_rate', res.metrics?.completion_rate || 94)
      animateKpi('on_time_rate', res.metrics?.on_time_rate || 89)
      animateKpi('avg_delivery_time', res.metrics?.avg_delivery_time || 45)
      animateKpi('satisfaction', res.metrics?.satisfaction || 4.8)
    }
  } catch (e) {
    console.error('加载仪表盘失败:', e)
    // 使用默认值
    animateKpi('completion_rate', 94)
    animateKpi('on_time_rate', 89)
    animateKpi('avg_delivery_time', 45)
    animateKpi('satisfaction', 4.8)
  }
}

const loadPrediction = async () => {
  try {
    const res = await predictDemand(predictDays.value)
    if (res.success) {
      predictions.value = res.predictions || []
      initPredictChart()
      
      // 计算汇总
      const total = predictions.value.reduce((sum, p) => sum + (p.predicted_orders || 0), 0)
      const peak = predictions.value.reduce((max, p) => 
        (p.predicted_orders > max.predicted_orders) ? p : max, predictions.value[0] || {})
      predictSummary.value = {
        total,
        peakDay: peak.date?.slice(5) || '-',
        confidence: 92
      }
    }
  } catch (e) {
    console.error('加载预测失败:', e)
    // 使用模拟数据
    predictions.value = Array.from({ length: predictDays.value }, (_, i) => ({
      date: new Date(Date.now() + (i + 1) * 86400000).toISOString().split('T')[0],
      predicted_orders: Math.floor(50 + Math.random() * 30)
    }))
    initPredictChart()
  }
}

const loadTrend = async () => {
  try {
    const endDate = new Date().toISOString().split('T')[0]
    const startDate = new Date(Date.now() - trendRange.value * 86400000).toISOString().split('T')[0]
    const res = await getTrend({ start_date: startDate, end_date: endDate })
    if (res.success) {
      trendData.value = res.trend || []
      initTrendChart()
    }
  } catch (e) {
    console.error('加载趋势失败:', e)
    // 使用模拟数据
    trendData.value = Array.from({ length: trendRange.value }, (_, i) => ({
      date: new Date(Date.now() - (trendRange.value - i - 1) * 86400000).toISOString().split('T')[0],
      orders: Math.floor(40 + Math.random() * 40),
      revenue: Math.floor(5000 + Math.random() * 3000)
    }))
    initTrendChart()
  }
}

const loadVehiclePerformance = async () => {
  try {
    const res = await getVehiclePerformance()
    if (res.success) {
      initVehicleChart(res.vehicles || [])
    }
  } catch (e) {
    console.error('加载车辆性能失败:', e)
    initVehicleChart([])
  }
}

// 动画 KPI
const animateKpi = (key, target) => {
  const duration = 2000
  const start = animatedKpi[key] || 0
  const increment = (target - start) / (duration / 16)
  let current = start
  const timer = setInterval(() => {
    current += increment
    if ((increment > 0 && current >= target) || (increment < 0 && current <= target) || increment === 0) {
      animatedKpi[key] = target
      clearInterval(timer)
    } else {
      animatedKpi[key] = Math.round(current * 10) / 10
    }
  }, 16)
}

// 初始化图表
const initPredictChart = () => {
  const chart = initChart(predictChart.value)
  if (!chart) return
  
  const data = predictions.value
  if (!data.length) return
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'axis',
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: '#00d4ff',
      textStyle: { color: '#fff' }
    },
    grid: { left: '5%', right: '5%', bottom: '10%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map(d => d.date?.slice(5) || ''),
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10, rotate: 30 }
    },
    yAxis: {
      type: 'value',
      name: '预测订单',
      nameTextStyle: { color: 'rgba(255,255,255,0.5)' },
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)' }
    },
    series: [{
      type: 'line',
      data: data.map(d => d.predicted_orders),
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { color: '#9b59b6', width: 3, shadowBlur: 10, shadowColor: 'rgba(155, 89, 182, 0.5)' },
      itemStyle: { color: '#9b59b6', borderColor: '#fff', borderWidth: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(155, 89, 182, 0.4)' },
          { offset: 1, color: 'rgba(155, 89, 182, 0.05)' }
        ])
      }
    }]
  })
}

const initTrendChart = () => {
  const chart = initChart(trendChart.value)
  if (!chart) return
  
  const data = trendData.value
  if (!data.length) return
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'axis',
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: '#00d4ff',
      textStyle: { color: '#fff' }
    },
    legend: { 
      data: ['订单数', '收入'],
      textStyle: { color: 'rgba(255,255,255,0.7)' },
      bottom: 0
    },
    grid: { left: '5%', right: '5%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map(d => d.date?.slice(5) || ''),
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10, rotate: 45 }
    },
    yAxis: [
      { 
        type: 'value', 
        name: '订单',
        nameTextStyle: { color: 'rgba(255,255,255,0.5)' },
        splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
        axisLabel: { color: 'rgba(255,255,255,0.6)' }
      },
      { 
        type: 'value', 
        name: '收入(元)',
        nameTextStyle: { color: 'rgba(255,255,255,0.5)' },
        splitLine: { show: false },
        axisLabel: { color: 'rgba(255,255,255,0.6)' }
      }
    ],
    series: [
      {
        name: '订单数',
        type: 'bar',
        data: data.map(d => d.orders),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#00d4ff' },
            { offset: 1, color: 'rgba(0, 212, 255, 0.3)' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        name: '收入',
        type: 'line',
        yAxisIndex: 1,
        data: data.map(d => d.revenue),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: '#00ff88', width: 2 },
        itemStyle: { color: '#00ff88' }
      }
    ]
  })
}

const initVehicleChart = (vehicles) => {
  const chart = initChart(vehicleChart.value)
  if (!chart) return
  
  const data = vehicles.length > 0 ? vehicles.slice(0, 5) : [
    { plate_number: '京A12345', utilization: 92 },
    { plate_number: '京B67890', utilization: 85 },
    { plate_number: '京C24680', utilization: 78 },
    { plate_number: '京D13579', utilization: 95 },
    { plate_number: '京E86420', utilization: 70 }
  ]
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'axis',
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: '#00d4ff',
      textStyle: { color: '#fff' }
    },
    grid: { left: '5%', right: '5%', bottom: '10%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map(v => v.plate_number),
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 9, rotate: 20 }
    },
    yAxis: {
      type: 'value',
      max: 100,
      name: '利用率%',
      nameTextStyle: { color: 'rgba(255,255,255,0.5)' },
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)' }
    },
    series: [{
      type: 'bar',
      data: data.map((v, i) => ({
        value: v.utilization,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: ['#00ff88', '#00d4ff', '#ffd93d', '#ff6b6b', '#a855f7'][i] },
            { offset: 1, color: ['rgba(0,255,136,0.3)', 'rgba(0,212,255,0.3)', 'rgba(255,217,61,0.3)', 'rgba(255,107,107,0.3)', 'rgba(168,85,247,0.3)'][i] }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      })),
      label: { show: true, position: 'top', formatter: '{c}%', fontSize: 9, color: 'rgba(255,255,255,0.7)' }
    }]
  })
}

const initHeatmapChart = () => {
  const chart = initChart(heatmapChart.value)
  if (!chart) return
  
  // 模拟热力图数据（小时 x 星期）
  const hours = ['0时', '3时', '6时', '9时', '12时', '15时', '18时', '21时']
  const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const data = []
  
  for (let i = 0; i < days.length; i++) {
    for (let j = 0; j < hours.length; j++) {
      data.push([j, i, Math.floor(Math.random() * 100)])
    }
  }
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      position: 'top',
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: '#00d4ff',
      textStyle: { color: '#fff' },
      formatter: (params) => `${days[params.value[1]]} ${hours[params.value[0]]}: ${params.value[2]}单`
    },
    grid: { left: '12%', right: '5%', bottom: '15%', top: '5%', containLabel: true },
    xAxis: {
      type: 'category',
      data: hours,
      splitArea: { show: true },
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 9 }
    },
    yAxis: {
      type: 'category',
      data: days,
      splitArea: { show: true },
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
    },
    visualMap: {
      min: 0,
      max: 100,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#0a0e27', '#00d4ff', '#00ff88', '#ffd93d', '#ff6b6b']
      },
      textStyle: { color: 'rgba(255,255,255,0.6)' }
    },
    series: [{
      type: 'heatmap',
      data: data,
      label: { show: false },
      emphasis: {
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }
      }
    }]
  })
}

// 导出
const handleExportExcel = async () => {
  exporting.value = true
  try {
    await exportExcel({
      type: reportType.value,
      start_date: reportDateRange.value?.[0],
      end_date: reportDateRange.value?.[1],
      content: reportContent.value
    })
    ElMessage.success('Excel 导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

const handleExportPDF = async () => {
  exporting.value = true
  try {
    await exportPDF({
      type: reportType.value,
      start_date: reportDateRange.value?.[0],
      end_date: reportDateRange.value?.[1],
      content: reportContent.value
    })
    ElMessage.success('PDF 导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

// 刷新所有数据
const refreshAll = async () => {
  ElMessage.info('正在刷新数据...')
  await Promise.all([
    loadDashboard(),
    loadPrediction(),
    loadTrend(),
    loadVehiclePerformance()
  ])
  ElMessage.success('数据已刷新')
}

// 窗口调整
const handleResize = () => charts.forEach(c => c.resize())

onMounted(async () => {
  await nextTick()
  
  await Promise.all([
    loadDashboard(),
    loadPrediction(),
    loadTrend(),
    loadVehiclePerformance()
  ])
  
  initHeatmapChart()
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  charts.forEach(c => c.dispose())
})
</script>

<style scoped>
.analytics-page {
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

.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.5), transparent);
  animation: scan 4s linear infinite;
}

@keyframes scan {
  0% { top: 0; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { top: 100%; opacity: 0; }
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
  background: linear-gradient(90deg, #00d4ff, #00ff88);
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

.ai-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(0, 255, 136, 0.1);
  border-radius: 20px;
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.ai-pulse {
  width: 8px;
  height: 8px;
  background: #00ff88;
  border-radius: 50%;
  animation: ai-pulse 2s infinite;
}

@keyframes ai-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.5); }
  50% { box-shadow: 0 0 0 8px rgba(0, 255, 136, 0); }
}

.ai-text {
  font-size: 12px;
  color: #00ff88;
}

/* KPI 卡片 */
.kpi-section {
  margin-bottom: 16px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.kpi-card {
  position: relative;
  padding: 16px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s;
}

.kpi-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 212, 255, 0.4);
  box-shadow: 0 8px 32px rgba(0, 212, 255, 0.15);
}

.kpi-card.success { border-left: 3px solid #00ff88; }
.kpi-card.warning { border-left: 3px solid #ffd93d; }
.kpi-card.info { border-left: 3px solid #00d4ff; }
.kpi-card.primary { border-left: 3px solid #a855f7; }

.kpi-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(0, 212, 255, 0.1) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.3s;
}

.kpi-card:hover .kpi-glow { opacity: 1; }

.kpi-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.kpi-icon {
  font-size: 20px;
}

.kpi-name {
  font-size: 12px;
  color: rgba(255,255,255,0.6);
}

.kpi-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 8px;
}

.value-main {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}

.value-unit {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
}

.kpi-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  margin-bottom: 8px;
}

.kpi-trend.up { color: #00ff88; }
.kpi-trend.down { color: #ff6b6b; }

.trend-arrow {
  font-weight: bold;
}

.kpi-sparkline {
  height: 24px;
  opacity: 0.6;
}

.kpi-sparkline svg {
  width: 100%;
  height: 100%;
}

.kpi-sparkline polyline {
  stroke: #00d4ff;
  fill: none;
}

/* 主网格 */
.main-grid {
  display: grid;
  grid-template-columns: 280px 1fr 280px;
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

.panel-card.half {
  width: calc(50% - 6px);
  display: inline-block;
}

.panel-card.half:nth-child(2n) {
  margin-left: 12px;
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
  background: linear-gradient(90deg, #00d4ff, transparent);
}

.deco-dot {
  width: 5px;
  height: 5px;
  background: #00d4ff;
  border-radius: 50%;
}

.header-title {
  flex: 1;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.chart-area {
  height: 180px;
}

.chart-area.large {
  height: 220px;
}

/* 预测汇总 */
.predict-summary {
  display: flex;
  justify-content: space-around;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.summary-item {
  text-align: center;
}

.summary-label {
  display: block;
  font-size: 10px;
  color: rgba(255,255,255,0.5);
  margin-bottom: 4px;
}

.summary-value {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.summary-value.highlight {
  color: #00ff88;
}

/* AI 洞察 */
.insights-list {
  max-height: 240px;
  overflow-y: auto;
}

.insight-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px;
  margin-bottom: 8px;
  background: rgba(0, 212, 255, 0.03);
  border-radius: 8px;
  border-left: 2px solid rgba(0, 212, 255, 0.3);
  transition: all 0.3s;
}

.insight-item:hover {
  background: rgba(0, 212, 255, 0.08);
}

.insight-item.info { border-left-color: #00d4ff; }
.insight-item.warning { border-left-color: #ffd93d; }
.insight-item.success { border-left-color: #00ff88; }

.insight-icon {
  font-size: 20px;
}

.insight-content {
  flex: 1;
}

.insight-title {
  font-size: 12px;
  font-weight: 500;
  color: #fff;
  margin-bottom: 4px;
}

.insight-desc {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
  line-height: 1.4;
}

.insight-score {
  flex-shrink: 0;
}

/* 数据质量 */
.quality-metrics {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quality-item {
  padding: 8px;
  background: rgba(0, 212, 255, 0.03);
  border-radius: 8px;
}

.quality-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.quality-name {
  font-size: 12px;
  color: rgba(255,255,255,0.7);
}

.quality-value {
  font-size: 13px;
  font-weight: 600;
}

.quality-value.good { color: #00ff88; }
.quality-value.warning { color: #ffd93d; }

/* 异常检测 */
.anomaly-list {
  max-height: 200px;
  overflow-y: auto;
}

.anomaly-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  margin-bottom: 8px;
  background: rgba(255, 107, 107, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(255, 107, 107, 0.2);
}

.anomaly-level {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.anomaly-level.high { background: #ff6b6b; color: #fff; }
.anomaly-level.medium { background: #ffd93d; color: #000; }
.anomaly-level.low { background: rgba(255,255,255,0.1); color: #fff; }

.anomaly-info {
  flex: 1;
}

.anomaly-type {
  font-size: 11px;
  font-weight: 500;
  color: #fff;
}

.anomaly-detail {
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

.anomaly-time {
  font-size: 10px;
  color: rgba(255,255,255,0.4);
}

/* 导出卡片 */
.export-card {
  margin-bottom: 0;
}

.export-form {
  padding: 8px 0;
}

.export-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.export-actions .el-button {
  flex: 1;
}

/* Element Plus 覆盖 */
:deep(.el-tag) {
  background: rgba(0, 212, 255, 0.2);
  border-color: rgba(0, 212, 255, 0.3);
  color: #00d4ff;
}

:deep(.el-radio-button__inner) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  color: rgba(255,255,255,0.6);
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #00d4ff;
  border-color: #00d4ff;
  color: #000;
}

:deep(.el-select .el-input__wrapper) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  box-shadow: none;
}

:deep(.el-select .el-input__inner) {
  color: #fff;
}

:deep(.el-date-editor) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
}

:deep(.el-date-editor .el-input__inner) {
  color: #fff;
}

:deep(.el-checkbox__label) {
  color: rgba(255,255,255,0.7);
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background: #00d4ff;
  border-color: #00d4ff;
}

:deep(.el-progress-bar__outer) {
  background: rgba(0, 212, 255, 0.1);
}

:deep(.el-empty__description p) {
  color: rgba(255,255,255,0.4);
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #00d4ff, #00ff88);
  border: none;
  color: #000;
}

:deep(.el-button--success) {
  background: linear-gradient(135deg, #00ff88, #00d4ff);
  border: none;
  color: #000;
}
</style>
