<template>
  <div class="vehicle-realtime-panel">
    <div class="panel-header">
      <span class="panel-title">🚛 实时车辆位置</span>
      <span class="update-time">{{ lastUpdate }}</span>
    </div>
    
    <div class="vehicle-list">
      <TransitionGroup name="vehicle-list">
        <div 
          v-for="vehicle in vehicles" 
          :key="vehicle.plate_number"
          class="vehicle-item"
          :class="vehicle.status"
        >
          <div class="vehicle-icon">
            {{ vehicle.status === 'in_transit' ? '🚚' : vehicle.status === 'idle' ? '🅿️' : '🔧' }}
          </div>
          <div class="vehicle-info">
            <div class="vehicle-plate">{{ vehicle.plate_number }}</div>
            <div class="vehicle-status">
              <span class="status-badge" :class="vehicle.status">
                {{ getStatusText(vehicle.status) }}
              </span>
              <span v-if="vehicle.speed > 0" class="vehicle-speed">
                {{ vehicle.speed }} km/h
              </span>
            </div>
          </div>
          <div class="vehicle-coords">
            {{ vehicle.lat.toFixed(4) }}, {{ vehicle.lng.toFixed(4) }}
          </div>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import wsService from '@/services/websocket'

const vehicles = ref([])
const lastUpdate = ref('-')

// 获取状态文本
const getStatusText = (status) => {
  const map = {
    'in_transit': '运输中',
    'idle': '空闲',
    'maintenance': '维护中'
  }
  return map[status] || status
}

// 格式化时间
const formatTime = () => {
  const now = new Date()
  return now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// 处理车辆位置更新
const handleVehiclePositions = (positions) => {
  vehicles.value = positions
  lastUpdate.value = formatTime()
}

onMounted(() => {
  wsService.on('vehicle_positions', handleVehiclePositions)
})

onUnmounted(() => {
  wsService.off('vehicle_positions', handleVehiclePositions)
})
</script>

<style scoped>
.vehicle-realtime-panel {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
  padding: 12px;
  backdrop-filter: blur(5px);
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
  color: #fff;
}

.update-time {
  font-size: 11px;
  color: #00ff88;
  font-family: 'Courier New', monospace;
}

.vehicle-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.vehicle-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: rgba(0, 212, 255, 0.03);
  border-radius: 8px;
  border-left: 3px solid rgba(0, 212, 255, 0.3);
  transition: all 0.3s;
}

.vehicle-item:hover {
  background: rgba(0, 212, 255, 0.08);
}

.vehicle-item.in_transit {
  border-left-color: #00ff88;
}

.vehicle-item.idle {
  border-left-color: #ffd93d;
}

.vehicle-item.maintenance {
  border-left-color: #ff6b6b;
}

.vehicle-icon {
  font-size: 20px;
}

.vehicle-info {
  flex: 1;
}

.vehicle-plate {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.vehicle-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 500;
}

.status-badge.in_transit {
  background: rgba(0, 255, 136, 0.2);
  color: #00ff88;
}

.status-badge.idle {
  background: rgba(255, 217, 61, 0.2);
  color: #ffd93d;
}

.status-badge.maintenance {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
}

.vehicle-speed {
  font-size: 11px;
  color: #00d4ff;
  font-family: 'Courier New', monospace;
}

.vehicle-coords {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  font-family: 'Courier New', monospace;
}

/* 动画 */
.vehicle-list-move,
.vehicle-list-enter-active,
.vehicle-list-leave-active {
  transition: all 0.3s ease;
}

.vehicle-list-enter-from,
.vehicle-list-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.vehicle-list-leave-active {
  position: absolute;
}
</style>