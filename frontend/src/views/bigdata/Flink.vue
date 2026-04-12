<template>
  <div class="flink-page">
    <!-- 页面标题 -->
    <el-page-header @back="goBack" content="Flink实时流处理" class="page-header">
      <template #extra>
        <el-tag :type="clusterStatus.running ? 'success' : 'danger'">
          {{ clusterStatus.running ? '运行中' : '已停止' }}
        </el-tag>
      </template>
    </el-page-header>

    <!-- 集群状态卡片 -->
    <el-row :gutter="20" class="status-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="status-card">
          <div class="status-item">
            <el-icon class="status-icon" :size="32" color="#409EFE">
              <Monitor />
            </el-icon>
            <div class="status-info">
              <div class="status-value">{{ clusterStatus.taskmanagers }}</div>
              <div class="status-label">TaskManagers</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="status-card">
          <div class="status-item">
            <el-icon class="status-icon" :size="32" color="#67C23A">
              <Cpu />
            </el-icon>
            <div class="status-info">
              <div class="status-value">{{ clusterStatus.slots_available }}/{{ clusterStatus.slots_total }}</div>
              <div class="status-label">可用Slots</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="status-card">
          <div class="status-item">
            <el-icon class="status-icon" :size="32" color="#E6A23C">
              <VideoPlay />
            </el-icon>
            <div class="status-info">
              <div class="status-value">{{ clusterStatus.jobs_running }}</div>
              <div class="status-label">运行中作业</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="status-card">
          <div class="status-item">
            <el-icon class="status-icon" :size="32" color="#909399">
              <CircleCheck />
            </el-icon>
            <div class="status-info">
              <div class="status-value">{{ clusterStatus.jobs_finished }}</div>
              <div class="status-label">已完成作业</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 实时统计 -->
    <el-row :gutter="20" class="realtime-section">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>实时处理统计</span>
              <el-button type="primary" link @click="refreshRealtimeStats">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="6" v-for="stat in realtimeStats" :key="stat.label">
              <div class="stat-item">
                <div class="stat-value">{{ stat.value }}</div>
                <div class="stat-label">{{ stat.label }}</div>
                <el-progress :percentage="stat.percentage" :color="stat.color" :show-text="false" />
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span>处理吞吐量</span>
          </template>
          <div class="throughput-chart" ref="throughputChart"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 作业列表 -->
    <el-card shadow="hover" class="jobs-section">
      <template #header>
        <div class="card-header">
          <span>Flink作业</span>
          <el-button type="primary" @click="openFlinkUI">
            <el-icon><Link /></el-icon>
            打开Flink UI
          </el-button>
        </div>
      </template>
      <el-table :data="jobs" stripe style="width: 100%">
        <el-table-column prop="job_id" label="作业ID" width="150" />
        <el-table-column prop="name" label="作业名称" min-width="250" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="启动时间" width="180" />
        <el-table-column prop="duration" label="运行时长" width="120">
          <template #default="{ row }">
            {{ formatDuration(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" type="primary" link>详情</el-button>
            <el-button size="small" type="danger" link>停止</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 实时告警 -->
    <el-card shadow="hover" class="alerts-section">
      <template #header>
        <div class="card-header">
          <span>实时告警</span>
          <el-select v-model="alertSeverity" size="small" style="width: 120px">
            <el-option label="全部" value="all" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </div>
      </template>
      <el-timeline>
        <el-timeline-item
          v-for="alert in alerts"
          :key="alert.alert_id"
          :type="getAlertType(alert.severity)"
          :timestamp="alert.timestamp"
        >
          <div class="alert-item">
            <el-tag :type="getAlertType(alert.severity)" size="small">
              {{ alert.type }}
            </el-tag>
            <span class="alert-message">{{ alert.message }}</span>
            <span class="alert-target" v-if="alert.vehicle_id">
              车辆 #{{ alert.vehicle_id }}
            </span>
            <span class="alert-target" v-if="alert.order_id">
              订单 {{ alert.order_id }}
            </span>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Monitor, Cpu, VideoPlay, CircleCheck, Refresh, Link, Promotion } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const router = useRouter()

// 集群状态
const clusterStatus = ref({
  running: false,
  taskmanagers: 0,
  slots_total: 0,
  slots_available: 0,
  jobs_running: 0,
  jobs_finished: 0
})

// 作业列表
const jobs = ref([])

// 实时统计
const realtimeData = ref({
  orders_last_5min: 0,
  high_value_orders: 0,
  active_vehicles: 0,
  alerts_today: 0,
  throughput: 0
})

const realtimeStats = computed(() => [
  { label: '近5分钟订单', value: realtimeData.value.orders_last_5min, percentage: 60, color: '#409EFE' },
  { label: '高价值订单', value: realtimeData.value.high_value_orders, percentage: 30, color: '#E6A23C' },
  { label: '活跃车辆', value: realtimeData.value.active_vehicles, percentage: 80, color: '#67C23A' },
  { label: '今日告警', value: realtimeData.value.alerts_today, percentage: 45, color: '#F56C6C' }
])

// 告警
const alerts = ref([])
const alertSeverity = ref('all')

// 吞吐量图表
const throughputChart = ref(null)
let chartInstance = null
let refreshTimer = null

// 加载集群状态
const loadClusterStatus = async () => {
  try {
    const res = await fetch('/api/flink/status')
    const data = await res.json()
    if (data.success) {
      clusterStatus.value = data.data
    }
  } catch (error) {
    console.error('加载集群状态失败:', error)
  }
}

// 加载作业列表
const loadJobs = async () => {
  try {
    const res = await fetch('/api/flink/jobs')
    const data = await res.json()
    if (data.success) {
      jobs.value = data.data
    }
  } catch (error) {
    console.error('加载作业列表失败:', error)
  }
}

// 加载实时统计
const loadRealtimeStats = async () => {
  try {
    const res = await fetch('/api/flink/realtime-stats')
    const data = await res.json()
    if (data.success) {
      realtimeData.value = data.data
      updateThroughputChart(data.data.throughput)
    }
  } catch (error) {
    console.error('加载实时统计失败:', error)
  }
}

// 加载告警
const loadAlerts = async () => {
  try {
    const res = await fetch(`/api/flink/alerts?severity=${alertSeverity.value}&limit=10`)
    const data = await res.json()
    if (data.success) {
      alerts.value = data.data
    }
  } catch (error) {
    console.error('加载告警失败:', error)
  }
}

// 刷新实时统计
const refreshRealtimeStats = () => {
  loadRealtimeStats()
  ElMessage.success('已刷新')
}

// 初始化吞吐量图表
const initThroughputChart = () => {
  if (!throughputChart.value) return
  
  chartInstance = echarts.init(throughputChart.value)
  
  const option = {
    grid: { top: 10, right: 10, bottom: 20, left: 40 },
    xAxis: {
      type: 'category',
      data: Array.from({ length: 10 }, (_, i) => `${i + 1}分`),
      axisLine: { lineStyle: { color: '#ccc' } },
      axisLabel: { color: '#666' }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#eee' } },
      axisLabel: { color: '#666' }
    },
    series: [{
      type: 'line',
      data: Array.from({ length: 10 }, () => Math.random() * 400 + 100),
      smooth: true,
      lineStyle: { color: '#409EFE', width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 254, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 254, 0.05)' }
        ])
      }
    }]
  }
  
  chartInstance.setOption(option)
}

// 更新吞吐量图表
const updateThroughputChart = (value) => {
  if (!chartInstance) return
  
  const option = chartInstance.getOption()
  const data = option.series[0].data.slice(1)
  data.push(value)
  option.series[0].data = data
  chartInstance.setOption(option)
}

// 打开 Flink UI
const openFlinkUI = () => {
  window.open('http://localhost:8083', '_blank')
}

// 返回上一页
const goBack = () => {
  router.push('/bigdata')
}

// 格式化时长
const formatDuration = (seconds) => {
  if (!seconds) return '-'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  }
  return `${minutes}分钟`
}

// 获取状态类型
const getStatusType = (status) => {
  const types = {
    'RUNNING': 'success',
    'FINISHED': 'info',
    'FAILED': 'danger',
    'CANCELED': 'warning'
  }
  return types[status] || 'info'
}

// 获取告警类型
const getAlertType = (severity) => {
  const types = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'info'
  }
  return types[severity] || 'info'
}

// 定时刷新
const startAutoRefresh = () => {
  refreshTimer = setInterval(() => {
    loadRealtimeStats()
    loadAlerts()
  }, 30000) // 30秒刷新一次
}

const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onMounted(() => {
  loadClusterStatus()
  loadJobs()
  loadRealtimeStats()
  loadAlerts()
  initThroughputChart()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
  if (chartInstance) {
    chartInstance.dispose()
  }
})
</script>

<style scoped>
.flink-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.status-cards {
  margin-bottom: 20px;
}

.status-card {
  height: 100px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 15px;
}

.status-icon {
  flex-shrink: 0;
}

.status-info {
  flex: 1;
}

.status-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.status-label {
  font-size: 14px;
  color: #909399;
}

.realtime-section {
  margin-bottom: 20px;
}

.stat-item {
  text-align: center;
  padding: 10px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 10px;
}

.throughput-chart {
  height: 200px;
}

.jobs-section,
.alerts-section {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.alert-message {
  flex: 1;
}

.alert-target {
  color: #909399;
  font-size: 12px;
}
</style>
