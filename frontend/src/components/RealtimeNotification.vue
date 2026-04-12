<template>
  <div class="realtime-notification">
    <!-- 连接状态指示器 -->
    <div class="connection-status" :class="connected ? 'connected' : 'disconnected'">
      <span class="status-dot"></span>
      <span class="status-text">{{ connected ? '实时推送' : '未连接' }}</span>
    </div>
    
    <!-- 预警消息列表（右上角悬浮） -->
    <TransitionGroup name="alert-list" tag="div" class="alert-container">
      <div 
        v-for="alert in alerts" 
        :key="alert.id"
        class="alert-item"
        :class="alert.level"
      >
        <div class="alert-icon">
          {{ getAlertIcon(alert.type) }}
        </div>
        <div class="alert-content">
          <div class="alert-title">{{ alert.title }}</div>
          <div class="alert-message">{{ alert.message }}</div>
          <div class="alert-time">{{ formatTime(alert.time) }}</div>
        </div>
        <button class="alert-close" @click="removeAlert(alert.id)">×</button>
      </div>
    </TransitionGroup>
    
    <!-- 车辆位置更新提示（底部） -->
    <Transition name="slide-up">
      <div v-if="vehicleUpdate" class="vehicle-update-toast">
        <span class="vehicle-icon">🚛</span>
        <span class="vehicle-text">{{ vehicleUpdate }}</span>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import wsService from '@/services/websocket'

const connected = ref(false)
const alerts = ref([])
const vehicleUpdate = ref('')
let alertId = 0

// 获取预警图标
const getAlertIcon = (type) => {
  const icons = {
    weather: '🌤️',
    traffic: '🚗',
    order: '📦',
    vehicle: '🚛',
    system: '📢'
  }
  return icons[type] || '📢'
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 添加预警
const addAlert = (alert) => {
  const id = alertId++
  alerts.value.unshift({ ...alert, id })
  
  // 限制显示数量
  if (alerts.value.length > 5) {
    alerts.value.pop()
  }
  
  // 自动移除（danger 级别不自动移除）
  if (alert.level !== 'danger') {
    setTimeout(() => {
      removeAlert(id)
    }, 8000)
  }
}

// 移除预警
const removeAlert = (id) => {
  const index = alerts.value.findIndex(a => a.id === id)
  if (index > -1) {
    alerts.value.splice(index, 1)
  }
}

// 显示车辆更新提示
const showVehicleUpdate = (message) => {
  vehicleUpdate.value = message
  setTimeout(() => {
    vehicleUpdate.value = ''
  }, 3000)
}

// 事件处理
const handleConnected = () => {
  connected.value = true
}

const handleDisconnected = () => {
  connected.value = false
}

const handleAlert = (alert) => {
  addAlert(alert)
}

const handleVehiclePositions = (positions) => {
  // 可以在这里处理车辆位置更新
  // showVehicleUpdate(`${positions.length} 辆车辆位置已更新`)
}

onMounted(() => {
  // 检查当前连接状态
  connected.value = wsService.isConnected()
  
  // 如果未连接，则连接 WebSocket
  if (!connected.value) {
    wsService.connect()
  }
  
  // 监听事件
  wsService.on('connected', handleConnected)
  wsService.on('disconnected', handleDisconnected)
  wsService.on('alert', handleAlert)
  wsService.on('vehicle_positions', handleVehiclePositions)
})

onUnmounted(() => {
  wsService.off('connected', handleConnected)
  wsService.off('disconnected', handleDisconnected)
  wsService.off('alert', handleAlert)
  wsService.off('vehicle_positions', handleVehiclePositions)
})
</script>

<style scoped>
.realtime-notification {
  position: fixed;
  z-index: 9999;
  pointer-events: none;
}

/* 连接状态 */
.connection-status {
  position: fixed;
  bottom: 20px;
  left: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 20px;
  font-size: 12px;
  color: #fff;
  pointer-events: auto;
  backdrop-filter: blur(10px);
}

.connection-status.connected {
  background: rgba(0, 255, 136, 0.15);
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.connection-status.disconnected {
  background: rgba(255, 107, 107, 0.15);
  border: 1px solid rgba(255, 107, 107, 0.3);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00ff88;
  animation: pulse 2s infinite;
}

.connection-status.disconnected .status-dot {
  background: #ff6b6b;
  animation: none;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.5); }
  50% { box-shadow: 0 0 0 6px rgba(0, 255, 136, 0); }
}

.status-text {
  color: rgba(255, 255, 255, 0.8);
}

/* 预警容器 */
.alert-container {
  position: fixed;
  top: 20px;
  right: 20px;
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: auto;
}

/* 预警项 */
.alert-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: rgba(0, 0, 0, 0.85);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.alert-item.warning {
  border-left: 4px solid #ffd93d;
  background: rgba(255, 217, 61, 0.1);
}

.alert-item.danger {
  border-left: 4px solid #ff6b6b;
  background: rgba(255, 107, 107, 0.15);
}

.alert-item.info {
  border-left: 4px solid #00d4ff;
  background: rgba(0, 212, 255, 0.1);
}

.alert-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.alert-content {
  flex: 1;
  min-width: 0;
}

.alert-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 4px;
}

.alert-message {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.4;
}

.alert-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 6px;
}

.alert-close {
  width: 20px;
  height: 20px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.6);
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  flex-shrink: 0;
  transition: all 0.2s;
}

.alert-close:hover {
  background: rgba(255, 107, 107, 0.3);
  color: #ff6b6b;
}

/* 车辆更新提示 */
.vehicle-update-toast {
  position: fixed;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(0, 212, 255, 0.15);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 20px;
  color: #00d4ff;
  font-size: 13px;
  backdrop-filter: blur(10px);
}

.vehicle-icon {
  font-size: 18px;
}

/* 动画 */
.alert-list-enter-active,
.alert-list-leave-active {
  transition: all 0.3s ease;
}

.alert-list-enter-from {
  opacity: 0;
  transform: translateX(100px);
}

.alert-list-leave-to {
  opacity: 0;
  transform: translateX(100px);
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}
</style>