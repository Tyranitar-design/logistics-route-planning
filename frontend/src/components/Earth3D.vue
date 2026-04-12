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
        <span class="control-label">轨迹飞线</span>
        <el-switch v-model="showFlyLines" @change="updateChart" />
      </div>
      <div class="control-item">
        <span class="control-label">粒子特效</span>
        <el-switch v-model="showParticles" @change="updateChart" />
      </div>
      <div class="control-item">
        <span class="control-label">🌟 节点脉冲</span>
        <el-switch v-model="showPulse" @change="updateChart" />
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
      <div class="legend-item" v-if="showFlyLines">
        <span class="legend-line flyline"></span>
        <span class="legend-text">飞线轨迹</span>
      </div>
      <div class="legend-item" v-if="showParticles">
        <span class="legend-dot particle"></span>
        <span class="legend-text">粒子云</span>
      </div>
    </div>
    
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
          <div class="info-row" v-if="selectedNode.capacity">
            <span class="info-label">📊 容量:</span>
            <span class="info-value">{{ selectedNode.capacity }}%</span>
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
      <div class="stat-item" v-if="showFlyLines">
        <span class="stat-value">{{ animatedStats.routes }}</span>
        <span class="stat-label">运输线路</span>
      </div>
      <div class="stat-item" v-if="showParticles">
        <span class="stat-value">{{ particleCount.toLocaleString() }}</span>
        <span class="stat-label">粒子数量</span>
      </div>
      <div class="stat-item" v-if="showVehicleAnimation">
        <span class="stat-value">{{ animatedVehicles }}</span>
        <span class="stat-label">运输车辆</span>
      </div>
    </div>
    
    <!-- 时间戳 -->
    <div class="time-panel">
      <span class="time-icon">⏰</span>
      <span class="time-text">{{ currentTime }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import 'echarts-gl'

// 图表引用
const earthChart = ref(null)
let chartInstance = null
let animationFrameId = null
let pulseAnimationId = null

// 控制状态
const autoRotate = ref(true)
const showFlyLines = ref(true)
const showParticles = ref(true)
const showPulse = ref(true)
const selectedNode = ref(null)

// 车辆动画状态
const showVehicleAnimation = ref(false)
const animationSpeed = ref(3)
const animatedVehicles = ref(0)
const vehicleRoutes = ref([])
const vehiclePositions = ref([])

// 粒子系统
const particleCount = ref(3000)
const particlesData = ref([])

// 时间显示
const currentTime = ref('')

// 统计数据
const animatedStats = reactive({
  nodes: 0,
  routes: 0
})

// 节点数据
const nodesData = ref([])
const tracksData = ref([])

// ==================== 纹理创建 ====================

// 创建发光纹理
const createGlowTexture = (color = '#00d4ff') => {
  const canvas = document.createElement('canvas')
  canvas.width = 256
  canvas.height = 256
  const ctx = canvas.getContext('2d')
  
  const gradient = ctx.createRadialGradient(128, 128, 0, 128, 128, 128)
  gradient.addColorStop(0, color)
  gradient.addColorStop(0.3, color.replace(')', ', 0.6)').replace('rgb', 'rgba'))
  gradient.addColorStop(0.6, 'rgba(0, 212, 255, 0.2)')
  gradient.addColorStop(1, 'rgba(0, 212, 255, 0)')
  
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, 256, 256)
  
  return canvas
}

// 创建网格纹理
const createGridTexture = () => {
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = 256
  const ctx = canvas.getContext('2d')
  
  // 深色背景
  ctx.fillStyle = '#0a1628'
  ctx.fillRect(0, 0, 512, 256)
  
  // 绘制经纬网格
  ctx.strokeStyle = 'rgba(0, 212, 255, 0.12)'
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
  ctx.fillStyle = 'rgba(0, 212, 255, 0.08)'
  ctx.beginPath()
  ctx.ellipse(380, 100, 55, 40, 0, 0, Math.PI * 2)
  ctx.fill()
  ctx.strokeStyle = 'rgba(0, 212, 255, 0.25)'
  ctx.lineWidth = 1
  ctx.stroke()
  
  return canvas
}

// 创建粒子纹理
const createParticleTexture = () => {
  const canvas = document.createElement('canvas')
  canvas.width = 64
  canvas.height = 64
  const ctx = canvas.getContext('2d')
  
  const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32)
  gradient.addColorStop(0, 'rgba(255, 255, 255, 1)')
  gradient.addColorStop(0.2, 'rgba(255, 255, 255, 0.8)')
  gradient.addColorStop(0.5, 'rgba(0, 212, 255, 0.4)')
  gradient.addColorStop(1, 'rgba(0, 212, 255, 0)')
  
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, 64, 64)
  
  return canvas
}

// ==================== 初始化 ====================

const initEarth = async () => {
  chartInstance = echarts.init(earthChart.value)
  
  // 加载数据
  await loadData()
  
  // 生成粒子数据
  generateParticles()
  
  // 初始化车辆路线
  initVehicleRoutes()
  
  // 更新时间
  updateTime()
  setInterval(updateTime, 1000)
  
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
  
  // 脉冲动画
  if (showPulse.value) {
    startPulseAnimation()
  }
}

// ==================== 数据 ====================

const loadData = async () => {
  try {
    nodesData.value = generateMockNodes()
    tracksData.value = generateMockRoutes()
  } catch (e) {
    console.error('加载数据失败', e)
    nodesData.value = generateMockNodes()
    tracksData.value = generateMockRoutes()
  }
}

// 生成模拟节点
const generateMockNodes = () => [
  { name: '北京总部', lng: 116.46, lat: 39.92, type: 'warehouse', orders: 156, vehicles: 12, status: '正常', capacity: 78 },
  { name: '上海仓库', lng: 121.48, lat: 31.22, type: 'warehouse', orders: 189, vehicles: 15, status: '正常', capacity: 85 },
  { name: '广州配送中心', lng: 113.23, lat: 23.16, type: 'station', orders: 98, vehicles: 8, status: '繁忙', capacity: 92 },
  { name: '深圳站点', lng: 114.07, lat: 22.62, type: 'station', orders: 67, vehicles: 5, status: '正常', capacity: 65 },
  { name: '杭州中心', lng: 120.19, lat: 30.26, type: 'station', orders: 112, vehicles: 9, status: '正常', capacity: 71 },
  { name: '南京仓库', lng: 118.78, lat: 32.04, type: 'warehouse', orders: 134, vehicles: 11, status: '正常', capacity: 68 },
  { name: '成都站点', lng: 104.06, lat: 30.67, type: 'station', orders: 78, vehicles: 6, status: '维护中', capacity: 45 },
  { name: '武汉中心', lng: 114.31, lat: 30.52, type: 'station', orders: 89, vehicles: 7, status: '正常', capacity: 72 },
  { name: '西安仓库', lng: 108.95, lat: 34.27, type: 'warehouse', orders: 56, vehicles: 4, status: '正常', capacity: 55 },
  { name: '重庆配送', lng: 106.55, lat: 29.56, type: 'station', orders: 71, vehicles: 5, status: '正常', capacity: 63 },
  { name: '天津站点', lng: 117.20, lat: 39.13, type: 'station', orders: 45, vehicles: 3, status: '正常', capacity: 48 },
  { name: '苏州中心', lng: 120.62, lat: 31.32, type: 'customer', orders: 23, vehicles: 0, status: '正常', capacity: 30 },
  { name: '青岛仓库', lng: 120.38, lat: 36.07, type: 'warehouse', orders: 87, vehicles: 6, status: '正常', capacity: 61 },
  { name: '厦门站点', lng: 118.10, lat: 24.46, type: 'station', orders: 34, vehicles: 3, status: '正常', capacity: 42 },
  { name: '长沙中心', lng: 112.94, lat: 28.23, type: 'station', orders: 52, vehicles: 4, status: '正常', capacity: 58 },
  { name: '郑州仓库', lng: 113.65, lat: 34.76, type: 'warehouse', orders: 63, vehicles: 5, status: '正常', capacity: 54 },
  { name: '沈阳站点', lng: 123.38, lat: 41.80, type: 'station', orders: 41, vehicles: 3, status: '正常', capacity: 47 },
  { name: '哈尔滨', lng: 126.63, lat: 45.75, type: 'warehouse', orders: 38, vehicles: 3, status: '正常', capacity: 40 },
  { name: '昆明中心', lng: 102.73, lat: 25.04, type: 'station', orders: 29, vehicles: 2, status: '正常', capacity: 35 },
  { name: '乌鲁木齐', lng: 87.62, lat: 43.83, type: 'station', orders: 15, vehicles: 1, status: '正常', capacity: 25 },
  { name: '福州站点', lng: 119.30, lat: 26.08, type: 'station', orders: 31, vehicles: 2, status: '正常', capacity: 38 },
  { name: '济南仓库', lng: 116.99, lat: 36.67, type: 'warehouse', orders: 49, vehicles: 4, status: '正常', capacity: 52 },
  { name: '太原中心', lng: 112.55, lat: 37.87, type: 'station', orders: 33, vehicles: 2, status: '正常', capacity: 41 },
  { name: '南宁站点', lng: 108.33, lat: 22.84, type: 'station', orders: 27, vehicles: 2, status: '正常', capacity: 33 },
  { name: '贵阳仓库', lng: 106.71, lat: 26.60, type: 'warehouse', orders: 35, vehicles: 3, status: '正常', capacity: 44 },
  { name: '拉萨中心', lng: 91.12, lat: 29.65, type: 'station', orders: 8, vehicles: 1, status: '正常', capacity: 15 },
  { name: '兰州站点', lng: 103.83, lat: 36.06, type: 'station', orders: 22, vehicles: 2, status: '正常', capacity: 28 },
  { name: '海口网点', lng: 110.35, lat: 20.02, type: 'customer', orders: 12, vehicles: 0, status: '正常', capacity: 20 },
  { name: '石家庄', lng: 114.48, lat: 38.03, type: 'warehouse', orders: 44, vehicles: 3, status: '正常', capacity: 49 },
  { name: '长春仓库', lng: 125.32, lat: 43.82, type: 'warehouse', orders: 36, vehicles: 3, status: '正常', capacity: 43 }
]

// 生成模拟路线
const generateMockRoutes = () => {
  const routes = []
  const mainLines = [
    [0, 1], [0, 2], [0, 3], [1, 4], [1, 11],
    [2, 3], [3, 13], [4, 11], [5, 0], [5, 7],
    [6, 9], [7, 14], [8, 0], [9, 18], [10, 0],
    [12, 1], [12, 4], [13, 2], [14, 7], [15, 7],
    [16, 0], [17, 16], [18, 6], [19, 8], [20, 13],
    [21, 10], [22, 8], [23, 2], [24, 6], [25, 19],
    [26, 8], [27, 2], [28, 10], [29, 17]
  ]
  
  mainLines.forEach(([from, to]) => {
    if (nodesData.value[from] && nodesData.value[to]) {
      routes.push({
        from: { lng: nodesData.value[from].lng, lat: nodesData.value[from].lat },
        to: { lng: nodesData.value[to].lng, lat: nodesData.value[to].lat }
      })
    }
  })
  
  return routes
}

// 生成粒子数据
const generateParticles = () => {
  const particles = []
  for (let i = 0; i < particleCount.value; i++) {
    // 随机球面坐标
    const phi = Math.random() * Math.PI * 2
    const theta = Math.random() * Math.PI
    const r = 100 + Math.random() * 5
    
    const x = r * Math.sin(theta) * Math.cos(phi)
    const y = r * Math.cos(theta)
    const z = r * Math.sin(theta) * Math.sin(phi)
    
    particles.push([x, y, z, Math.random() * 0.5 + 0.5])
  }
  particlesData.value = particles
}

// 初始化车辆路线
const initVehicleRoutes = () => {
  if (tracksData.value.length === 0) return
  
  const routeCount = Math.min(8, tracksData.value.length)
  vehicleRoutes.value = tracksData.value.slice(0, routeCount).map((track, index) => ({
    id: index,
    from: track.from,
    to: track.to,
    progress: Math.random(),
    speed: 0.2 + Math.random() * 0.3
  }))
  
  animatedVehicles.value = vehicleRoutes.value.length
}

// ==================== 图表更新 ====================

const updateChart = () => {
  if (!chartInstance) return
  
  // 停止所有动画
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
  
  const option = buildOption()
  chartInstance.setOption(option, { notMerge: true })
  
  // 如果开启脉冲，启动动画
  if (showPulse.value || showVehicleAnimation.value) {
    startAnimationLoop()
  }
}

const buildOption = () => {
  const scatterData = buildScatterData()
  const linesData = buildLinesData()
  const vehicleData = buildVehicleData()
  
  return {
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 3000,
    globe: {
      baseColor: '#0a1628',
      shading: 'color',
      environment: 'auto',
      light: {
        ambient: { intensity: 0.5 },
        main: { intensity: 1.0 }
      },
      viewControl: {
        autoRotate: autoRotate.value && !showVehicleAnimation.value,
        autoRotateSpeed: 2,
        autoRotateAfterStill: 3,
        distance: 160,
        alpha: 25,
        beta: 0,
        minDistance: 100,
        maxDistance: 350,
        targetCoord: [105, 36]
      },
      atmosphere: {
        show: true,
        offset: 8,
        color: '#00d4ff',
        glowPower: 0.3
      },
      globeRadius: 100,
      layers: [{
        type: 'blend',
        blendTo: 'emission',
        texture: createGridTexture()
      }]
    },
    series: [
      // 粒子云层（最底层）
      ...(showParticles.value ? [{
        type: 'scatter3D',
        coordinateSystem: 'globe',
        blendMode: 'lighter',
        symbol: 'circle',
        symbolSize: 3,
        itemStyle: {
          color: 'rgba(0, 212, 255, 0.15)',
          opacity: 0.4
        },
        data: particlesData.value,
        silent: true
      }] : []),
      
      // 节点脉冲光环层
      ...(showPulse.value ? [{
        type: 'scatter3D',
        coordinateSystem: 'globe',
        blendMode: 'lighter',
        symbol: 'circle',
        symbolSize: (val) => Math.max(val[2] / 1.5 + 15, 20),
        itemStyle: {
          color: (params) => {
            const colors = {
              'warehouse': 'rgba(0, 212, 255, 0.3)',
              'station': 'rgba(0, 255, 136, 0.25)',
              'customer': 'rgba(255, 107, 107, 0.2)'
            }
            return colors[params.data.type] || 'rgba(0, 212, 255, 0.3)'
          },
          opacity: 0.6
        },
        data: scatterData.map(d => ({ ...d, value: [...d.value] })),
        silent: true
      }] : []),
      
      // 主节点层
      {
        type: 'scatter3D',
        coordinateSystem: 'globe',
        blendMode: 'lighter',
        symbolSize: (val) => Math.max(val[2] / 4, 10),
        itemStyle: {
          color: (params) => {
            const colors = {
              'warehouse': '#00d4ff',
              'station': '#00ff88',
              'customer': '#ff6b6b'
            }
            return colors[params.data.type] || '#00d4ff'
          },
          opacity: 1,
          borderWidth: 2,
          borderColor: 'rgba(255, 255, 255, 0.5)'
        },
        label: {
          show: false,
          formatter: '{b}',
          position: 'top',
          color: '#fff',
          fontSize: 11,
          distance: 5
        },
        emphasis: {
          scale: 1.3,
          label: { show: true }
        },
        data: scatterData
      },
      
      // 飞线轨迹层
      ...(showFlyLines.value ? [{
        type: 'lines3D',
        coordinateSystem: 'globe',
        blendMode: 'lighter',
        effect: {
          show: true,
          period: 3,
          trailLength: 0.4,
          trailWidth: 3,
          trailColor: 'rgba(0, 255, 136, 0.8)',
          trailOpacity: 0.6
        },
        lineStyle: {
          width: 1.5,
          color: 'rgb(0, 212, 255)',
          opacity: 0.5
        },
        data: linesData
      }] : []),
      
      // 车辆动画层
      ...(showVehicleAnimation.value && vehicleData.length > 0 ? [
        {
          type: 'scatter3D',
          coordinateSystem: 'globe',
          symbol: 'circle',
          symbolSize: 18,
          itemStyle: {
            color: '#ffcc00',
            opacity: 1,
            borderWidth: 3,
            borderColor: '#fff',
            shadowBlur: 20,
            shadowColor: '#ffcc00'
          },
          data: vehicleData,
          silent: true
        },
        // 车辆光晕
        {
          type: 'scatter3D',
          coordinateSystem: 'globe',
          symbol: 'circle',
          symbolSize: 30,
          itemStyle: {
            color: 'rgba(255, 204, 0, 0.3)',
            opacity: 0.7
          },
          data: vehicleData,
          silent: true
        }
      ] : [])
    ]
  }
}

// 构建散点数据
const buildScatterData = () => {
  return nodesData.value.map(node => ({
    name: node.name,
    value: [node.lng, node.lat, node.orders || 10],
    type: node.type,
    itemStyle: {
      color: node.capacity > 80 ? '#ff6b6b' : undefined
    }
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

// 构建车辆数据
const buildVehicleData = () => {
  return vehiclePositions.value.map(pos => [pos.lng, pos.lat, 15])
}

// ==================== 动画 ====================

const startAnimationLoop = () => {
  const animate = () => {
    if (!showPulse.value && !showVehicleAnimation.value) {
      animationFrameId = null
      return
    }
    
    // 更新脉冲
    if (showPulse.value) {
      updatePulse()
    }
    
    // 更新车辆
    if (showVehicleAnimation.value) {
      updateVehicles()
    }
    
    animationFrameId = requestAnimationFrame(animate)
  }
  
  if (!animationFrameId) {
    animationFrameId = requestAnimationFrame(animate)
  }
}

let pulsePhase = 0
const updatePulse = () => {
  pulsePhase += 0.02
  
  const pulseData = nodesData.value.map(node => {
    const size = Math.max(node.orders / 4, 10)
    const scale = 1 + Math.sin(pulsePhase + node.lng) * 0.2
    return {
      name: node.name,
      value: [node.lng, node.lat, node.orders || 10, size * scale],
      type: node.type
    }
  })
  
  chartInstance.setOption({
    series: [
      { seriesIndex: showParticles.value ? 1 : 0 },
      { seriesIndex: showParticles.value ? 2 : 1 },
      { seriesIndex: showParticles.value ? 3 : 2 },
      { seriesIndex: showParticles.value ? 4 : 3 },
      {
        seriesIndex: showParticles.value ? 5 : 4,
        data: pulseData
      }
    ]
  })
}

let lastTime = 0
const updateVehicles = () => {
  const now = performance.now()
  const delta = (now - lastTime) / 1000
  lastTime = now
  
  if (delta > 100) return
  
  vehicleRoutes.value.forEach(route => {
    route.progress += route.speed * delta * animationSpeed.value * 0.008
    if (route.progress > 1) route.progress = 0
  })
  
  vehiclePositions.value = vehicleRoutes.value.map(route => {
    const lng = route.from.lng + (route.to.lng - route.from.lng) * route.progress
    const lat = route.from.lat + (route.to.lat - route.from.lat) * route.progress
    return { lng, lat }
  })
  
  const vehicleData = buildVehicleData()
  
  // 找到车辆层的索引
  let vehicleLayerIndex = 0
  if (showParticles.value) vehicleLayerIndex++
  if (showPulse.value) vehicleLayerIndex++
  vehicleLayerIndex++ // 节点层
  if (showFlyLines.value) vehicleLayerIndex++
  
  chartInstance.setOption({
    series: [
      { seriesIndex: vehicleLayerIndex, data: vehicleData },
      { seriesIndex: vehicleLayerIndex + 1, data: vehicleData }
    ]
  })
}

const startPulseAnimation = () => {
  if (pulseAnimationId) return
  pulseAnimationId = setInterval(() => {
    if (showPulse.value && chartInstance) {
      updatePulse()
    }
  }, 50)
}

// 动画数字
const animateStats = () => {
  const targetNodes = nodesData.value.length
  const targetRoutes = tracksData.value.length
  
  animateValue('nodes', targetNodes)
  animateValue('routes', targetRoutes)
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

// 更新时间的函数
const updateTime = () => {
  const now = new Date()
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  const seconds = String(now.getSeconds()).padStart(2, '0')
  currentTime.value = `${hours}:${minutes}:${seconds}`
}

// ==================== 控制方法 ====================

const toggleAutoRotate = () => {
  updateChart()
}

const toggleVehicleAnimation = () => {
  if (showVehicleAnimation.value) {
    lastTime = performance.now()
    startAnimationLoop()
  }
  updateChart()
}

// ==================== 辅助方法 ====================

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

// ==================== 生命周期 ====================

onMounted(() => {
  initEarth()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  if (pulseAnimationId) clearInterval(pulseAnimationId)
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
  min-height: 600px;
}

.earth-chart {
  width: 100%;
  height: 100%;
  min-height: 600px;
}

/* 控制面板 */
.control-panel {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 14px 18px;
  background: rgba(10, 14, 39, 0.88);
  border: 1px solid rgba(0, 212, 255, 0.35);
  border-radius: 12px;
  backdrop-filter: blur(12px);
  z-index: 10;
  min-width: 160px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #00d4ff;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
}

.control-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.control-item:last-child {
  margin-bottom: 0;
}

.control-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
}

/* 图例 */
.legend-panel {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 14px 18px;
  background: rgba(10, 14, 39, 0.88);
  border: 1px solid rgba(0, 212, 255, 0.35);
  border-radius: 12px;
  backdrop-filter: blur(12px);
  z-index: 10;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.legend-item:last-child {
  margin-bottom: 0;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  box-shadow: 0 0 8px currentColor;
}

.legend-dot.warehouse {
  background: #00d4ff;
  color: #00d4ff;
  box-shadow: 0 0 10px rgba(0, 212, 255, 0.6);
}

.legend-dot.station {
  background: #00ff88;
  color: #00ff88;
  box-shadow: 0 0 10px rgba(0, 255, 136, 0.6);
}

.legend-dot.customer {
  background: #ff6b6b;
  color: #ff6b6b;
  box-shadow: 0 0 10px rgba(255, 107, 107, 0.6);
}

.legend-dot.particle {
  background: linear-gradient(135deg, #00d4ff, #00ff88);
  animation: particleGlow 2s ease-in-out infinite;
}

.legend-line {
  width: 24px;
  height: 3px;
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.8), rgba(0, 255, 136, 0.8));
  border-radius: 2px;
  position: relative;
  overflow: hidden;
}

.legend-line::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 50%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.8), transparent);
  animation: flyline 1.5s linear infinite;
}

.legend-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
}

/* 信息卡片 */
.info-card {
  position: absolute;
  bottom: 90px;
  left: 12px;
  width: 240px;
  padding: 16px;
  background: rgba(10, 14, 39, 0.92);
  border: 1px solid rgba(0, 212, 255, 0.45);
  border-radius: 14px;
  backdrop-filter: blur(14px);
  z-index: 10;
}

.info-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
}

.info-icon {
  font-size: 22px;
}

.info-name {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
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

/* 统计面板 */
.stats-panel {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 28px;
  padding: 14px 28px;
  background: rgba(10, 14, 39, 0.88);
  border: 1px solid rgba(0, 212, 255, 0.35);
  border-radius: 35px;
  backdrop-filter: blur(12px);
  z-index: 10;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #00d4ff;
  text-shadow: 0 0 15px rgba(0, 212, 255, 0.4);
}

.stat-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 5px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 时间面板 */
.time-panel {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  background: rgba(10, 14, 39, 0.88);
  border: 1px solid rgba(0, 212, 255, 0.35);
  border-radius: 20px;
  backdrop-filter: blur(12px);
  z-index: 10;
}

.time-icon {
  font-size: 14px;
}

.time-text {
  font-size: 14px;
  font-weight: 600;
  color: #00d4ff;
  font-family: 'Monaco', 'Consolas', monospace;
  letter-spacing: 1px;
}

/* 动画 */
@keyframes particleGlow {
  0%, 100% { opacity: 0.6; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
}

@keyframes flyline {
  0% { left: -100%; }
  100% { left: 200%; }
}

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

:deep(.el-tag--success) {
  background-color: rgba(0, 255, 136, 0.2);
  border-color: rgba(0, 255, 136, 0.4);
  color: #00ff88;
}

:deep(.el-tag--warning) {
  background-color: rgba(255, 170, 0, 0.2);
  border-color: rgba(255, 170, 0, 0.4);
  color: #ffaa00;
}

:deep(.el-tag--danger) {
  background-color: rgba(255, 107, 107, 0.2);
  border-color: rgba(255, 107, 107, 0.4);
  color: #ff6b6b;
}
</style>
