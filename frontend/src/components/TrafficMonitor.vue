<template>
  <div class="traffic-monitor">
    <!-- 路况概览卡片 -->
    <div class="traffic-overview">
      <div class="overview-header">
        <span class="overview-icon">🚦</span>
        <span class="overview-title">实时路况监控</span>
        <el-tag :type="overallStatus.type" size="small" effect="dark">
          {{ overallStatus.text }}
        </el-tag>
      </div>
      
      <div class="traffic-stats">
        <div class="stat-item" v-for="(count, level) in trafficStats" :key="level">
          <span class="stat-dot" :style="{ background: getLevelColor(level) }"></span>
          <span class="stat-label">{{ level }}</span>
          <span class="stat-value">{{ count }}段</span>
        </div>
      </div>
    </div>
    
    <!-- 拥堵路段列表 -->
    <div class="congestion-list" v-if="congestions.length > 0">
      <div class="list-header">
        <span>⚠️ 拥堵路段</span>
        <el-button size="small" type="primary" link @click="autoAvoid">
          🔄 自动规避
        </el-button>
      </div>
      
      <div class="congestion-item" v-for="(item, index) in congestions" :key="index">
        <div class="item-header">
          <span class="item-level" :style="{ background: getLevelColor(item.level_name) }">
            {{ item.level_name }}
          </span>
          <span class="item-road">{{ item.road }}</span>
        </div>
        <div class="item-desc">{{ item.description }}</div>
        <div class="item-meta">
          <span>📏 {{ item.distance }}米</span>
        </div>
      </div>
    </div>
    
    <!-- 备选路线 -->
    <div class="alternatives" v-if="alternatives.length > 0">
      <div class="list-header">
        <span>🛣️ 推荐备选路线</span>
      </div>
      
      <div 
        class="alternative-item" 
        v-for="(route, index) in alternatives" 
        :key="index"
        :class="{ active: selectedAlternative === index }"
        @click="selectAlternative(index)"
      >
        <div class="alt-header">
          <span class="alt-strategy">{{ route.strategy }}</span>
          <span class="alt-score">路况评分: {{ route.traffic_score }}分</span>
        </div>
        <div class="alt-info">
          <span>📏 {{ (route.distance / 1000).toFixed(1) }}km</span>
          <span>⏱️ {{ Math.round(route.duration / 60) }}分钟</span>
          <span>🚦 {{ route.traffic_lights }}个红绿灯</span>
        </div>
        <div class="alt-toll" v-if="route.tolls > 0">
          💰 过路费: ¥{{ route.tolls }}
        </div>
      </div>
    </div>
    
    <!-- 推荐提示 -->
    <div class="recommendation" v-if="recommendation">
      <div class="rec-icon">💡</div>
      <div class="rec-content">
        <div class="rec-message">{{ recommendation.message }}</div>
        <div class="rec-action" v-if="recommendation.action === 'reroute'">
          <el-button type="primary" size="small" @click="applyRecommendation">
            立即切换路线
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 操作按钮 -->
    <div class="actions">
      <el-button @click="refreshTraffic" :loading="loading">
        🔄 刷新路况
      </el-button>
      <el-button type="primary" @click="startMonitor" v-if="!isMonitoring">
        📡 开始监控
      </el-button>
      <el-button type="danger" @click="stopMonitor" v-else>
        ⏹️ 停止监控
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { analyzeAndAvoid, checkRouteTraffic } from '@/api/traffic'
import { ElMessage, ElNotification } from 'element-plus'

const props = defineProps({
  origin: {
    type: String,
    required: true
  },
  destination: {
    type: String,
    required: true
  },
  waypoints: {
    type: String,
    default: ''
  },
  autoStart: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['route-change', 'traffic-update'])

// 状态
const loading = ref(false)
const isMonitoring = ref(false)
const monitorInterval = ref(null)
const congestions = ref([])
const alternatives = ref([])
const recommendation = ref(null)
const selectedAlternative = ref(0)
const trafficStats = ref({
  '畅通': 0,
  '基本畅通': 0,
  '轻度拥堵': 0,
  '中度拥堵': 0,
  '严重拥堵': 0
})

// 总体状态
const overallStatus = computed(() => {
  if (congestions.value.length === 0) {
    return { type: 'success', text: '路况良好' }
  }
  
  const severeCount = congestions.value.filter(c => c.level >= 4).length
  if (severeCount > 0) {
    return { type: 'danger', text: '严重拥堵' }
  }
  
  return { type: 'warning', text: '部分拥堵' }
})

// 获取路况等级颜色
const getLevelColor = (level) => {
  const colors = {
    '畅通': '#00ff88',
    '基本畅通': '#88ff00',
    '轻度拥堵': '#ffcc00',
    '中度拥堵': '#ff9900',
    '严重拥堵': '#ff0000',
    '未知': '#999999'
  }
  return colors[level] || '#999999'
}

// 分析路况
const analyzeTraffic = async () => {
  loading.value = true
  
  try {
    const result = await analyzeAndAvoid({
      origin: props.origin,
      destination: props.destination,
      waypoints: props.waypoints,
      threshold: 3 // 中度拥堵及以上触发规避
    })
    
    if (result.success) {
      congestions.value = result.congestions || []
      alternatives.value = result.alternatives || []
      recommendation.value = result.recommendation || null
      
      // 发送事件
      emit('traffic-update', {
        hasCongestion: result.has_congestion,
        congestions: congestions.value,
        alternatives: alternatives.value
      })
      
      // 如果有严重拥堵，弹出通知
      if (congestions.value.some(c => c.level >= 4)) {
        ElNotification({
          title: '⚠️ 路况预警',
          message: `检测到${congestions.value.length}处拥堵路段，建议切换路线`,
          type: 'warning',
          duration: 5000
        })
      }
    } else {
      console.error('路况分析失败:', result.error)
    }
  } catch (e) {
    console.error('路况分析异常:', e)
  } finally {
    loading.value = false
  }
}

// 刷新路况
const refreshTraffic = () => {
  analyzeTraffic()
}

// 自动规避
const autoAvoid = () => {
  if (alternatives.value.length > 0) {
    selectAlternative(0)
    applyRecommendation()
  } else {
    ElMessage.warning('暂无可用备选路线')
  }
}

// 选择备选路线
const selectAlternative = (index) => {
  selectedAlternative.value = index
}

// 应用推荐路线
const applyRecommendation = () => {
  const route = alternatives.value[selectedAlternative.value]
  if (route) {
    emit('route-change', {
      polyline: route.polyline,
      distance: route.distance,
      duration: route.duration,
      strategy: route.strategy
    })
    
    ElMessage.success(`已切换至"${route.strategy}"路线`)
  }
}

// 开始监控
const startMonitor = () => {
  isMonitoring.value = true
  
  // 立即检查一次
  analyzeTraffic()
  
  // 每5分钟检查一次
  monitorInterval.value = setInterval(() => {
    analyzeTraffic()
  }, 5 * 60 * 1000)
  
  ElMessage.success('已开始路况监控，每5分钟自动更新')
}

// 停止监控
const stopMonitor = () => {
  isMonitoring.value = false
  
  if (monitorInterval.value) {
    clearInterval(monitorInterval.value)
    monitorInterval.value = null
  }
  
  ElMessage.info('已停止路况监控')
}

// 生命周期
onMounted(() => {
  if (props.autoStart) {
    startMonitor()
  }
})

onUnmounted(() => {
  stopMonitor()
})

// 暴露方法
defineExpose({
  refreshTraffic,
  startMonitor,
  stopMonitor
})
</script>

<style scoped>
.traffic-monitor {
  padding: 16px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
}

/* 概览 */
.traffic-overview {
  margin-bottom: 16px;
}

.overview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.overview-icon {
  font-size: 20px;
}

.overview-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  flex: 1;
}

.traffic-stats {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.stat-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.stat-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}

.stat-value {
  font-size: 11px;
  color: #fff;
  font-weight: 500;
}

/* 拥堵列表 */
.congestion-list {
  margin-bottom: 16px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: #fff;
}

.congestion-item {
  padding: 10px;
  margin-bottom: 8px;
  background: rgba(255, 107, 107, 0.1);
  border: 1px solid rgba(255, 107, 107, 0.3);
  border-radius: 8px;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.item-level {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  color: #000;
  font-weight: 600;
}

.item-road {
  font-size: 12px;
  color: #fff;
  font-weight: 500;
}

.item-desc {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 4px;
}

.item-meta {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}

/* 备选路线 */
.alternatives {
  margin-bottom: 16px;
}

.alternative-item {
  padding: 10px;
  margin-bottom: 8px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.alternative-item:hover {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.4);
}

.alternative-item.active {
  background: rgba(0, 212, 255, 0.15);
  border-color: #00d4ff;
}

.alt-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.alt-strategy {
  font-size: 13px;
  color: #00d4ff;
  font-weight: 500;
}

.alt-score {
  font-size: 11px;
  color: #00ff88;
}

.alt-info {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}

.alt-toll {
  margin-top: 6px;
  font-size: 11px;
  color: #ffd93d;
}

/* 推荐 */
.recommendation {
  display: flex;
  gap: 10px;
  padding: 12px;
  background: rgba(255, 217, 61, 0.1);
  border: 1px solid rgba(255, 217, 61, 0.3);
  border-radius: 8px;
  margin-bottom: 16px;
}

.rec-icon {
  font-size: 24px;
}

.rec-content {
  flex: 1;
}

.rec-message {
  font-size: 12px;
  color: #fff;
  margin-bottom: 8px;
}

/* 操作按钮 */
.actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}

/* Element Plus 覆盖 */
:deep(.el-button) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.3);
  color: #fff;
}

:deep(.el-button:hover) {
  background: rgba(0, 212, 255, 0.2);
  border-color: #00d4ff;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #00d4ff, #0088cc);
  border-color: #00d4ff;
}

:deep(.el-tag) {
  background: rgba(0, 212, 255, 0.2);
  border-color: rgba(0, 212, 255, 0.3);
  color: #00d4ff;
}

:deep(.el-tag.el-tag--success) {
  background: rgba(0, 255, 136, 0.2);
  border-color: rgba(0, 255, 136, 0.3);
  color: #00ff88;
}

:deep(.el-tag.el-tag--warning) {
  background: rgba(255, 204, 0, 0.2);
  border-color: rgba(255, 204, 0, 0.3);
  color: #ffcc00;
}

:deep(.el-tag.el-tag--danger) {
  background: rgba(255, 107, 107, 0.2);
  border-color: rgba(255, 107, 107, 0.3);
  color: #ff6b6b;
}
</style>
