<template>
  <div class="big-data-screen">
    <!-- 顶部标题 -->
    <header class="screen-header">
      <h1>📊 物流大数据实时分析平台</h1>
      <div class="header-info">
        <span>Kafka: {{ kafkaStatus ? '✅ 已连接' : '❌ 未连接' }}</span>
        <span>{{ currentTime }}</span>
      </div>
    </header>

    <!-- 主内容 -->
    <main class="screen-main">
      <!-- 核心指标 -->
      <section class="metrics-row">
        <div class="metric-card">
          <div class="metric-value">{{ stats.totalOrders }}</div>
          <div class="metric-label">总订单数</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{{ stats.todayOrders }}</div>
          <div class="metric-label">今日订单</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">{{ stats.totalVehicles }}</div>
          <div class="metric-label">车辆总数</div>
        </div>
        <div class="metric-card">
          <div class="metric-value">¥{{ formatNumber(stats.totalCost) }}</div>
          <div class="metric-label">总成本</div>
        </div>
      </section>

      <!-- 图表区域 -->
      <section class="charts-row">
        <div class="chart-card">
          <h3>📦 订单状态分布</h3>
          <div ref="orderChartRef" class="chart-box"></div>
        </div>
        <div class="chart-card">
          <h3>🚛 车辆状态</h3>
          <div ref="vehicleChartRef" class="chart-box"></div>
        </div>
        <div class="chart-card">
          <h3>📈 本周订单趋势</h3>
          <div ref="trendChartRef" class="chart-box"></div>
        </div>
      </section>

      <!-- 实时日志 -->
      <section class="log-section">
        <h3>🔔 实时数据流</h3>
        <div class="log-box">
          <div v-for="(log, i) in recentLogs" :key="i" class="log-item" :class="log.type">
            <span class="log-time">{{ log.time }}</span>
            <span class="log-msg">{{ log.message }}</span>
          </div>
        </div>
      </section>

      <!-- Spark 分析结果 -->
      <section class="spark-section">
        <h3>🔮 智能预测分析 (Spark MLlib)</h3>
        <div class="spark-grid">
          <!-- 需求预测 -->
          <div class="spark-card">
            <h4>📊 未来7天需求预测</h4>
            <div class="prediction-list">
              <div v-for="item in demandPredictions" :key="item.region" class="prediction-item">
                <span class="region-name">{{ item.region }}</span>
                <span class="demand-value">{{ item.avg_demand }} 单/日</span>
                <span class="demand-status" :class="item.status">{{ item.status === 'high' ? '⚠️ 高峰' : item.status === 'medium' ? '📊 正常' : '✅ 平稳' }}</span>
              </div>
            </div>
          </div>

          <!-- 车辆调配建议 -->
          <div class="spark-card">
            <h4>🚚 车辆调配建议</h4>
            <div class="suggestion-list">
              <div v-for="item in vehicleSuggestions" :key="item.region" class="suggestion-item">
                <span class="region-name">{{ item.region }}</span>
                <span class="vehicles">建议 {{ item.vehicles_suggested }} 辆</span>
                <span class="note">{{ item.note }}</span>
              </div>
            </div>
          </div>

          <!-- 供应链瓶颈 -->
          <div class="spark-card">
            <h4>⚠️ 供应链瓶颈识别</h4>
            <div class="bottleneck-list">
              <div v-for="item in bottlenecks" :key="item.id" class="bottleneck-item">
                <span class="node-name">{{ item.name }}</span>
                <span class="score">风险评分: {{ (item.score * 100).toFixed(0) }}%</span>
                <span class="utilization">使用率: {{ (item.utilization * 100).toFixed(0) }}%</span>
              </div>
              <div v-if="bottlenecks.length === 0" class="no-data">
                ✅ 暂无明显瓶颈
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import request from '@/api/request'

// 图表引用
const orderChartRef = ref(null)
const vehicleChartRef = ref(null)
const trendChartRef = ref(null)

// 图表实例
let orderChart = null
let vehicleChart = null
let trendChart = null

// 状态
const currentTime = ref('')
const kafkaStatus = ref(false)
const stats = reactive({
  totalOrders: 0,
  todayOrders: 0,
  totalVehicles: 0,
  totalCost: 0
})
const recentLogs = ref([])

// Spark 分析数据
const demandPredictions = ref([])
const vehicleSuggestions = ref([])
const bottlenecks = ref([])

// 格式化数字
const formatNumber = (num) => {
  if (num >= 10000) return (num / 10000).toFixed(1) + '万'
  return num.toLocaleString()
}

// 更新时间
const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN')
}

// 获取大数据
const fetchData = async () => {
  try {
    const res = await request.get('/bigdata/dashboard')
    if (res.success) {
      const data = res.data
      
      // 更新统计（字段映射）
      stats.totalOrders = data.summary.total_orders || 0
      stats.todayOrders = data.summary.today_orders || 0
      stats.totalVehicles = data.summary.total_vehicles || 0
      stats.totalCost = data.summary.total_cost || 0
      
      // 更新图表
      updateCharts(data)
      
      // 添加日志
      addLog('info', `数据更新: 订单${data.summary.total_orders}个, 车辆${data.summary.total_vehicles}辆`)
      
      // Kafka 状态
      kafkaStatus.value = data.kafka?.connected || false
    }
  } catch (e) {
    addLog('error', '获取数据失败: ' + e.message)
  }
}

// 获取 Spark 分析数据
const fetchSparkData = async () => {
  try {
    // 获取车辆调配建议
    const suggestionsRes = await request.get('/spark/vehicle-suggestions')
    if (suggestionsRes.success) {
      vehicleSuggestions.value = suggestionsRes.data.slice(0, 5)
    }
    
    // 获取供应链分析
    const supplyRes = await request.get('/spark/supply-chain')
    if (supplyRes.success) {
      bottlenecks.value = supplyRes.data.bottlenecks || []
    }
    
    // 获取需求预测
    const forecastRes = await request.get('/spark/demand-forecast')
    if (forecastRes.success && forecastRes.data) {
      // 按区域汇总
      const regionData = {}
      Object.values(forecastRes.data).forEach(dayData => {
        dayData.forEach(item => {
          if (!regionData[item.region]) {
            regionData[item.region] = []
          }
          regionData[item.region].push(item.demand)
        })
      })
      
      // 计算平均值
      demandPredictions.value = Object.entries(regionData).map(([region, demands]) => {
        const avg = Math.round(demands.reduce((a, b) => a + b, 0) / demands.length)
        return {
          region,
          avg_demand: avg,
          status: avg > 150 ? 'high' : avg > 100 ? 'medium' : 'normal'
        }
      }).sort((a, b) => b.avg_demand - a.avg_demand).slice(0, 5)
    }
  } catch (e) {
    console.error('Spark data fetch error:', e)
  }
}

// 初始化图表
const initCharts = () => {
  // 订单状态图
  if (orderChartRef.value) {
    orderChart = echarts.init(orderChartRef.value)
    orderChart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        label: { color: '#fff' },
        data: [
          { value: 0, name: '待处理', itemStyle: { color: '#ffc107' } },
          { value: 0, name: '运输中', itemStyle: { color: '#00d4ff' } },
          { value: 0, name: '已完成', itemStyle: { color: '#00ff88' } }
        ]
      }]
    })
  }

  // 车辆状态图
  if (vehicleChartRef.value) {
    vehicleChart = echarts.init(vehicleChartRef.value)
    vehicleChart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        label: { color: '#fff' },
        data: [
          { value: 0, name: '运输中', itemStyle: { color: '#00ff88' } },
          { value: 0, name: '空闲', itemStyle: { color: '#00d4ff' } },
          { value: 0, name: '维护', itemStyle: { color: '#ff6b6b' } }
        ]
      }]
    })
  }

  // 趋势图
  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      xAxis: {
        type: 'category',
        data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
        axisLabel: { color: '#aaa' }
      },
      yAxis: { 
        type: 'value',
        axisLabel: { color: '#aaa' }
      },
      series: [{
        type: 'line',
        smooth: true,
        data: [0, 0, 0, 0, 0, 0, 0],
        lineStyle: { color: '#00d4ff' },
        areaStyle: { color: 'rgba(0, 212, 255, 0.2)' }
      }]
    })
  }
}

// 更新图表
const updateCharts = (data) => {
  if (orderChart && data.orders?.status_distribution) {
    const dist = data.orders.status_distribution
    orderChart.setOption({
      series: [{
        data: [
          { value: dist.pending || 0, name: '待处理' },
          { value: dist.in_transit || 0, name: '运输中' },
          { value: dist.delivered || dist.completed || 0, name: '已完成' }
        ]
      }]
    })
  }

  if (vehicleChart && data.vehicles?.status_distribution) {
    const dist = data.vehicles.status_distribution
    vehicleChart.setOption({
      series: [{
        data: [
          { value: dist.in_use || dist.in_transit || 0, name: '运输中' },
          { value: dist.available || 0, name: '空闲' },
          { value: dist.maintenance || 0, name: '维护' }
        ]
      }]
    })
  }

  if (trendChart && data.orders?.weekly_trend) {
    trendChart.setOption({
      series: [{
        data: data.orders.weekly_trend.map(d => d.count)
      }]
    })
  }
}

// 添加日志
const addLog = (type, message) => {
  recentLogs.value.unshift({
    type,
    message,
    time: new Date().toLocaleTimeString('zh-CN')
  })
  if (recentLogs.value.length > 10) recentLogs.value.pop()
}

// 处理实时统计更新
const handleStatisticsUpdate = (data) => {
  if (data && data.data) {
    const summary = data.data.summary || data.data.orders || {}
    stats.totalOrders = summary.total || summary.total_orders || stats.totalOrders
    stats.todayOrders = summary.today || summary.today_orders || stats.todayOrders
    stats.totalVehicles = data.data.vehicles?.total || stats.totalVehicles
    stats.totalCost = summary.total_cost || stats.totalCost
    
    addLog('success', '实时数据更新')
  }
}

// 处理订单更新
const handleOrderUpdate = (data) => {
  addLog('info', `订单${data.event}: ${data.data?.order_id || ''}`)
}

// 处理预警更新
const handleAlertUpdate = (data) => {
  addLog('warning', data.data?.title || '新预警')
}

// 定时器
let timer = null

onMounted(async () => {
  updateTime()
  setInterval(updateTime, 1000)
  
  await nextTick()
  initCharts()
  
  // 获取数据
  await fetchData()
  
  // 获取 Spark 分析数据
  await fetchSparkData()
  
  // 监听 WebSocket 实时推送
  const socket = window.socketInstance
  if (socket) {
    socket.on('statistics_update', handleStatisticsUpdate)
    socket.on('order_update', handleOrderUpdate)
    socket.on('alert_update', handleAlertUpdate)
  }
  
  // 定时刷新（作为备选）
  timer = setInterval(fetchData, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  
  // 移除 WebSocket 监听
  const socket = window.socketInstance
  if (socket) {
    socket.off('statistics_update', handleStatisticsUpdate)
    socket.off('order_update', handleOrderUpdate)
    socket.off('alert_update', handleAlertUpdate)
  }
  
  orderChart?.dispose()
  vehicleChart?.dispose()
  trendChart?.dispose()
})
</script>

<style scoped>
.big-data-screen {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 100%);
  color: #fff;
  padding: 20px;
}

.screen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: rgba(0, 212, 255, 0.1);
  border-radius: 10px;
  margin-bottom: 20px;
}

.screen-header h1 {
  font-size: 24px;
  background: linear-gradient(90deg, #00d4ff, #00ff88);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-info {
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: rgba(255,255,255,0.7);
}

.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.metric-card {
  background: rgba(10, 14, 39, 0.8);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 10px;
  padding: 20px;
  text-align: center;
}

.metric-value {
  font-size: 32px;
  font-weight: 700;
  color: #00d4ff;
}

.metric-label {
  font-size: 14px;
  color: rgba(255,255,255,0.6);
  margin-top: 8px;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.chart-card {
  background: rgba(10, 14, 39, 0.8);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 10px;
  padding: 15px;
}

.chart-card h3 {
  font-size: 14px;
  color: #00d4ff;
  margin-bottom: 10px;
}

.chart-box {
  height: 200px;
}

.log-section {
  background: rgba(10, 14, 39, 0.8);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 10px;
  padding: 15px;
}

.log-section h3 {
  font-size: 14px;
  color: #00d4ff;
  margin-bottom: 10px;
}

.log-box {
  max-height: 150px;
  overflow-y: auto;
}

.log-item {
  display: flex;
  gap: 15px;
  padding: 8px 10px;
  font-size: 12px;
  border-left: 3px solid #00d4ff;
  margin-bottom: 5px;
  background: rgba(0,0,0,0.2);
}

.log-item.error { border-color: #ff6b6b; }
.log-item.info { border-color: #00d4ff; }
.log-item.success { border-color: #00ff88; }

.log-time { color: rgba(255,255,255,0.5); }
.log-msg { color: rgba(255,255,255,0.8); }

/* Spark 分析区域 */
.spark-section {
  margin-top: 20px;
  background: rgba(10, 14, 39, 0.8);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 10px;
  padding: 15px;
}

.spark-section h3 {
  font-size: 14px;
  color: #00d4ff;
  margin-bottom: 15px;
}

.spark-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
}

.spark-card {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  padding: 12px;
}

.spark-card h4 {
  font-size: 13px;
  color: #00ff88;
  margin-bottom: 10px;
}

.prediction-item,
.suggestion-item,
.bottleneck-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
 margin-bottom: 5px;
 background: rgba(0, 212, 255, 0.05);
  border-radius: 4px;
 font-size: 12px;
}

.region-name {
  color: #fff;
  font-weight: 500;
}

.demand-value {
  color: #00d4ff;
}

.demand-status.high { color: #ff6b6b; }
.demand-status.medium { color: #ffc107; }
.demand-status.normal { color: #00ff88; }

.vehicles {
  color: #00d4ff;
}

.note {
  color: rgba(255,255,255,0.6);
  font-size: 11px;
}

.score {
  color: #ffc107;
}

.utilization {
  color: rgba(255,255,255,0.6);
}

.no-data {
  text-align: center;
  color: rgba(255,255,255,0.5);
  padding: 20px;
}
</style>
