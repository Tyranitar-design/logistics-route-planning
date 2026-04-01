<template>
  <div class="weather-card">
    <!-- 当前天气 -->
    <div v-if="weatherData" class="current-weather">
      <div class="weather-main">
        <span class="weather-icon">{{ getWeatherIcon(weatherData.weather) }}</span>
        <div class="weather-info">
          <div class="temperature">{{ weatherData.temperature }}°C</div>
          <div class="weather-text">{{ weatherData.weather }}</div>
          <div class="city-name">{{ weatherData.city }}</div>
        </div>
      </div>
      
      <div class="weather-details">
        <div class="detail-item">
          <span class="label">风向</span>
          <span class="value">{{ weatherData.wind_direction }}风</span>
        </div>
        <div class="detail-item">
          <span class="label">风力</span>
          <span class="value">{{ weatherData.wind_power }}级</span>
        </div>
        <div class="detail-item">
          <span class="label">湿度</span>
          <span class="value">{{ weatherData.humidity }}%</span>
        </div>
      </div>
      
      <!-- 运输影响 -->
      <div v-if="transportImpact" class="transport-impact" :class="getImpactClass(transportImpact.impact_level)">
        <div class="impact-header">
          <span class="impact-icon">{{ getImpactIcon(transportImpact.impact_level) }}</span>
          <span class="impact-level">{{ transportImpact.impact_level }}</span>
        </div>
        
        <div v-if="transportImpact.safety_warning" class="safety-warning">
          {{ transportImpact.safety_warning }}
        </div>
        
        <div class="suggestions">
          <div v-for="(suggestion, index) in transportImpact.suggestions.slice(0, 3)" 
               :key="index" 
               class="suggestion-item">
            {{ suggestion }}
          </div>
        </div>
        
        <div class="impact-metrics">
          <div class="metric">
            <span class="metric-label">速度影响</span>
            <el-progress 
              :percentage="transportImpact.speed_reduction * 100" 
              :stroke-width="8"
              :color="getProgressColor(transportImpact.speed_reduction)"
              :show-text="false"
            />
            <span class="metric-value">-{{ (transportImpact.speed_reduction * 100).toFixed(0) }}%</span>
          </div>
          <div class="metric">
            <span class="metric-label">延误风险</span>
            <el-progress 
              :percentage="transportImpact.delay_risk * 100" 
              :stroke-width="8"
              :color="getProgressColor(transportImpact.delay_risk)"
              :show-text="false"
            />
            <span class="metric-value">{{ (transportImpact.delay_risk * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 加载中 -->
    <div v-else-if="loading" class="loading-state">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>获取天气中...</span>
    </div>
    
    <!-- 无数据 -->
    <div v-else class="empty-state">
      <span class="empty-icon">🌤️</span>
      <span>选择节点查看天气</span>
    </div>
    
    <!-- 刷新按钮 -->
    <el-button 
      v-if="weatherData" 
      size="small" 
      text 
      @click="refreshWeather"
      :loading="loading"
      class="refresh-btn"
    >
      刷新
    </el-button>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { getNodeWeather, getWeatherNow } from '@/api/weather'
import { Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  nodeId: {
    type: Number,
    default: null
  },
  city: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['weather-loaded'])

const weatherData = ref(null)
const transportImpact = ref(null)
const loading = ref(false)

// 天气图标映射
const weatherIcons = {
  '晴': '☀️',
  '多云': '⛅',
  '阴': '☁️',
  '小雨': '🌧️',
  '中雨': '🌧️',
  '大雨': '🌧️',
  '暴雨': '⛈️',
  '小雪': '🌨️',
  '中雪': '🌨️',
  '大雪': '❄️',
  '雾': '🌫️',
  '霾': '😷',
  '沙尘暴': '🌪️',
  'default': '🌤️'
}

// 影响等级图标
const impactIcons = {
  '无影响': '✅',
  '轻微影响': '⚠️',
  '中度影响': '🔶',
  '严重影响': '🔴',
  '极端影响，建议暂停运输': '🚨'
}

const getWeatherIcon = (weather) => {
  return weatherIcons[weather] || weatherIcons['default']
}

const getImpactIcon = (level) => {
  return impactIcons[level] || '❓'
}

const getImpactClass = (level) => {
  if (level === '无影响') return 'impact-none'
  if (level === '轻微影响') return 'impact-minor'
  if (level === '中度影响') return 'impact-moderate'
  if (level === '严重影响') return 'impact-severe'
  return 'impact-extreme'
}

const getProgressColor = (value) => {
  if (value < 0.2) return '#67C23A'
  if (value < 0.4) return '#E6A23C'
  if (value < 0.6) return '#F56C6C'
  return '#909399'
}

const loadWeather = async () => {
  if (!props.nodeId && !props.city) return
  
  loading.value = true
  
  try {
    let result
    
    if (props.nodeId) {
      result = await getNodeWeather(props.nodeId)
    } else {
      result = await getWeatherNow(props.city)
    }
    
    if (result.success) {
      weatherData.value = result.data
      transportImpact.value = result.data.transport_impact
      
      emit('weather-loaded', result.data)
    } else {
      ElMessage.error(result.error || '获取天气失败')
    }
  } catch (error) {
    console.error('获取天气失败:', error)
    ElMessage.error('获取天气失败')
  } finally {
    loading.value = false
  }
}

const refreshWeather = () => {
  loadWeather()
}

// 监听节点变化
watch(() => props.nodeId, (newVal) => {
  if (newVal) {
    loadWeather()
  }
})

watch(() => props.city, (newVal) => {
  if (newVal) {
    loadWeather()
  }
})

onMounted(() => {
  if (props.nodeId || props.city) {
    loadWeather()
  }
})
</script>

<style scoped>
.weather-card {
  position: relative;
  padding: 15px;
}

.current-weather {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.weather-main {
  display: flex;
  align-items: center;
  gap: 15px;
}

.weather-icon {
  font-size: 48px;
}

.weather-info {
  flex: 1;
}

.temperature {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.weather-text {
  font-size: 14px;
  color: #606266;
  margin-top: 4px;
}

.city-name {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.weather-details {
  display: flex;
  gap: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 8px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.detail-item .label {
  font-size: 12px;
  color: #909399;
}

.detail-item .value {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-top: 4px;
}

/* 运输影响样式 */
.transport-impact {
  padding: 12px;
  border-radius: 8px;
  margin-top: 10px;
}

.impact-none {
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
}

.impact-minor {
  background: #fdf6ec;
  border: 1px solid #faecd8;
}

.impact-moderate {
  background: #fef0f0;
  border: 1px solid #fde2e2;
}

.impact-severe,
.impact-extreme {
  background: #fef0f0;
  border: 1px solid #fbc4c4;
}

.impact-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.impact-icon {
  font-size: 20px;
}

.impact-level {
  font-weight: bold;
  font-size: 14px;
}

.safety-warning {
  padding: 8px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 4px;
  font-size: 13px;
  color: #f56c6c;
  margin-bottom: 10px;
}

.suggestions {
  margin-bottom: 10px;
}

.suggestion-item {
  font-size: 12px;
  color: #606266;
  padding: 4px 0;
  border-bottom: 1px dashed #ebeef5;
}

.suggestion-item:last-child {
  border-bottom: none;
}

.impact-metrics {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.metric {
  display: flex;
  align-items: center;
  gap: 10px;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  width: 60px;
}

.metric .el-progress {
  flex: 1;
}

.metric-value {
  font-size: 12px;
  font-weight: bold;
  width: 40px;
  text-align: right;
}

/* 加载和空状态 */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 30px;
  color: #909399;
}

.empty-icon {
  font-size: 32px;
  margin-bottom: 10px;
}

.refresh-btn {
  position: absolute;
  top: 10px;
  right: 10px;
}
</style>
