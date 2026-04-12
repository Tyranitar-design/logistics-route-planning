<template>
  <div class="spark-page">
    <div class="spark-header">
      <h2>🔥 Spark Streaming 实时处理</h2>
      <el-tag :type="status === 'running' ? 'success' : 'info'">
        {{ status === 'running' ? '运行中' : '就绪' }}
      </el-tag>
    </div>

    <!-- 性能指标 -->
    <div class="metrics-row">
      <div class="metric-card" v-for="m in metrics" :key="m.label">
        <span class="metric-value">{{ m.value }}</span>
        <span class="metric-label">{{ m.label }}</span>
      </div>
    </div>

    <!-- 实时图表 -->
    <div class="chart-card">
      <h3>📊 实时数据处理速率</h3>
      <div class="chart-container" ref="chart"></div>
    </div>

    <!-- 操作按钮 -->
    <div class="actions-card">
      <el-button type="primary" @click="startStreaming" :loading="loading">
        ▶ 启动流处理
      </el-button>
      <el-button @click="stopStreaming">⏹ 停止</el-button>
      <el-button @click="refreshData">🔄 刷新</el-button>
      <el-button @click="openSparkUI">🌐 Spark UI</el-button>
    </div>

    <!-- 信息卡片 -->
    <div class="info-row">
      <el-card>
        <template #header><span>📡 数据源</span></template>
        <ul>
          <li>Kafka Topic: logistics-orders</li>
          <li>Kafka Topic: logistics-vehicles</li>
          <li>处理模式: Structured Streaming</li>
        </ul>
      </el-card>
      <el-card>
        <template #header><span>⚡ 处理能力</span></template>
        <ul>
          <li>吞吐量: 10K-50K 条/秒</li>
          <li>延迟: &lt;100ms</li>
          <li>Executor: 2 个</li>
        </ul>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const status = ref('ready')
const loading = ref(false)
const chart = ref(null)
let chartInstance = null

const metrics = ref([
  { label: 'Executor 数', value: '-' },
  { label: 'CPU 核心', value: '-' },
  { label: '内存使用', value: '-' },
  { label: '吞吐量', value: '-' }
])

const fetchData = async () => {
  try {
    const res = await fetch('/api/spark/metrics')
    const data = await res.json()
    if (data.success) {
      const d = data.data
      metrics.value = [
        { label: 'Executor 数', value: d.executors },
        { label: 'CPU 核心', value: d.cores },
        { label: '内存使用', value: `${d.memory_used_gb}/${d.memory_total_gb} GB` },
        { label: '吞吐量', value: `${d.throughput_records_per_sec}/s` }
      ]
    }
  } catch (e) {
    console.error('获取数据失败:', e)
  }
}

const initChart = async () => {
  if (!chart.value) return
  
  try {
    const res = await fetch('/api/spark/analysis/realtime')
    const data = await res.json()
    
    if (data.success) {
      chartInstance = echarts.init(chart.value, 'dark')
      
      const option = {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
          type: 'category',
          data: data.data.timeline.minutes,
          axisLabel: { color: '#666' }
        },
        yAxis: {
          type: 'value',
          axisLabel: { color: '#666' },
          splitLine: { lineStyle: { color: '#222' } }
        },
        series: [{
          name: '处理速率',
          type: 'bar',
          data: data.data.timeline.order_rates,
          itemStyle: { color: '#ff6b35' }
        }]
      }
      
      chartInstance.setOption(option)
    }
  } catch (e) {
    console.error('初始化图表失败:', e)
  }
}

const startStreaming = async () => {
  loading.value = true
  try {
    await fetch('/api/spark/streaming/start', { method: 'POST' })
    status.value = 'running'
  } finally {
    loading.value = false
  }
}

const stopStreaming = async () => {
  await fetch('/api/spark/streaming/stop', { method: 'POST' })
  status.value = 'ready'
}

const refreshData = () => {
  fetchData()
  initChart()
}

const openSparkUI = () => {
  window.open('http://localhost:8080', '_blank')
}

onMounted(() => {
  fetchData()
  setTimeout(initChart, 100)
})

onUnmounted(() => {
  chartInstance?.dispose()
})
</script>

<style scoped>
.spark-page {
  max-width: 1000px;
  margin: 0 auto;
}

.spark-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.spark-header h2 {
  margin: 0;
  color: #ff6b35;
}

.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.metric-card {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  border: 1px solid rgba(255, 107, 53, 0.2);
}

.metric-value {
  font-size: 28px;
  font-weight: bold;
  color: #ff6b35;
  display: block;
}

.metric-label {
  font-size: 12px;
  color: #888;
}

.chart-card {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid rgba(255, 107, 53, 0.2);
}

.chart-card h3 {
  margin: 0 0 16px;
  color: #ff6b35;
  font-size: 14px;
}

.chart-container {
  height: 250px;
}

.actions-card {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  display: flex;
  gap: 12px;
  border: 1px solid rgba(255, 107, 53, 0.2);
}

.info-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.info-row .el-card {
  background: #1a1a2e;
  border: 1px solid rgba(255, 107, 53, 0.2);
}

.info-row ul {
  list-style: none;
  padding: 0;
  margin: 0;
  color: #a0a0a0;
}

.info-row li {
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.info-row li:last-child {
  border-bottom: none;
}
</style>
