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
const grafanaUrl = ref('http://localhost:3000/d/logistics-main?orgId=1&kiosk&theme=dark')

const metrics = ref([
  { icon: '📦', label: '订单总数', value: '--' },
  { icon: '🚚', label: '活跃订单', value: '--' },
  { icon: '🚛', label: '车辆总数', value: '--' },
  { icon: '🗺️', label: '路线总数', value: '--' },
  { icon: '❤️', label: '系统健康', value: '--' }
])

// 从后端获取指标数据
const fetchMetrics = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/metrics/json')
    const data = await res.json()
    if (data.success) {
      metrics.value = [
        { icon: '📦', label: '订单总数', value: data.data.orders.total },
        { icon: '🚚', label: '活跃订单', value: data.data.orders.active },
        { icon: '🚛', label: '车辆总数', value: data.data.vehicles.total },
        { icon: '🗺️', label: '路线总数', value: data.data.routes.total },
        { icon: '❤️', label: '系统健康', value: data.data.system.health + '%' }
      ]
    }
  } catch (e) {
    console.error('获取指标失败:', e)
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
