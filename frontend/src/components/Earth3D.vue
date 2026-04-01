<template>
  <div class="earth-container">
    <div ref="earthChart" class="earth-chart"></div>
    
    <!-- 控制面板 -->
    <div class="control-panel">
      <div class="panel-title">🌍 3D 地球控制</div>
      <div class="control-item">
        <span class="control-label">自动旋转</span>
        <el-switch v-model="autoRotate" @change="toggleAutoRotate" />
      </div>
      <div class="control-item">
        <span class="control-label">显示轨迹</span>
        <el-switch v-model="showTracks" @change="updateChart" />
      </div>
      <div class="control-item">
        <span class="control-label">🚚 车辆动画</span>
        <el-switch v-model="showVehicleAnimation" @change="toggleVehicleAnimation" />
      </div>
      <div class="control-item" v-if="showVehicleAnimation">
        <span class="control-label">动画速度</span>
        <el-slider v-model="animationSpeed" :min="1" :max="10" :step="1" style="width: 80px" />
      </div>
    </div>
    
    <!-- 图例 -->
    <div class="legend-panel">
      <div class="legend-item">
        <span class="legend-dot warehouse"></span>
        <span class="legend-text">仓库</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot station"></span>
        <span class="legend-text">配送站</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot customer"></span>
        <span class="legend-text">客户点</span>
      </div>
      <div class="legend-item">
        <span class="legend-line"></span>
        <span class="legend-text">运输轨迹</span>
      </div>
      <div class="legend-item" v-if="showVehicleAnimation">
        <span class="legend-dot vehicle"></span>
        <span class="legend-text">运输车辆</span>
      </div>
    </div>
    
    <!-- 车辆信息卡片 -->
    <transition name="fade">
      <div v-if="showVehicleAnimation && currentVehicleInfo" class="vehicle-info-card">
        <div class="info-header">
          <span class="info-icon">🚚</span>
          <span class="info-name">{{ currentVehicleInfo.route }}</span>
        </div>
        <div class="info-content">
          <div class="info-row">
            <span class="info-label">进度</span>
            <span class="info-value">{{ currentVehicleInfo.progress }}%</span>
          </div>
          <div class="info-row">
            <span class="info-label">状态</span>
            <span class="info-value highlight">运输中</span>
          </div>
        </div>
      </div>
    </transition>
    
    <!-- 节点信息卡片 -->
    <transition name="fade">
      <div v-if="selectedNode && !showVehicleAnimation" class="info-card">
        <div class="info-header">
          <span class="info-icon">{{ getNodeIcon(selectedNode.type) }}</span>
          <span class="info-name">{{ selectedNode.name }}</span>
          <el-tag size="small" :type="getStatusType(selectedNode.status)">{{ selectedNode.status }}</el-tag>
        </div>
        <div class="info-content">
          <div class="info-row">
            <span class="info-label">📍 坐标:</span>
            <span class="info-value">{{ selectedNode.lng?.toFixed(2) }}, {{ selectedNode.lat?.toFixed(2) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">📦 订单量:</span>
            <span class="info-value">{{ selectedNode.orders || 0 }} 单</span>
          </div>
          <div class="info-row">
            <span class="info-label">🚛 车辆:</span>
            <span class="info-value">{{ selectedNode.vehicles || 0 }} 辆</span>
          </div>
        </div>
      </div>
    </transition>
    
    <!-- 统计信息 -->
    <div class="stats-panel">
      <div class="stat-item">
        <span class="stat-value">{{ animatedStats.nodes }}</span>
        <span class="stat-label">节点总数</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ animatedStats.tracks }}</span>
        <span class="stat-label">运输轨迹</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ animatedStats.distance }}</span>
        <span class="stat-label">总里程(km)</span>
      </div>
      <div class="stat-item" v-if="showVehicleAnimation">
        <span class="stat-value">{{ animatedVehicles }}</span>
        <span class="stat-label">运输车辆</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import 'echarts-gl'
import { getNodes, getRoutes } from '@/api/nodes'
import { ElMessage } from 'element-plus'

// 图表引用
const earthChart = ref(null)
let chartInstance = null

// 控制状态
const autoRotate = ref(true)
const showTracks = ref(true)
const selectedNode = ref(null)

// 车辆动画状态
const showVehicleAnimation = ref(false)
const animationSpeed = ref(3)
const animatedVehicles = ref(0)
const currentVehicleInfo = ref(null)

// 车辆数据
const vehicleRoutes = ref([])
const vehiclePositions = ref([])
let animationFrameId = null
let lastAnimationTime = 0

// 统计数据
const animatedStats = reactive({
  nodes: 0,
  tracks: 0,
  distance: 0
})

// 节点数据
const nodesData = ref([])
const tracksData = ref([])

// 创建网格纹理
const createGridTexture = () => {
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = 256
  const ctx = canvas.getContext('2d')
  
  // 背景
  ctx.fillStyle = '#0a1628'
  ctx.fillRect(0, 0, 512, 256)
  
  // 绘制经纬网格
  ctx.strokeStyle = 'rgba(0, 212, 255, 0.15)'
  ctx.lineWidth = 0.5
  
  // 经线
  for (let i = 0; i <= 36; i++) {
    ctx.beginPath()
    ctx.moveTo(i * (512 / 36), 0)
    ctx.lineTo(i * (512 / 36), 256)
    ctx.stroke()
  }
  
  // 纬线
  for (let i = 0; i <= 18; i++) {
    ctx.beginPath()
    ctx.moveTo(0, i * (256 / 18))
    ctx.lineTo(512, i * (256 / 18))
    ctx.stroke()
  }
  
  // 中国区域高亮
  ctx.fillStyle = 'rgba(0, 212, 255, 0.1)'
  ctx.beginPath()
  ctx.ellipse(380, 100, 50, 35, 0, 0, Math.PI * 2)
  ctx.fill()
  ctx.strokeStyle = 'rgba(0, 212, 255, 0.3)'
  ctx.lineWidth = 1
  ctx.stroke()
  
  return canvas
}

// 初始化地球
const initEarth = async () => {
  chartInstance = echarts.init(earthChart.value)
  
  // 加载数据
  await loadData()
  
  // 初始化车辆路线
  initVehicleRoutes()
  
  // 更新图表
  updateChart()
  
  // 点击事件
  chartInstance.on('click', (params) => {
    if (params.seriesType === 'scatter3D' && !showVehicleAnimation.value) {
      selectedNode.value = nodesData.value.find(n => n.name === params.name)
    }
  })
  
  // 动画数字
  animateStats()
}

// 初始化车辆路线
const initVehicleRoutes = () => {
  if (tracksData.value.length === 0) return
  
  // 选择几条主要路线作为车辆动画
  const routeCount = Math.min(5, tracksData.value.length)
  vehicleRoutes.value = tracksData.value.slice(0, routeCount).map((track, index) => ({
    id: index,
    from: track.from,
    to: track.to,
    progress: Math.random(), // 初始进度随机
    speed: 0.3 + Math.random() * 0.4, // 不同车辆速度不同
    fromNode: nodesData.value.find(n => 
      Math.abs(n.lng - track.from?.lng) < 1 && Math.abs(n.lat - track.from?.lat) < 1
    ),
    toNode: nodesData.value.find(n => 
      Math.abs(n.lng - track.to?.lng) < 1 && Math.abs(n.lat - track.to?.lat) < 1
    )
  }))
  
  animatedVehicles.value = vehicleRoutes.value.length
}

// 更新图表
const updateChart = () => {
  if (!chartInstance) return
  
  // 构建散点数据
  const scatterData = buildScatterData()
  
  // 构建轨迹数据
  const linesData = buildLinesData()
  
  // 构建车辆数据
  const vehicleData = buildVehicleData()
  
  const option = {
    backgroundColor: 'transparent',
    globe: {
      baseColor: '#0a1628',
      shading: 'color',
      environment: 'auto',
      light: {
        ambient: { intensity: 0.6 },
        main: { intensity: 1.2 }
      },
      viewControl: {
        autoRotate: autoRotate.value && !showVehicleAnimation.value,
        autoRotateSpeed: 3,
        autoRotateAfterStill: 3,
        distance: 180,
        alpha: 30,
        beta: 0,
        minDistance: 100,
        maxDistance: 400,
        targetCoord: [104, 35]
      },
      atmosphere: {
        show: true,
        offset: 5,
        color: '#00d4ff'
      },
      globeRadius: 100,
      layers: [{
        type: 'blend',
        blendTo: 'emission',
        texture: createGridTexture()
      }]
    },
    series: [
      // 节点散点
      {
        type: 'scatter3D',
        coordinateSystem: 'globe',
        blendMode: 'lighter',
        symbolSize: (val) => Math.max(val[2] / 3, 8),
        itemStyle: {
          color: (params) => {
            const colors = {
              'warehouse': '#00d4ff',
              'station': '#00ff88',
              'customer': '#ff6b6b'
            }
            return colors[params.data.type] || '#00d4ff'
          },
          opacity: 0.9
        },
        label: {
          show: false,
          formatter: '{b}',
          position: 'top',
          color: '#fff',
          fontSize: 12
        },
        emphasis: {
          label: { show: true }
        },
        data: scatterData
      },
      // 运输轨迹
      {
        type: 'lines3D',
        coordinateSystem: 'globe',
        show: showTracks.value,
        blendMode: 'lighter',
        effect: {
          show: true,
          period: 4,
          trailLength: 0.15,
          trailWidth: 2,
          trailColor: '#00ff88'
        },
        lineStyle: {
          width: 2,
          color: 'rgb(0, 212, 255)',
          opacity: 0.4
        },
        data: linesData
      },
      // 发光效果层
      {
        type: 'scatter3D',
        coordinateSystem: 'globe',
        blendMode: 'lighter',
        symbolSize: (val) => Math.max(val[2] / 2, 12),
        itemStyle: {
          color: 'rgba(0, 212, 255, 0.3)',
          opacity: 0.3
        },
        data: scatterData.map(d => ({ ...d, value: [...d.value] }))
      },
      // 车辆层（仅在动画开启时显示）
      ...(showVehicleAnimation.value && vehicleData.length > 0 ? [
        {
          type: 'scatter3D',
          coordinateSystem: 'globe',
          symbol: 'circle',
          symbolSize: 15,
          itemStyle: {
            color: '#ffcc00',
            opacity: 1,
            borderWidth: 2,
            borderColor: '#fff'
          },
          data: vehicleData
        },
        // 车辆发光
        {
          type: 'scatter3D',
          coordinateSystem: 'globe',
          symbol: 'circle',
          symbolSize: 25,
          itemStyle: {
            color: 'rgba(255, 204, 0, 0.4)',
            opacity: 0.6
          },
          data: vehicleData
        }
      ] : [])
    ]
  }
  
  chartInstance.setOption(option)
}

// 构建车辆数据
const buildVehicleData = () => {
  return vehiclePositions.value.map(pos => [pos.lng, pos.lat, 20])
}

// 加载数据
const loadData = async () => {
  try {
    nodesData.value = generateMockNodes()
    tracksData.value = generateMockRoutes()
    
    const [nodesRes, routesRes] = await Promise.all([
      getNodes().catch(() => null),
      getRoutes().catch(() => null)
    ])
    
    if (nodesRes?.nodes?.length > 0) {
      nodesData.value = nodesRes.nodes
    }
    if (routesRes?.routes?.length > 0) {
      tracksData.value = routesRes.routes
    }
  } catch (e) {
    console.error('加载数据失败', e)
    nodesData.value = generateMockNodes()
    tracksData.value = generateMockRoutes()
  }
}

// 生成模拟节点
const generateMockNodes = () => [
  { name: '北京总部', lng: 116.46, lat: 39.92, type: 'warehouse', orders: 156, vehicles: 12, status: '正常' },
  { name: '上海仓库', lng: 121.48, lat: 31.22, type: 'warehouse', orders: 189, vehicles: 15, status: '正常' },
  { name: '广州配送中心', lng: 113.23, lat: 23.16, type: 'station', orders: 98, vehicles: 8, status: '繁忙' },
  { name: '深圳站点', lng: 114.07, lat: 22.62, type: 'station', orders: 67, vehicles: 5, status: '正常' },
  { name: '杭州中心', lng: 120.19, lat: 30.26, type: 'station', orders: 112, vehicles: 9, status: '正常' },
  { name: '南京仓库', lng: 118.78, lat: 32.04, type: 'warehouse', orders: 134, vehicles: 11, status: '正常' },
  { name: '成都站点', lng: 104.06, lat: 30.67, type: 'station', orders: 78, vehicles: 6, status: '维护中' },
  { name: '武汉中心', lng: 114.31, lat: 30.52, type: 'station', orders: 89, vehicles: 7, status: '正常' },
  { name: '西安仓库', lng: 108.95, lat: 34.27, type: 'warehouse', orders: 56, vehicles: 4, status: '正常' },
  { name: '重庆配送', lng: 106.55, lat: 29.56, type: 'station', orders: 71, vehicles: 5, status: '正常' },
  { name: '天津站点', lng: 117.20, lat: 39.13, type: 'station', orders: 45, vehicles: 3, status: '正常' },
  { name: '苏州中心', lng: 120.62, lat: 31.32, type: 'customer', orders: 23, vehicles: 0, status: '正常' },
  { name: '青岛仓库', lng: 120.38, lat: 36.07, type: 'warehouse', orders: 87, vehicles: 6, status: '正常' },
  { name: '厦门站点', lng: 118.10, lat: 24.46, type: 'station', orders: 34, vehicles: 3, status: '正常' },
  { name: '长沙中心', lng: 112.94, lat: 28.23, type: 'station', orders: 52, vehicles: 4, status: '正常' },
  { name: '郑州仓库', lng: 113.65, lat: 34.76, type: 'warehouse', orders: 63, vehicles: 5, status: '正常' },
  { name: '沈阳站点', lng: 123.38, lat: 41.80, type: 'station', orders: 41, vehicles: 3, status: '正常' },
  { name: '哈尔滨仓库', lng: 126.63, lat: 45.75, type: 'warehouse', orders: 38, vehicles: 3, status: '正常' },
  { name: '昆明中心', lng: 102.73, lat: 25.04, type: 'station', orders: 29, vehicles: 2, status: '正常' },
  { name: '乌鲁木齐', lng: 87.62, lat: 43.83, type: 'station', orders: 15, vehicles: 1, status: '正常' }
]

// 生成模拟路线
const generateMockRoutes = () => {
  const routes = []
  const nodes = nodesData.value.length > 0 ? nodesData.value : generateMockNodes()
  
  const mainLines = [
    [0, 1], [0, 2], [1, 2], [1, 4], [2, 3],
    [5, 0], [5, 7], [6, 9], [8, 0], [10, 0],
    [12, 1], [12, 4], [13, 2], [14, 7], [15, 7],
    [16, 0], [17, 16], [18, 6], [19, 8]
  ]
  
  mainLines.forEach(([from, to]) => {
    if (nodes[from] && nodes[to]) {
      routes.push({
        from: { lng: nodes[from].lng, lat: nodes[from].lat },
        to: { lng: nodes[to].lng, lat: nodes[to].lat }
      })
    }
  })
  
  return routes
}

// 构建散点数据
const buildScatterData = () => {
  return nodesData.value.map(node => ({
    name: node.name,
    value: [node.lng, node.lat, node.orders || 10],
    type: node.type
  }))
}

// 构建轨迹数据
const buildLinesData = () => {
  if (!tracksData.value || tracksData.value.length === 0) return []
  return tracksData.value.map(track => ({
    coords: [
      [track.from?.lng || 0, track.from?.lat || 0],
      [track.to?.lng || 0, track.to?.lat || 0]
    ]
  })).filter(track => track.coords[0][0] !== 0 && track.coords[1][0] !== 0)
}

// 动画数字
const animateStats = () => {
  const targetNodes = nodesData.value.length
  const targetTracks = tracksData.value.length
  const targetDistance = Math.round(tracksData.value.length * 850)
  
  animateValue('nodes', targetNodes)
  animateValue('tracks', targetTracks)
  animateValue('distance', targetDistance)
}

const animateValue = (key, target) => {
  const duration = 2000
  const start = animatedStats[key]
  const increment = (target - start) / (duration / 16)
  let current = start
  
  const timer = setInterval(() => {
    current += increment
    if ((increment > 0 && current >= target) || (increment < 0 && current <= target)) {
      animatedStats[key] = target
      clearInterval(timer)
    } else {
      animatedStats[key] = Math.round(current)
    }
  }, 16)
}

// 控制方法
const toggleAutoRotate = () => {
  updateChart()
}

const toggleVehicleAnimation = () => {
  if (showVehicleAnimation.value) {
    startVehicleAnimation()
  } else {
    stopVehicleAnimation()
  }
  updateChart()
}

// 车辆动画
const startVehicleAnimation = () => {
  lastAnimationTime = performance.now()
  animateVehicles()
}

const stopVehicleAnimation = () => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
  vehiclePositions.value = []
  currentVehicleInfo.value = null
}

const animateVehicles = () => {
  const now = performance.now()
  const delta = (now - lastAnimationTime) / 1000
  lastAnimationTime = now
  
  // 更新每个车辆的位置
  vehiclePositions.value = vehicleRoutes.value.map(route => {
    // 更新进度
    route.progress += route.speed * delta * animationSpeed.value * 0.01
    
    // 循环
    if (route.progress > 1) {
      route.progress = 0
    }
    
    // 插值计算位置
    const lng = route.from.lng + (route.to.lng - route.from.lng) * route.progress
    const lat = route.from.lat + (route.to.lat - route.from.lat) * route.progress
    
    return { lng, lat, route }
  })
  
  // 更新当前车辆信息
  if (vehicleRoutes.value.length > 0) {
    const firstRoute = vehicleRoutes.value[0]
    currentVehicleInfo.value = {
      route: `${firstRoute.fromNode?.name || '起点'} → ${firstRoute.toNode?.name || '终点'}`,
      progress: Math.round(firstRoute.progress * 100)
    }
  }
  
  // 更新图表
  updateChart()
  
  // 继续动画
  if (showVehicleAnimation.value) {
    animationFrameId = requestAnimationFrame(animateVehicles)
  }
}

// 辅助方法
const getNodeIcon = (type) => ({
  'warehouse': '🏭',
  'station': '🚛',
  'customer': '📍'
}[type] || '📍')

const getStatusType = (status) => ({
  '正常': 'success',
  '繁忙': 'warning',
  '维护中': 'danger'
}[status] || 'info')

// 窗口大小变化
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

onMounted(() => {
  initEarth()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  stopVehicleAnimation()
  if (chartInstance) {
    chartInstance.dispose()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.earth-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 500px;
}

.earth-chart {
  width: 100%;
  height: 100%;
  min-height: 500px;
}

/* 控制面板 */
.control-panel {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 12px 16px;
  background: rgba(10, 14, 39, 0.85);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 10px;
  backdrop-filter: blur(10px);
  z-index: 10;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #00d4ff;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
}

.control-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.control-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

/* 图例 */
.legend-panel {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 12px 16px;
  background: rgba(10, 14, 39, 0.85);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 10px;
  backdrop-filter: blur(10px);
  z-index: 10;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.legend-item:last-child {
  margin-bottom: 0;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-dot.warehouse {
  background: #00d4ff;
  box-shadow: 0 0 8px rgba(0, 212, 255, 0.5);
}

.legend-dot.station {
  background: #00ff88;
  box-shadow: 0 0 8px rgba(0, 255, 136, 0.5);
}

.legend-dot.customer {
  background: #ff6b6b;
  box-shadow: 0 0 8px rgba(255, 107, 107, 0.5);
}

.legend-dot.vehicle {
  background: #ffcc00;
  box-shadow: 0 0 8px rgba(255, 204, 0, 0.5);
}

.legend-line {
  width: 20px;
  height: 2px;
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.8), rgba(0, 255, 136, 0.8));
}

.legend-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

/* 信息卡片 */
.info-card,
.vehicle-info-card {
  position: absolute;
  bottom: 80px;
  left: 12px;
  width: 220px;
  padding: 16px;
  background: rgba(10, 14, 39, 0.9);
  border: 1px solid rgba(0, 212, 255, 0.4);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  z-index: 10;
}

.vehicle-info-card {
  bottom: 80px;
  left: auto;
  right: 12px;
  border-color: rgba(255, 204, 0, 0.4);
}

.info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
}

.info-icon {
  font-size: 20px;
}

.info-name {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.info-label {
  color: rgba(255, 255, 255, 0.5);
}

.info-value {
  color: #fff;
  font-weight: 500;
}

.info-value.highlight {
  color: #00ff88;
  font-weight: 600;
}

/* 统计面板 */
.stats-panel {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 24px;
  padding: 12px 24px;
  background: rgba(10, 14, 39, 0.85);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 30px;
  backdrop-filter: blur(10px);
  z-index: 10;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #00d4ff;
  text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
}

.stat-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 4px;
}

/* 动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* Element Plus 覆盖 */
:deep(.el-switch.is-checked .el-switch__core) {
  background-color: #00d4ff;
  border-color: #00d4ff;
}

:deep(.el-slider__bar) {
  background-color: #00d4ff;
}

:deep(.el-slider__button) {
  border-color: #00d4ff;
}
</style>
