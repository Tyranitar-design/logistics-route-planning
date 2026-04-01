<template>
  <div class="tracking-page">
    <el-row :gutter="20">
      <!-- 左侧地图 -->
      <el-col :span="18">
        <el-card>
          <div class="map-toolbar">
            <el-select v-model="selectedOrderId" placeholder="选择订单" filterable @change="onOrderChange" style="width: 300px">
              <el-option 
                v-for="order in inTransitOrders" 
                :key="order.id"
                :label="`${order.order_number} - ${order.pickup_node?.name || '?'} → ${order.delivery_node?.name || '?'}`"
                :value="order.id"
              />
            </el-select>
            
            <div class="control-buttons" v-if="routeData">
              <el-button-group>
                <el-button :type="isPlaying ? 'primary' : 'default'" @click="togglePlay">
                  <el-icon><VideoPlay v-if="!isPlaying" /><VideoPause v-else /></el-icon>
                  {{ isPlaying ? '暂停' : '播放' }}
                </el-button>
                <el-button @click="resetSimulation">
                  <el-icon><RefreshRight /></el-icon>
                  重置
                </el-button>
              </el-button-group>
              
              <el-select v-model="playSpeed" style="width: 100px; margin-left: 10px" @change="onSpeedChange">
                <el-option label="1x" :value="1" />
                <el-option label="2x" :value="2" />
                <el-option label="5x" :value="5" />
                <el-option label="10x" :value="10" />
              </el-select>
            </div>
          </div>
          
          <div id="tracking-map" class="map-container"></div>
        </el-card>
      </el-col>
      
      <!-- 右侧信息面板 -->
      <el-col :span="6">
        <!-- 订单信息 -->
        <el-card v-if="currentOrder" class="order-info-card">
          <template #header>
            <span>订单信息</span>
          </template>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="订单号">{{ currentOrder.order_number }}</el-descriptions-item>
            <el-descriptions-item label="货物">{{ currentOrder.cargo_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="起点">{{ currentOrder.pickup_node?.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="终点">{{ currentOrder.delivery_node?.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusType(currentOrder.status)" size="small">
                {{ statusMap[currentOrder.status] }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
        
        <!-- 运输进度 -->
        <el-card v-if="routeData" class="progress-card">
          <template #header>
            <span>运输进度</span>
          </template>
          
          <div class="progress-info">
            <el-progress 
              :percentage="currentProgress" 
              :stroke-width="20"
              :format="formatProgress"
              :color="getProgressColor"
            />
            
            <div class="progress-details">
              <div class="detail-item">
                <span class="label">已行驶</span>
                <span class="value">{{ traveledDistance }} 公里</span>
              </div>
              <div class="detail-item">
                <span class="label">剩余</span>
                <span class="value">{{ remainingDistance }} 公里</span>
              </div>
              <div class="detail-item">
                <span class="label">预计到达</span>
                <span class="value highlight">{{ estimatedArrival }}</span>
              </div>
            </div>
          </div>
        </el-card>
        
        <!-- 车辆信息 -->
        <el-card v-if="currentVehicle" class="vehicle-card">
          <template #header>
            <span>车辆信息</span>
          </template>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="车牌">{{ currentVehicle.plate_number }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ currentVehicle.vehicle_type }}</el-descriptions-item>
            <el-descriptions-item label="司机">{{ currentVehicle.driver_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="电话">{{ currentVehicle.driver_phone || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
        
        <!-- 图例 -->
        <el-card class="legend-card">
          <template #header>
            <span>图例</span>
          </template>
          <div class="legend">
            <div class="legend-item">
              <span class="legend-marker start"></span>
              <span>起点</span>
            </div>
            <div class="legend-item">
              <span class="legend-marker end"></span>
              <span>终点</span>
            </div>
            <div class="legend-item">
              <span class="legend-marker truck"></span>
              <span>车辆</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { getOrders, getOrder } from '@/api/orders'
import { getRoutePolyline, simulateTracking, estimateArrival } from '@/api/tracking'
import { ElMessage } from 'element-plus'
import { VideoPlay, VideoPause, RefreshRight } from '@element-plus/icons-vue'

// 数据
const orders = ref([])
const selectedOrderId = ref(null)
const currentOrder = ref(null)
const currentVehicle = ref(null)
const routeData = ref(null)
const inTransitOrders = ref([])

// 模拟控制
const isPlaying = ref(false)
const playSpeed = ref(1)
const currentProgress = ref(0)
const animationFrameId = ref(null)
const lastTimestamp = ref(0)

// 地图相关
let map = null
let routeLine = null
let vehicleMarker = null
let startMarker = null
let endMarker = null

// 状态映射
const statusMap = {
  pending: '待分配',
  assigned: '已分配',
  in_transit: '运输中',
  delivered: '已送达',
  cancelled: '已取消'
}

// 计算属性
const traveledDistance = computed(() => {
  if (!routeData.value) return '0'
  return (routeData.value.distance_km * currentProgress.value / 100).toFixed(1)
})

const remainingDistance = computed(() => {
  if (!routeData.value) return '0'
  return (routeData.value.distance_km * (100 - currentProgress.value) / 100).toFixed(1)
})

const estimatedArrival = computed(() => {
  if (!routeData.value) return '-'
  const remainingMinutes = routeData.value.duration_minutes * (100 - currentProgress.value) / 100
  const eta = new Date(Date.now() + remainingMinutes * 60 * 1000)
  return eta.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})

// 方法
const getStatusType = (status) => {
  const types = {
    pending: 'info',
    assigned: 'warning',
    in_transit: 'primary',
    delivered: 'success',
    cancelled: 'danger'
  }
  return types[status] || 'info'
}

const formatProgress = (percentage) => {
  return `${percentage.toFixed(0)}%`
}

const getProgressColor = (percentage) => {
  if (percentage < 30) return '#409EFF'
  if (percentage < 70) return '#E6A23C'
  return '#67C23A'
}

// 加载订单列表
const loadOrders = async () => {
  try {
    const res = await getOrders({ per_page: 100 })
    orders.value = res.orders || []
    // 筛选运输中的订单（或所有订单用于演示）
    inTransitOrders.value = orders.value.filter(o => 
      o.status === 'in_transit' || o.status === 'assigned' || o.status === 'pending'
    )
    
    // 如果没有运输中的订单，显示所有订单
    if (inTransitOrders.value.length === 0) {
      inTransitOrders.value = orders.value.slice(0, 10)
    }
  } catch (error) {
    console.error('加载订单失败:', error)
  }
}

// 订单变化
const onOrderChange = async (orderId) => {
  if (!orderId) {
    currentOrder.value = null
    routeData.value = null
    return
  }
  
  // 停止当前动画
  stopAnimation()
  
  try {
    // 获取订单详情
    const orderRes = await getOrder(orderId)
    currentOrder.value = orderRes.order
    
    // 获取轨迹模拟数据
    const trackRes = await simulateTracking(orderId, playSpeed.value)
    
    if (trackRes.success) {
      routeData.value = trackRes.data.route
      currentVehicle.value = trackRes.data.vehicle
      
      // 绘制路线
      await drawRoute()
    } else {
      ElMessage.error(trackRes.error || '获取路线失败')
    }
  } catch (error) {
    console.error('加载订单轨迹失败:', error)
    ElMessage.error('加载订单轨迹失败')
  }
}

// 初始化地图
const initMap = async () => {
  // 动态加载 Leaflet
  if (!window.L) {
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    document.head.appendChild(link)
    
    await new Promise((resolve) => {
      const script = document.createElement('script')
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
      script.onload = resolve
      document.head.appendChild(script)
    })
  }
  
  const L = window.L
  if (!L) return
  
  // 创建地图
  map = L.map('tracking-map').setView([35.8617, 104.1954], 4)
  
  // 高德地图图层
  L.tileLayer(
    'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
    {
      subdomains: ['1', '2', '3', '4'],
      attribution: '© 高德地图',
      maxZoom: 18
    }
  ).addTo(map)
}

// 绘制路线
const drawRoute = async () => {
  const L = window.L
  if (!L || !map || !routeData.value) return
  
  // 清除旧图层
  if (routeLine) map.removeLayer(routeLine)
  if (vehicleMarker) map.removeLayer(vehicleMarker)
  if (startMarker) map.removeLayer(startMarker)
  if (endMarker) map.removeLayer(endMarker)
  
  const polyline = routeData.value.polyline
  if (!polyline || polyline.length < 2) return
  
  // 转换坐标 - polyline 格式为 [[lng, lat], ...]，Leaflet 需要 [lat, lng]
  let coords
  if (Array.isArray(polyline[0])) {
    // 格式: [[lng, lat], ...]
    coords = polyline.map(p => [p[1], p[0]])
  } else if (typeof polyline[0] === 'object') {
    // 格式: [{latitude, longitude}, ...]
    coords = polyline.map(p => [p.latitude, p.longitude])
  } else {
    console.error('未知的 polyline 格式:', polyline[0])
    return
  }
  
  // 绘制路线
  routeLine = L.polyline(coords, {
    color: '#409EFF',
    weight: 5,
    opacity: 0.8
  }).addTo(map)
  
  // 起点标记
  const startIcon = L.divIcon({
    className: 'custom-marker start-marker',
    html: '<div class="marker-inner start">起</div>',
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  })
  startMarker = L.marker(coords[0], { icon: startIcon }).addTo(map)
  
  // 终点标记
  const endIcon = L.divIcon({
    className: 'custom-marker end-marker',
    html: '<div class="marker-inner end">终</div>',
    iconSize: [30, 30],
    iconAnchor: [15, 15]
  })
  endMarker = L.marker(coords[coords.length - 1], { icon: endIcon }).addTo(map)
  
  // 车辆标记
  const truckIcon = L.divIcon({
    className: 'custom-marker truck-marker',
    html: '<div class="marker-inner truck">🚚</div>',
    iconSize: [36, 36],
    iconAnchor: [18, 18]
  })
  vehicleMarker = L.marker(coords[0], { icon: truckIcon }).addTo(map)
  
  // 调整视野
  map.fitBounds(routeLine.getBounds(), { padding: [50, 50] })
  
  // 重置进度
  currentProgress.value = 0
}

// 播放/暂停
const togglePlay = () => {
  if (isPlaying.value) {
    stopAnimation()
  } else {
    startAnimation()
  }
}

// 开始动画
const startAnimation = () => {
  if (!routeData.value?.polyline) return
  
  isPlaying.value = true
  lastTimestamp.value = performance.now()
  animate()
}

// 停止动画
const stopAnimation = () => {
  isPlaying.value = false
  if (animationFrameId.value) {
    cancelAnimationFrame(animationFrameId.value)
    animationFrameId.value = null
  }
}

// 动画循环
const animate = () => {
  if (!isPlaying.value) return
  
  const now = performance.now()
  const delta = (now - lastTimestamp.value) / 1000 // 秒
  lastTimestamp.value = now
  
  // 更新进度
  // 假设完整路线需要60秒播放完（基于速度倍数）
  const baseDuration = 60 // 秒
  const progressIncrement = (delta / baseDuration) * 100 * playSpeed.value
  currentProgress.value = Math.min(100, currentProgress.value + progressIncrement)
  
  // 更新车辆位置
  updateVehiclePosition()
  
  if (currentProgress.value >= 100) {
    stopAnimation()
    ElMessage.success('运输完成！')
    return
  }
  
  animationFrameId.value = requestAnimationFrame(animate)
}

// 更新车辆位置
const updateVehiclePosition = () => {
  const L = window.L
  if (!L || !map || !vehicleMarker || !routeData.value?.polyline) return
  
  const polyline = routeData.value.polyline
  
  // 转换坐标 - 兼容两种格式
  let coords
  if (Array.isArray(polyline[0])) {
    coords = polyline.map(p => [p[1], p[0]])
  } else if (typeof polyline[0] === 'object') {
    coords = polyline.map(p => [p.latitude, p.longitude])
  } else {
    return
  }
  
  // 计算当前位置
  const totalPoints = coords.length
  const currentIndex = Math.floor((currentProgress.value / 100) * (totalPoints - 1))
  const nextIndex = Math.min(currentIndex + 1, totalPoints - 1)
  
  // 插值计算精确位置
  const segmentProgress = (currentProgress.value / 100) * (totalPoints - 1) - currentIndex
  const current = coords[currentIndex]
  const next = coords[nextIndex]
  
  const lat = current[0] + (next[0] - current[0]) * segmentProgress
  const lng = current[1] + (next[1] - current[1]) * segmentProgress
  
  vehicleMarker.setLatLng([lat, lng])
}

// 重置模拟
const resetSimulation = () => {
  stopAnimation()
  currentProgress.value = 0
  updateVehiclePosition()
}

// 速度变化
const onSpeedChange = () => {
  // 可以在这里调整动画速度
}

// 生命周期
onMounted(async () => {
  await loadOrders()
  await nextTick()
  await initMap()
})

onUnmounted(() => {
  stopAnimation()
})
</script>

<style scoped>
.tracking-page {
  padding: 20px;
}

.map-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 8px;
}

.control-buttons {
  display: flex;
  align-items: center;
}

.map-container {
  width: 100%;
  height: calc(100vh - 280px);
  min-height: 500px;
  border-radius: 8px;
}

.order-info-card,
.progress-card,
.vehicle-card,
.legend-card {
  margin-bottom: 15px;
}

.progress-info {
  padding: 10px 0;
}

.progress-details {
  margin-top: 20px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #ebeef5;
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-item .label {
  color: #909399;
}

.detail-item .value {
  font-weight: 500;
}

.detail-item .value.highlight {
  color: #409EFF;
  font-size: 16px;
}

.legend {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.legend-marker {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.legend-marker.start {
  background: #67C23A;
}

.legend-marker.end {
  background: #F56C6C;
}

.legend-marker.truck {
  background: #409EFF;
}
</style>

<style>
/* 地图标记样式 */
.custom-marker {
  background: transparent !important;
  border: none !important;
}

.marker-inner {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.marker-inner.start {
  background: #67C23A;
  font-size: 12px;
}

.marker-inner.end {
  background: #F56C6C;
  font-size: 12px;
}

.marker-inner.truck {
  background: #409EFF;
  font-size: 18px;
  width: 36px;
  height: 36px;
}
</style>
