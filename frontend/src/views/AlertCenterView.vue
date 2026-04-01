<template>
  <div class="alert-page">
    <!-- 背景动效 -->
    <div class="bg-effects">
      <div class="grid-lines"></div>
      <div class="scan-line"></div>
    </div>

    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="glow-title">🔔 智能预警中心</h1>
        <span class="subtitle">ALERT CENTER</span>
      </div>
      <div class="header-right">
        <div class="health-badge" :class="summary.status">
          <span class="health-score">{{ summary.health_score }}</span>
          <span class="health-label">健康度</span>
        </div>
        <el-button type="primary" @click="refreshData" :loading="loading" size="small">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card critical" @click="filterByLevel('critical')">
        <div class="stat-icon">🚨</div>
        <div class="stat-value">{{ statistics.critical || 0 }}</div>
        <div class="stat-label">严重</div>
      </div>
      <div class="stat-card high" @click="filterByLevel('high')">
        <div class="stat-icon">⚠️</div>
        <div class="stat-value">{{ statistics.high || 0 }}</div>
        <div class="stat-label">高级</div>
      </div>
      <div class="stat-card medium" @click="filterByLevel('medium')">
        <div class="stat-icon">📋</div>
        <div class="stat-value">{{ statistics.medium || 0 }}</div>
        <div class="stat-label">中级</div>
      </div>
      <div class="stat-card low" @click="filterByLevel('low')">
        <div class="stat-icon">💡</div>
        <div class="stat-value">{{ statistics.low || 0 }}</div>
        <div class="stat-label">低级</div>
      </div>
    </div>

    <!-- 系统建议 -->
    <div class="recommendation-card" v-if="summary.recommendation">
      <el-icon><InfoFilled /></el-icon>
      <span>{{ summary.recommendation }}</span>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 预警类型筛选 -->
      <div class="filter-bar">
        <el-radio-group v-model="filterType" size="small" @change="handleFilterChange">
          <el-radio-button label="">全部 ({{ statistics.total || 0 }})</el-radio-button>
          <el-radio-button label="order">订单 ({{ statistics.by_type?.order || 0 }})</el-radio-button>
          <el-radio-button label="vehicle">车辆 ({{ statistics.by_type?.vehicle || 0 }})</el-radio-button>
          <el-radio-button label="route">路线 ({{ statistics.by_type?.route || 0 }})</el-radio-button>
          <el-radio-button label="supply_chain">供应链 ({{ statistics.by_type?.supply_chain || 0 }})</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 预警列表 -->
      <div class="alert-list">
        <div 
          v-for="alert in filteredAlerts" 
          :key="alert.id" 
          class="alert-card"
          :class="[alert.level, { unread: !alert.is_read }]"
        >
          <div class="alert-header">
            <div class="alert-level">
              <span class="level-icon">{{ getLevelIcon(alert.level) }}</span>
              <span class="level-text">{{ getLevelText(alert.level) }}</span>
            </div>
            <div class="alert-type">
              <el-tag size="small" :type="getTypeTag(alert.type)">
                {{ getTypeText(alert.type) }}
              </el-tag>
            </div>
            <div class="alert-time">{{ formatTime(alert.created_at) }}</div>
          </div>
          
          <div class="alert-title">{{ alert.title }}</div>
          <div class="alert-message">{{ alert.message }}</div>
          
          <div class="alert-actions" v-if="alert.actions && alert.actions.length > 0">
            <el-button 
              v-for="(action, idx) in alert.actions.slice(0, 3)" 
              :key="idx"
              size="small"
              :type="idx === 0 ? 'primary' : 'default'"
              @click="handleAction(alert, action)"
            >
              {{ action }}
            </el-button>
          </div>
        </div>
        
        <el-empty v-if="filteredAlerts.length === 0" description="暂无预警信息" :image-size="80" />
      </div>
    </div>

    <!-- 预警详情弹窗 -->
    <el-dialog v-model="detailVisible" title="预警详情" width="400px">
      <div class="alert-detail" v-if="selectedAlert">
        <div class="detail-row">
          <span class="label">预警类型</span>
          <el-tag :type="getTypeTag(selectedAlert.type)">{{ getTypeText(selectedAlert.type) }}</el-tag>
        </div>
        <div class="detail-row">
          <span class="label">预警级别</span>
          <span :class="['level-badge', selectedAlert.level]">{{ getLevelText(selectedAlert.level) }}</span>
        </div>
        <div class="detail-row">
          <span class="label">预警标题</span>
          <span>{{ selectedAlert.title }}</span>
        </div>
        <div class="detail-row">
          <span class="label">详细信息</span>
          <span>{{ selectedAlert.message }}</span>
        </div>
        <div class="detail-row">
          <span class="label">发生时间</span>
          <span>{{ formatTime(selectedAlert.created_at) }}</span>
        </div>
        <div class="detail-actions">
          <el-button type="primary" @click="handleResolve(selectedAlert)">标记已解决</el-button>
          <el-button @click="detailVisible = false">关闭</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { Refresh, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getAlertDashboard, markAlertRead, markAlertResolved } from '@/api/alert'

// 状态
const loading = ref(false)
const alerts = ref([])
const statistics = ref({})
const summary = ref({
  health_score: 100,
  status: 'normal',
  recommendation: ''
})
const filterType = ref('')
const filterLevel = ref('')
const detailVisible = ref(false)
const selectedAlert = ref(null)

// 自动刷新定时器
let refreshTimer = null

// 过滤后的预警列表
const filteredAlerts = computed(() => {
  let result = alerts.value
  
  if (filterType.value) {
    result = result.filter(a => a.type === filterType.value)
  }
  
  if (filterLevel.value) {
    result = result.filter(a => a.level === filterLevel.value)
  }
  
  return result
})

// 获取数据
const refreshData = async () => {
  loading.value = true
  try {
    const res = await getAlertDashboard()
    if (res.success) {
      alerts.value = res.alerts || []
      statistics.value = res.statistics || {}
      summary.value = res.summary || {}
    }
  } catch (e) {
    ElMessage.error('数据加载失败')
  } finally {
    loading.value = false
  }
}

// 按级别筛选
const filterByLevel = (level) => {
  filterLevel.value = filterLevel.value === level ? '' : level
}

// 处理筛选变化
const handleFilterChange = () => {
  filterLevel.value = ''
}

// 处理操作
const handleAction = async (alert, action) => {
  if (action === '查看详情') {
    selectedAlert.value = alert
    detailVisible.value = true
    await markAlertRead(alert.id)
    alert.is_read = true
  } else if (action === '标记已解决' || action === '已解决') {
    await handleResolve(alert)
  } else {
    ElMessage.info(`执行操作: ${action}`)
  }
}

// 标记已解决
const handleResolve = async (alert) => {
  try {
    await markAlertResolved(alert.id)
    alert.is_read = true
    ElMessage.success('已标记为已解决')
    detailVisible.value = false
    refreshData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

// 辅助方法
const getLevelIcon = (level) => {
  const icons = { critical: '🚨', high: '⚠️', medium: '📋', low: '💡' }
  return icons[level] || '📢'
}

const getLevelText = (level) => {
  const texts = { critical: '严重', high: '高级', medium: '中级', low: '低级' }
  return texts[level] || level
}

const getTypeText = (type) => {
  const texts = { order: '订单', vehicle: '车辆', route: '路线', supply_chain: '供应链' }
  return texts[type] || type
}

const getTypeTag = (type) => {
  const tags = { order: 'danger', vehicle: 'warning', route: 'info', supply_chain: 'success' }
  return tags[type] || ''
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleDateString()
}

// 启动自动刷新
const startAutoRefresh = () => {
  refreshTimer = setInterval(() => {
    refreshData()
  }, 60000) // 每分钟刷新一次
}

onMounted(() => {
  refreshData()
  startAutoRefresh()
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
/* 移动端优先设计 */
.alert-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #0d1033 100%);
  padding: 12px;
  color: #fff;
  position: relative;
  overflow-x: hidden;
}

/* 背景效果 */
.bg-effects {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.grid-lines {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 30px 30px;
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
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding: 12px 16px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.glow-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  background: linear-gradient(90deg, #00d4ff, #00ff88, #ffd93d);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  display: none;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.health-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.health-badge.danger {
  background: rgba(255, 107, 107, 0.1);
  border-color: rgba(255, 107, 107, 0.3);
}

.health-badge.warning {
  background: rgba(255, 217, 61, 0.1);
  border-color: rgba(255, 217, 61, 0.3);
}

.health-score {
  font-size: 24px;
  font-weight: 700;
  color: #00ff88;
}

.health-badge.danger .health-score { color: #ff6b6b; }
.health-badge.warning .health-score { color: #ffd93d; }

.health-label {
  font-size: 10px;
  color: rgba(255,255,255,0.6);
}

/* 统计卡片 */
.stats-row {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-card.critical { border-left: 3px solid #ff0000; }
.stat-card.high { border-left: 3px solid #ff6b6b; }
.stat-card.medium { border-left: 3px solid #ffd93d; }
.stat-card.low { border-left: 3px solid #95e1d3; }

.stat-icon {
  font-size: 20px;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
}

.stat-card.critical .stat-value { color: #ff0000; }
.stat-card.high .stat-value { color: #ff6b6b; }
.stat-card.medium .stat-value { color: #ffd93d; }
.stat-card.low .stat-value { color: #95e1d3; }

.stat-label {
  font-size: 10px;
  color: rgba(255,255,255,0.6);
}

/* 系统建议 */
.recommendation-card {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  margin-bottom: 12px;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  font-size: 13px;
}

/* 主内容 */
.main-content {
  position: relative;
  z-index: 1;
}

/* 筛选栏 */
.filter-bar {
  margin-bottom: 12px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.filter-bar :deep(.el-radio-group) {
  display: flex;
  flex-wrap: nowrap;
  gap: 4px;
}

.filter-bar :deep(.el-radio-button__inner) {
  padding: 6px 10px;
  font-size: 12px;
  white-space: nowrap;
}

/* 预警列表 */
.alert-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-card {
  padding: 14px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 10px;
  transition: all 0.3s;
}

.alert-card.unread {
  border-left: 3px solid #00d4ff;
}

.alert-card.critical {
  background: rgba(255, 0, 0, 0.1);
  border-color: rgba(255, 0, 0, 0.3);
}

.alert-card.high {
  background: rgba(255, 107, 107, 0.08);
  border-color: rgba(255, 107, 107, 0.25);
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.alert-level {
  display: flex;
  align-items: center;
  gap: 4px;
}

.level-icon {
  font-size: 14px;
}

.level-text {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255,255,255,0.1);
}

.alert-card.critical .level-text { background: rgba(255, 0, 0, 0.3); color: #ff0000; }
.alert-card.high .level-text { background: rgba(255, 107, 107, 0.3); color: #ff6b6b; }
.alert-card.medium .level-text { background: rgba(255, 217, 61, 0.3); color: #ffd93d; }
.alert-card.low .level-text { background: rgba(149, 225, 211, 0.3); color: #95e1d3; }

.alert-time {
  margin-left: auto;
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

.alert-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}

.alert-message {
  font-size: 12px;
  color: rgba(255,255,255,0.7);
  line-height: 1.4;
  margin-bottom: 10px;
}

.alert-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.alert-actions .el-button {
  font-size: 11px;
  padding: 5px 10px;
}

/* 详情弹窗 */
.alert-detail {
  padding: 10px 0;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.detail-row .label {
  color: rgba(255,255,255,0.6);
  font-size: 13px;
}

.level-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.level-badge.critical { background: rgba(255, 0, 0, 0.3); color: #ff0000; }
.level-badge.high { background: rgba(255, 107, 107, 0.3); color: #ff6b6b; }
.level-badge.medium { background: rgba(255, 217, 61, 0.3); color: #ffd93d; }
.level-badge.low { background: rgba(149, 225, 211, 0.3); color: #95e1d3; }

.detail-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

/* Element Plus 覆盖 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #00d4ff, #00ff88);
  border: none;
  color: #000;
}

:deep(.el-tag) {
  background: rgba(0, 212, 255, 0.2);
  border-color: rgba(0, 212, 255, 0.3);
  color: #00d4ff;
}

:deep(.el-radio-button__inner) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  color: #fff;
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, #00d4ff, #00ff88);
  border-color: #00d4ff;
  color: #000;
}

:deep(.el-dialog) {
  background: #1a1a3e;
  border: 1px solid rgba(0, 212, 255, 0.2);
}

:deep(.el-dialog__title) {
  color: #fff;
}

/* 平板和桌面端适配 */
@media (min-width: 768px) {
  .alert-page {
    padding: 16px;
  }
  
  .glow-title {
    font-size: 22px;
  }
  
  .subtitle {
    display: block;
    font-size: 10px;
    color: rgba(255,255,255,0.4);
    letter-spacing: 3px;
    margin-top: 2px;
  }
  
  .stats-row {
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }
  
  .stat-card {
    padding: 16px 12px;
  }
  
  .stat-icon {
    font-size: 24px;
  }
  
  .stat-value {
    font-size: 28px;
  }
  
  .alert-card {
    padding: 16px;
  }
  
  .alert-title {
    font-size: 15px;
  }
  
  .alert-message {
    font-size: 13px;
  }
}

/* 大屏幕 */
@media (min-width: 1024px) {
  .alert-page {
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
  }
  
  .glow-title {
    font-size: 24px;
  }
  
  .stats-row {
    gap: 16px;
  }
}
</style>