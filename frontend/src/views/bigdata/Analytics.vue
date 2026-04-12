<template>
  <div class="analytics-page">
    <!-- 顶部统计卡片 -->
    <div class="stats-row">
      <div class="stat-card" v-for="stat in stats" :key="stat.label">
        <div class="stat-icon">{{ stat.icon }}</div>
        <div class="stat-content">
          <span class="stat-value">{{ stat.value }}</span>
          <span class="stat-label">{{ stat.label }}</span>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-row">
      <!-- 订单趋势折线图 -->
      <div class="chart-card">
        <h3>📈 24小时订单趋势</h3>
        <div class="chart-container" ref="lineChart"></div>
      </div>
      
      <!-- 货物类型分布饼图 -->
      <div class="chart-card">
        <h3>📦 货物类型分布</h3>
        <div class="chart-container" ref="pieChart"></div>
      </div>
    </div>

    <!-- 性能指标 -->
    <div class="performance-card">
      <h3>⚡ ClickHouse 性能指标</h3>
      <div class="metrics-grid">
        <div class="metric-item">
          <span class="metric-label">查询耗时</span>
          <span class="metric-value">{{ performance.query_time_ms.toFixed(1) }} ms</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">扫描行数</span>
          <span class="metric-value">{{ formatNumber(performance.rows_analyzed) }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">内存使用</span>
          <span class="metric-value">{{ performance.memory_used_mb }} MB</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">优化评分</span>
          <span class="metric-value highlight">{{ performance.optimization_score }}/100</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const stats = ref([
  { icon: '📊', label: '总订单', value: '--' },
  { icon: '🚚', label: '运输中', value: '--' },
  { icon: '✅', label: '已送达', value: '--' },
  { icon: '🚛', label: '车辆数', value: '--' }
])

const performance = ref({
  query_time_ms: 0,
  rows_analyzed: 0,
  cache_hit: false,
  optimization_score: 0,
  memory_used_mb: 0
})

const cargoData = ref([])
const lineChart = ref(null)
const pieChart = ref(null)
let lineChartInstance = null
let pieChartInstance = null

const formatNumber = (num) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num
}

// 初始化折线图
const initLineChart = async () => {
  if (!lineChart.value) return
  
  try {
    // 获取真实数据
    const res = await fetch('/api/ch/realtime')
    const data = await res.json()
    
    let hours = []
    let orderData = []
    
    if (data.success && data.data.timeline) {
      hours = data.data.timeline.hours
      orderData = data.data.timeline.orders
    }
    
    lineChartInstance = echarts.init(lineChart.value, 'dark')
    
    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: '#00d4ff',
        textStyle: { color: '#fff' }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: hours,
        axisLine: { lineStyle: { color: '#333' } },
        axisLabel: { color: '#666', fontSize: 10 }
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: '#333' } },
        axisLabel: { color: '#666' },
        splitLine: { lineStyle: { color: '#222' } }
      },
      series: [{
        name: '订单数',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          color: '#00d4ff',
          width: 2
        },
        itemStyle: {
          color: '#00d4ff'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 212, 255, 0.3)' },
            { offset: 1, color: 'rgba(0, 212, 255, 0.05)' }
          ])
        },
        data: orderData
      }]
    }
    
    lineChartInstance.setOption(option)
  } catch (e) {
    console.error('初始化折线图失败:', e)
  }
}

// 初始化饼图
const initPieChart = () => {
  if (!pieChart.value || cargoData.value.length === 0) return
  
  pieChartInstance = echarts.init(pieChart.value, 'dark')
  
  const pieData = cargoData.value.map(item => ({
    name: item.type,
    value: item.count
  }))
  
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      borderColor: '#00d4ff',
      textStyle: { color: '#fff' },
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      textStyle: { color: '#888', fontSize: 11 },
      itemWidth: 10,
      itemHeight: 10
    },
    series: [{
      name: '货物类型',
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 6,
        borderColor: '#1a1a2e',
        borderWidth: 2
      },
      label: {
        show: false
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 14,
          fontWeight: 'bold',
          color: '#fff'
        },
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 212, 255, 0.5)'
        }
      },
      labelLine: {
        show: false
      },
      data: pieData,
      color: ['#00d4ff', '#00ff88', '#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff', '#ff8c42', '#a66cff', '#ff6b9d', '#50e3c2']
    }]
  }
  
  pieChartInstance.setOption(option)
}

const fetchData = async () => {
  try {
    // 获取仪表盘数据
    const res1 = await fetch('/api/ch/dashboard')
    const data1 = await res1.json()
    if (data1.success) {
      const d = data1.data
      stats.value = [
        { icon: '📊', label: '总订单', value: d.orders.total },
        { icon: '🚚', label: '运输中', value: d.orders.in_transit },
        { icon: '✅', label: '已送达', value: d.orders.delivered },
        { icon: '🚛', label: '车辆数', value: d.vehicles.total }
      ]
      
      cargoData.value = d.cargo_distribution
    }
    
    // 获取性能数据
    const res2 = await fetch('/api/ch/analysis/performance')
    const data2 = await res2.json()
    if (data2.success) {
      performance.value = data2.data
    }
  } catch (e) {
    console.error('获取数据失败:', e)
  }
}

// 窗口大小变化时重绘图表
const handleResize = () => {
  lineChartInstance?.resize()
  pieChartInstance?.resize()
}

onMounted(async () => {
  await fetchData()
  
  // 延迟初始化图表，确保 DOM 已渲染
  setTimeout(() => {
    initLineChart()
    initPieChart()
  }, 100)
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  lineChartInstance?.dispose()
  pieChartInstance?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.analytics-page {
  padding: 0;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid rgba(0, 212, 255, 0.1);
}

.stat-icon {
  font-size: 32px;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #00d4ff;
}

.stat-label {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}

.charts-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.chart-card {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(0, 212, 255, 0.1);
}

.chart-card h3 {
  margin: 0 0 16px;
  font-size: 14px;
  color: #00d4ff;
}

.chart-container {
  height: 250px;
  width: 100%;
}

.performance-card {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(0, 212, 255, 0.1);
}

.performance-card h3 {
  margin: 0 0 16px;
  font-size: 14px;
  color: #00d4ff;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.metric-item {
  text-align: center;
  padding: 16px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
}

.metric-label {
  display: block;
  font-size: 12px;
  color: #888;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #fff;
}

.metric-value.highlight {
  color: #00ff88;
}
</style>
