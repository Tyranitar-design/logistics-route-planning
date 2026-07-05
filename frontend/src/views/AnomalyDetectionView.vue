<template>
  <div class="anomaly-detection-page">
    <!-- 背景动效 -->
    <div class="bg-effects">
      <div class="grid-lines"></div>
      <div class="scan-line"></div>
    </div>

    <!-- 顶部标题 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="glow-title">🚨 实时异常检测中心</h1>
        <span class="subtitle">REALTIME ANOMALY DETECTION CENTER</span>
      </div>
      <div class="header-right">
        <div class="health-score" :class="healthLevel">
          <span class="score-value">{{ healthScore }}</span>
          <span class="score-label">健康度</span>
        </div>
        <el-button type="primary" @click="runDetection" :loading="detecting">
          <el-icon><Refresh /></el-icon> 立即检测
        </el-button>
        <el-button type="warning" @click="runDeepDetection" :loading="deepDetecting">
          <el-icon><Refresh /></el-icon> 深度检测
        </el-button>
      </div>
    </div>

    <!-- 检测状态 -->
    <div class="detection-status" :class="statusClass">
      <div class="status-icon">{{ statusIcon }}</div>
      <div class="status-text">{{ statusText }}</div>
      <div class="last-check">上次检测: {{ lastCheckTime }}</div>
    </div>

    <!-- 核心指标 -->
    <div class="metrics-row">
      <div class="metric-card" v-for="(count, type) in summary.by_type" :key="type" :class="getMetricClass(type)">
        <div class="metric-icon">{{ getTypeIcon(type) }}</div>
        <div class="metric-content">
          <div class="metric-value">{{ count }}</div>
          <div class="metric-label">{{ getTypeLabel(type) }}</div>
        </div>
        <div class="metric-trend" v-if="count > 0">⚠️</div>
      </div>
    </div>

    <!-- 按级别统计 -->
    <div class="level-stats">
      <div class="level-item critical" v-if="summary.by_level.critical > 0">
        <span class="level-count">{{ summary.by_level.critical }}</span>
        <span class="level-label">严重</span>
      </div>
      <div class="level-item high" v-if="summary.by_level.high > 0">
        <span class="level-count">{{ summary.by_level.high }}</span>
        <span class="level-label">高</span>
      </div>
      <div class="level-item medium" v-if="summary.by_level.medium > 0">
        <span class="level-count">{{ summary.by_level.medium }}</span>
        <span class="level-label">中</span>
      </div>
      <div class="level-item low" v-if="summary.by_level.low > 0">
        <span class="level-count">{{ summary.by_level.low }}</span>
        <span class="level-label">低</span>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 异常列表 -->
      <div class="anomaly-list-panel">
        <div class="panel-header">
          <span class="panel-title">📋 异常事件列表</span>
          <el-tag :type="anomalies.length > 0 ? 'danger' : 'success'" size="small">
            {{ anomalies.length }} 条异常
          </el-tag>
        </div>

        <div class="anomaly-list" v-if="anomalies.length > 0">
          <div
            v-for="(anomaly, index) in anomalies"
            :key="anomaly.id || index"
            class="anomaly-item"
            :class="anomaly.level"
          >
            <div class="anomaly-header">
              <span class="anomaly-icon">{{ getLevelIcon(anomaly.level) }}</span>
              <span class="anomaly-title">{{ anomaly.title }}</span>
              <el-tag size="small" :type="getTagType(anomaly.level)">
                {{ getLevelText(anomaly.level) }}
              </el-tag>
            </div>
            <div class="anomaly-message">{{ anomaly.message }}</div>
            <div class="anomaly-meta">
              <span class="meta-item">
                <el-icon><Location /></el-icon>
                {{ anomaly.source }}
              </span>
              <span class="meta-item">
                <el-icon><TrendCharts /></el-icon>
                偏差 {{ anomaly.deviation }}%
              </span>
              <span class="meta-item">
                <el-icon><Clock /></el-icon>
                {{ formatTime(anomaly.detected_at) }}
              </span>
            </div>
            <div class="anomaly-actions">
              <el-button 
                v-for="(action, i) in anomaly.actions?.slice(0, 3)" 
                :key="i"
                size="small" 
                type="primary"
                plain
                @click="handleAction(action, anomaly)"
              >
                {{ action }}
              </el-button>
            </div>
          </div>
        </div>

        <div class="no-anomaly" v-else>
          <div class="no-anomaly-icon">✅</div>
          <div class="no-anomaly-text">暂无异常，系统运行正常</div>
        </div>
      </div>

      <!-- 检测类型面板 -->
      <div class="detection-panels">
        <!-- 订单超时 -->
        <div class="detection-panel">
          <div class="panel-title">
            <span class="icon">📦</span> 订单超时检测
          </div>
          <div class="panel-content">
            <div class="detection-stat">
              <span class="stat-value">{{ orderTimeouts }}</span>
              <span class="stat-label">超时订单</span>
            </div>
            <div class="threshold-info">
              <span>普通: 48h</span>
              <span>紧急: 12h</span>
              <span>预约: 72h</span>
            </div>
          </div>
        </div>

        <!-- 成本飙升 -->
        <div class="detection-panel">
          <div class="panel-title">
            <span class="icon">💰</span> 成本飙升检测
          </div>
          <div class="panel-content">
            <div class="detection-stat">
              <span class="stat-value">{{ costSpikes }}</span>
              <span class="stat-label">成本异常</span>
            </div>
            <div class="threshold-info">
              <span>阈值: Z > 2.5</span>
              <span>监控窗口: 50条</span>
            </div>
          </div>
        </div>

        <!-- 路线偏离 -->
        <div class="detection-panel">
          <div class="panel-title">
            <span class="icon">🗺️</span> 路线偏离检测
          </div>
          <div class="panel-content">
            <div class="detection-stat">
              <span class="stat-value">{{ routeDeviations }}</span>
              <span class="stat-label">偏离车辆</span>
            </div>
            <div class="threshold-info">
              <span>偏离阈值: 30%</span>
              <span>实时监控中</span>
            </div>
          </div>
        </div>

        <!-- 天气影响 -->
        <div class="detection-panel">
          <div class="panel-title">
            <span class="icon">🌧️</span> 天气影响检测
          </div>
          <div class="panel-content">
            <div class="detection-stat">
              <span class="stat-value">{{ weatherAlerts }}</span>
              <span class="stat-label">受影响区域</span>
            </div>
            <div class="threshold-info">
              <span>风险等级 ≥ 2</span>
              <span>延迟 > 50%</span>
            </div>
          </div>
        </div>

        <!-- 车辆故障预测 -->
        <div class="detection-panel">
          <div class="panel-title">
            <span class="icon">🚗</span> 车辆故障预测
          </div>
          <div class="panel-content">
            <div class="detection-stat">
              <span class="stat-value">{{ vehicleFaults }}</span>
              <span class="stat-label">高风险车辆</span>
            </div>
            <div class="threshold-info">
              <span>风险分 ≥ 40</span>
              <span>里程/维保/车龄</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 建议区 -->
    <div class="recommendations-panel" v-if="recommendations.length > 0">
      <div class="panel-title">💡 系统建议</div>
      <div class="recommendation-list">
        <div v-for="(rec, i) in recommendations" :key="i" class="recommendation-item">
          {{ rec }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Refresh, Location, TrendCharts, Clock } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'
import { detectShipmentAnomalies, getAiAnomalyScorecard } from '@/api/aiAnomaly'

// 状态
const detecting = ref(false)
const deepDetecting = ref(false)
const healthScore = ref(100)
const lastCheckTime = ref('-')
const anomalies = ref([])
const recommendations = ref([])
const summary = ref({
  total_anomalies: 0,
  by_type: {},
  by_level: { critical: 0, high: 0, medium: 0, low: 0 }
})

// 按类型统计
const orderTimeouts = computed(() => summary.value.by_type?.order_timeout || 0)
const costSpikes = computed(() => summary.value.by_type?.cost_spike || 0)
const routeDeviations = computed(() => summary.value.by_type?.route_deviation || 0)
const weatherAlerts = computed(() => summary.value.by_type?.weather_impact || 0)
const vehicleFaults = computed(() => summary.value.by_type?.vehicle_fault || 0)

// 健康等级
const healthLevel = computed(() => {
  if (healthScore.value >= 90) return 'excellent'
  if (healthScore.value >= 70) return 'good'
  if (healthScore.value >= 50) return 'warning'
  return 'critical'
})

// 状态显示
const statusClass = computed(() => {
  const total = summary.value.total_anomalies
  if (total === 0) return 'normal'
  if (total <= 3) return 'warning'
  return 'critical'
})

const statusIcon = computed(() => {
  const total = summary.value.total_anomalies
  if (total === 0) return '✅'
  if (total <= 3) return '⚠️'
  return '🚨'
})

const statusText = computed(() => {
  const total = summary.value.total_anomalies
  if (total === 0) return '系统运行正常'
  if (total <= 3) return '存在少量异常'
  return '发现多个异常，请立即处理'
})

// 获取类型图标
const getTypeIcon = (type) => {
  const icons = {
    order_timeout: '📦',
    cost_spike: '💰',
    route_deviation: '🗺️',
    weather_impact: '🌧️',
    vehicle_fault: '🚗',
    status: '📦',
    geo: '🗺️',
    cost: '💰',
    eta: '⏱️',
    delay: '⏱️',
    od_volume: '📊',
    node_congestion: '🏬',
    ml: '🤖'
  }
  return icons[type] || '⚠️'
}

// 获取类型标签
const getTypeLabel = (type) => {
  const labels = {
    order_timeout: '订单超时',
    cost_spike: '成本飙升',
    route_deviation: '路线偏离',
    weather_impact: '天气影响',
    vehicle_fault: '车辆故障',
    status: '状态异常',
    geo: '坐标异常',
    cost: '成本异常',
    eta: '时效异常',
    delay: '延误异常',
    od_volume: 'OD 波动',
    node_congestion: '节点拥堵',
    ml: 'ML Shadow'
  }
  return labels[type] || type
}

// 获取级别图标
const getLevelIcon = (level) => {
  const icons = {
    critical: '🔴',
    high: '🟠',
    medium: '🟡',
    low: '🔵'
  }
  return icons[level] || '⚪'
}

// 获取级别文本
const getLevelText = (level) => {
  const texts = {
    critical: '严重',
    high: '高',
    medium: '中',
    low: '低'
  }
  return texts[level] || level
}

// 获取标签类型
const getTagType = (level) => {
  const types = {
    critical: 'danger',
    high: 'danger',
    medium: 'warning',
    low: 'info'
  }
  return types[level] || 'info'
}

// 获取指标卡片样式
const getMetricClass = (type) => {
  if (summary.value.by_type[type] > 0) return 'has-anomaly'
  return 'normal'
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return '-'
  const date = new Date(time)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 运行检测
const runDetection = async (options = {}) => {
  const isFull = options.runtime_profile === 'full'
  if (isFull) {
    deepDetecting.value = true
  } else {
    detecting.value = true
  }
  try {
    const [res, scorecard] = await Promise.all([
      detectShipmentAnomalies({
        runtime_profile: isFull ? 'full' : 'interactive',
        limit: isFull ? 50000 : 5000,
        anomaly_limit: isFull ? 160 : 40,
        use_ml: isFull
      }),
      getAiAnomalyScorecard({
        runtime_profile: isFull ? 'full' : 'interactive',
        limit: isFull ? 50000 : 5000,
        anomaly_limit: isFull ? 160 : 80,
        use_ml: isFull
      })
    ])
    if (res.success) {
      summary.value = normalizeSummary(res.summary)
      anomalies.value = (res.anomalies || []).map(normalizeAnomaly)
      healthScore.value = Math.round(scorecard.summary?.readiness_score ?? Math.max(0, 100 - (summary.value.total_anomalies || 0)))
      recommendations.value = scorecard.recommendations || []
      lastCheckTime.value = new Date().toLocaleTimeString('zh-CN')
      
      if (summary.value.total_anomalies > 0) {
        ElNotification({
          title: isFull ? '深度检测完成' : '异常检测完成',
          message: `发现 ${summary.value.total_anomalies} 个真实 shipment_facts 异常信号`,
          type: 'warning'
        })
      } else {
        ElMessage.success(isFull ? '深度检测完成，暂未发现高风险异常' : '检测完成，系统运行正常')
      }
    }
  } catch (e) {
    console.error('检测失败:', e)
    ElMessage.error(friendlyError(e, 'AI 异常检测接口失败，请检查 /api/ai-anomaly 后端链路'))
  } finally {
    detecting.value = false
    deepDetecting.value = false
  }
}

const runDeepDetection = () => runDetection({ runtime_profile: 'full' })

const friendlyError = (error, fallback) => {
  if (error?.code === 'ECONNABORTED' || String(error?.message || '').includes('timeout')) {
    return '异常检测超时：请先使用轻量检测，深度检测可稍后重试'
  }
  if (!error?.response) return '后端不可达：请确认 Flask 服务已启动'
  return error.response.data?.fallback_reason || error.response.data?.error || fallback
}

const normalizeSummary = (raw = {}) => {
  return {
    total_anomalies: raw.anomaly_count || raw.total_anomalies || 0,
    by_type: raw.by_type || {},
    by_level: {
      critical: raw.by_level?.critical || 0,
      high: raw.by_level?.high || 0,
      medium: raw.by_level?.medium || 0,
      low: raw.by_level?.low || 0
    }
  }
}

const normalizeAnomaly = (item = {}) => {
  const type = item.anomaly_type || item.type || 'unknown'
  return {
    id: item.anomaly_id || item.id || `${type}_${item.source_id || item.shipment_id || Math.random()}`,
    type,
    level: item.level || 'medium',
    title: item.title || getTypeLabel(type),
    message: item.explanation || item.message || item.reason || '真实异常信号已返回，但暂无详细解释。',
    source: item.source_id || item.shipment_id || item.order_id || item.data_source || 'shipment_fact',
    deviation: Number(item.deviation ?? item.z_score ?? item.score ?? item.risk_score ?? 0).toFixed(1),
    detected_at: item.detected_at || item.created_at || new Date().toISOString(),
    actions: item.actions || ['人工复核', '查看订单', '调度评估']
  }
}

// 处理操作
const handleAction = (action, anomaly) => {
  ElMessage.info(`执行操作: ${action}`)
}

// 初始化
onMounted(async () => {
  await runDetection()
})
</script>

<style scoped>
.anomaly-detection-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #0d1033 100%);
  padding: 16px;
  color: #fff;
  position: relative;
}

.bg-effects {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.grid-lines {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(255, 107, 107, 0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255, 107, 107, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
}

.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #ff6b6b, transparent);
  animation: scan 3s linear infinite;
}

@keyframes scan {
  0% { top: 0; opacity: 1; }
  100% { top: 100%; opacity: 0; }
}

/* Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px 20px;
  background: rgba(255, 107, 107, 0.05);
  border: 1px solid rgba(255, 107, 107, 0.15);
  border-radius: 12px;
}

.glow-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  background: linear-gradient(90deg, #ff6b6b, #ffd93d, #ff6b6b);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  display: block;
  font-size: 10px;
  color: rgba(255,255,255,0.4);
  letter-spacing: 2px;
  margin-top: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.health-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 16px;
  border-radius: 8px;
  min-width: 80px;
}

.health-score.excellent { background: rgba(0, 255, 136, 0.2); }
.health-score.good { background: rgba(0, 212, 255, 0.2); }
.health-score.warning { background: rgba(255, 217, 61, 0.2); }
.health-score.critical { background: rgba(255, 107, 107, 0.2); }

.score-value {
  font-size: 24px;
  font-weight: 700;
}

.health-score.excellent .score-value { color: #00ff88; }
.health-score.good .score-value { color: #00d4ff; }
.health-score.warning .score-value { color: #ffd93d; }
.health-score.critical .score-value { color: #ff6b6b; }

.score-label {
  font-size: 10px;
  color: rgba(255,255,255,0.6);
}

/* Detection Status */
.detection-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.detection-status.normal {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.2);
}

.detection-status.warning {
  background: rgba(255, 217, 61, 0.1);
  border: 1px solid rgba(255, 217, 61, 0.2);
}

.detection-status.critical {
  background: rgba(255, 107, 107, 0.1);
  border: 1px solid rgba(255, 107, 107, 0.2);
}

.status-icon {
  font-size: 24px;
}

.status-text {
  flex: 1;
  font-weight: 600;
}

.last-check {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
}

/* Metrics */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  display: flex;
  align-items: center;
  padding: 12px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 8px;
  gap: 10px;
}

.metric-card.has-anomaly {
  background: rgba(255, 107, 107, 0.1);
  border-color: rgba(255, 107, 107, 0.3);
}

.metric-icon {
  font-size: 24px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
}

.metric-label {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
}

.metric-trend {
  font-size: 14px;
}

/* Level Stats */
.level-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.level-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 12px;
}

.level-item.critical { background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }
.level-item.high { background: rgba(255, 165, 0, 0.2); color: #ffa500; }
.level-item.medium { background: rgba(255, 217, 61, 0.2); color: #ffd93d; }
.level-item.low { background: rgba(0, 212, 255, 0.2); color: #00d4ff; }

.level-count {
  font-weight: 700;
  font-size: 16px;
}

/* Main Content */
.main-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

/* Anomaly List Panel */
.anomaly-list-panel {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 12px;
  padding: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
}

.anomaly-list {
  max-height: 500px;
  overflow-y: auto;
}

.anomaly-item {
  padding: 12px;
  margin-bottom: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border-left: 3px solid;
}

.anomaly-item.critical { border-left-color: #ff6b6b; }
.anomaly-item.high { border-left-color: #ffa500; }
.anomaly-item.medium { border-left-color: #ffd93d; }
.anomaly-item.low { border-left-color: #00d4ff; }

.anomaly-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.anomaly-icon {
  font-size: 16px;
}

.anomaly-title {
  flex: 1;
  font-weight: 600;
  font-size: 13px;
}

.anomaly-message {
  font-size: 12px;
  color: rgba(255,255,255,0.8);
  margin-bottom: 8px;
}

.anomaly-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
  font-size: 11px;
  color: rgba(255,255,255,0.5);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.anomaly-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.no-anomaly {
  text-align: center;
  padding: 40px;
}

.no-anomaly-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.no-anomaly-text {
  color: rgba(255,255,255,0.6);
}

/* Detection Panels */
.detection-panels {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detection-panel {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 8px;
  padding: 12px;
}

.detection-panel .panel-title {
  font-size: 12px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.panel-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detection-stat {
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}

.stat-label {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
}

.threshold-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 10px;
  color: rgba(255,255,255,0.4);
  text-align: right;
}

/* Recommendations */
.recommendations-panel {
  background: rgba(255, 217, 61, 0.05);
  border: 1px solid rgba(255, 217, 61, 0.15);
  border-radius: 12px;
  padding: 16px;
}

.recommendation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.recommendation-item {
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  font-size: 13px;
}

/* Button Overrides */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #ff6b6b, #ffd93d);
  border: none;
  color: #000;
}

:deep(.el-tag--danger) {
  background: rgba(255, 107, 107, 0.2);
  border-color: rgba(255, 107, 107, 0.3);
  color: #ff6b6b;
}

:deep(.el-tag--warning) {
  background: rgba(255, 217, 61, 0.2);
  border-color: rgba(255, 217, 61, 0.3);
  color: #ffd93d;
}
</style>
