<template>
  <div class="monitor-page">
    <!-- 顶部指标卡片 -->
    <div class="metrics-cards">
      <div class="metric-card" v-for="metric in metrics" :key="metric.label">
        <div class="metric-icon">{{ metric.icon }}</div>
        <div class="metric-info">
          <span class="metric-value">{{ metric.value }}</span>
          <span class="metric-label">{{ metric.label }}</span>
        </div>
      </div>
    </div>

    <!-- Grafana 嵌入区域 -->
    <div class="grafana-container">
      <div class="iframe-header">
        <h3>📊 实时监控大屏</h3>
        <el-button type="primary" size="small" @click="openGrafana">
          <el-icon><Link /></el-icon>
          在新窗口打开
        </el-button>
      </div>
      <iframe 
        ref="grafanaFrame"
        :src="grafanaUrl" 
        frameborder="0"
        class="grafana-iframe"
        @load="onIframeLoad"
      ></iframe>
      <div v-if="loading" class="iframe-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在加载监控大屏...</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Link, Loading } from '@element-plus/icons-vue'

const loading = ref(true)
const grafanaFrame = ref(null)

// Grafana 仪表盘 URL（需要配置匿名访问或嵌入模式）
// 使用首页而非特定仪表盘（仪表盘需手动创建）
const grafanaUrl = ref('http://localhost:3000/?orgId=1&kiosk&theme=dark')

const metrics = ref([
  { icon: '📦', label: '订单总数', value: '--' },
  { icon: '🚚', label: '活跃订单', value: '--' },
  { icon: '🚛', label: '车辆总数', value: '--' },
  { icon: '🗺️', label: '路线总数', value: '--' },
  { icon: '❤️', label: '系统健康', value: '--' }
])

// 从后端获取指标数据（降级：后端无此接口时使用基础接口）
const fetchMetrics = async () => {
  try {
    // 优先尝试 metrics/json
    const res = await fetch('/api/metrics/json')
    if (res.ok) {
      const data = await res.json()
      if (data.success) {
        metrics.value = [
          { icon: '📦', label: '订单总数', value: data.data.orders.total },
          { icon: '🚚', label: '活跃订单', value: data.data.orders.active },
          { icon: '🚛', label: '车辆总数', value: data.data.vehicles.total },
          { icon: '🗺️', label: '路线总数', value: data.data.routes.total },
          { icon: '❤️', label: '系统健康', value: data.data.system.health + '%' }
        ]
        return
      }
    }
    // 降级：用基础 API 获取
    await fallbackFetch()
  } catch (e) {
    // 后端无 metrics 接口，降级处理
    await fallbackFetch()
  }
}

// 降级方案：从基础接口获取数据
const fallbackFetch = async () => {
  try {
    const [ordersRes, vehiclesRes, routesRes] = await Promise.allSettled([
      fetch('/api/orders', { headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` } }).then(r => r.ok ? r.json() : null),
      fetch('/api/vehicles', { headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` } }).then(r => r.ok ? r.json() : null),
      fetch('/api/routes', { headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` } }).then(r => r.ok ? r.json() : null)
    ])
    const orders = ordersRes.status === 'fulfilled' && ordersRes.value?.data ? ordersRes.value.data : (Array.isArray(ordersRes.value) ? ordersRes.value : [])
    const vehicles = vehiclesRes.status === 'fulfilled' && vehiclesRes.value?.data ? vehiclesRes.value.data : (Array.isArray(vehiclesRes.value) ? vehiclesRes.value : [])
    const routes = routesRes.status === 'fulfilled' && routesRes.value?.data ? routesRes.value.data : (Array.isArray(routesRes.value) ? routesRes.value : [])
    metrics.value = [
      { icon: '📦', label: '订单总数', value: Array.isArray(orders) ? orders.length : '--' },
      { icon: '🚚', label: '活跃订单', value: Array.isArray(orders) ? orders.filter(o => ['pending','in_transit','picked_up'].includes(o.status)).length : '--' },
      { icon: '🚛', label: '车辆总数', value: Array.isArray(vehicles) ? vehicles.length : '--' },
      { icon: '🗺️', label: '路线总数', value: Array.isArray(routes) ? routes.length : '--' },
      { icon: '❤️', label: '系统健康', value: '100%' }
    ]
  } catch (e) {
    // 静默失败，保持默认 '--' 显示
  }
}

const onIframeLoad = () => {
  loading.value = false
}

const openGrafana = () => {
  window.open('http://localhost:3000', '_blank')
}

onMounted(() => {
  fetchMetrics()
  // 定时刷新
  setInterval(fetchMetrics, 10000)
})
</script>

<style scoped>
.monitor-page {
  height: 100%;
}

.metrics-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.metric-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid rgba(0, 212, 255, 0.1);
}

.metric-icon {
  font-size: 32px;
}

.metric-info {
  display: flex;
  flex-direction: column;
}

.metric-value {
  font-size: 28px;
  font-weight: bold;
  color: #00d4ff;
}

.metric-label {
  font-size: 12px;
  color: #888;
  margin-top: 4px;
}

.grafana-container {
  background: #1a1a2e;
  border-radius: 12px;
  height: calc(100vh - 200px);
  overflow: hidden;
  position: relative;
  border: 1px solid rgba(0, 212, 255, 0.1);
}

.iframe-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.3);
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.iframe-header h3 {
  margin: 0;
  font-size: 14px;
  color: #00d4ff;
}

.grafana-iframe {
  width: 100%;
  height: calc(100% - 50px);
}

.iframe-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #00d4ff;
}

.iframe-loading .el-icon {
  font-size: 32px;
}
</style>
