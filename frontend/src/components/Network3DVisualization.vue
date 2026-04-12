<template>
  <div class="network-3d-container">
    <!-- 3D 场景容器 -->
    <div ref="containerRef" class="scene-container"></div>
    
    <!-- 加载提示 -->
    <div class="loading-overlay" v-if="loading">
      <el-icon class="is-loading" :size="40"><Loading /></el-icon>
      <p>加载中国3D地图中...</p>
    </div>
    
    <!-- 标题 -->
    <div class="title-panel">
      <span class="title-icon">🗺️</span>
      <span class="title-text">物流网络3D地图</span>
    </div>
    
    <!-- 控制面板 -->
    <div class="control-panel">
      <el-card class="control-card">
        <template #header>
          <span>🎮 3D 控制</span>
        </template>
        
        <el-form label-width="70px" size="small">
          <el-form-item label="自动旋转">
            <el-switch v-model="autoRotate" />
          </el-form-item>
          <el-form-item label="地图效果">
            <el-switch v-model="showMapEffect" />
          </el-form-item>
          <el-form-item label="设施节点">
            <el-switch v-model="showFacilities" />
          </el-form-item>
          <el-form-item label="物流连线">
            <el-switch v-model="showConnections" />
          </el-form-item>
          <el-form-item label="飞线动画">
            <el-switch v-model="showFlyLines" />
          </el-form-item>
        </el-form>
        
        <el-divider />
        
        <div class="legend">
          <div class="legend-item">
            <span class="dot warehouse"></span> 仓库/工厂
          </div>
          <div class="legend-item">
            <span class="dot station"></span> 配送站
          </div>
          <div class="legend-item">
            <span class="dot customer"></span> 客户
          </div>
          <div class="legend-item">
            <span class="dot selected"></span> 已选设施
          </div>
          <div class="legend-item">
            <span class="line-connection"></span> 物流连线
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 统计信息 -->
    <div class="stats-panel" v-if="stats">
      <div class="stat-item">
        <span class="stat-value">{{ stats.nodes }}</span>
        <span class="stat-label">节点</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ stats.connections }}</span>
        <span class="stat-label">连线</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ stats.coverage }}%</span>
        <span class="stat-label">覆盖率</span>
      </div>
    </div>
    
    <!-- 节点信息卡片 -->
    <transition name="fade">
      <div v-if="selectedNode" class="node-info-card">
        <div class="card-header">
          <span class="node-icon">{{ getNodeIcon(selectedNode.type) }}</span>
          <span class="node-name">{{ selectedNode.name }}</span>
          <el-tag size="small" :type="selectedNode.isSelected ? 'danger' : 'success'">
            {{ selectedNode.isSelected ? '已选中' : '候选' }}
          </el-tag>
        </div>
        <div class="card-content">
          <div class="info-row">
            <span class="label">类型</span>
            <span class="value">{{ getTypeName(selectedNode.type) }}</span>
          </div>
          <div class="info-row" v-if="selectedNode.lon">
            <span class="label">坐标</span>
            <span class="value">{{ selectedNode.lon?.toFixed(2) }}, {{ selectedNode.lat?.toFixed(2) }}</span>
          </div>
          <div class="info-row" v-if="selectedNode.capacity">
            <span class="label">容量</span>
            <span class="value">{{ selectedNode.capacity }}%</span>
          </div>
          <div class="info-row" v-if="selectedNode.demand">
            <span class="label">需求</span>
            <span class="value">{{ selectedNode.demand }}</span>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js'
import { Loading } from '@element-plus/icons-vue'

// Props
const props = defineProps({
  customers: { type: Array, default: () => [] },
  candidates: { type: Array, default: () => [] },
  selectedFacilities: { type: Array, default: () => [] },
  assignments: { type: Object, default: () => ({}) }
})

// Emits
const emit = defineEmits(['node-click'])

// Refs
const containerRef = ref(null)
const isInitialized = ref(false)
const autoRotate = ref(true)
const showMapEffect = ref(true)
const showFacilities = ref(true)
const showConnections = ref(true)
const showFlyLines = ref(true)
const stats = ref(null)
const loading = ref(true)
const selectedNode = ref(null)

// Three.js 对象
let scene, camera, renderer, controls, labelRenderer
let nodeGroup, connectionGroup, flyLineGroup
let animationId
let nodeObjects = []
let connectionObjects = []
let flyLineObjects = []

// 地图配置
const MAP_CONFIG = {
  // 阿里云 DataV 官方中国地图数据（包含所有省份 + 南海诸岛）
  // 数据来源：https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json
  mapDataUrl: 'https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json',
}

// 中国区域经纬度边界（包含南海诸岛）
// 最东: 135°E (黑龙江抚远)
// 最西: 73°E (新疆帕米尔)
// 最南: 8°N (曾母暗礁) - 包含南海诸岛
// 最北: 54°N (黑龙江漠河)
const BOUNDS = {
  minLon: 73,
  maxLon: 135,
  minLat: 8,   // 从 18 降到 8，包含南海
  maxLat: 54
}

// 场景尺寸
const SCENE_SIZE = 500

// ==================== 初始化 ====================

const initScene = async () => {
  if (!containerRef.value) return
  loading.value = true
  
  // 创建场景
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a1628)
  scene.fog = new THREE.FogExp2(0x0a1628, 0.0008)
  
  // 创建相机
  const width = containerRef.value.clientWidth
  const height = containerRef.value.clientHeight
  
  camera = new THREE.PerspectiveCamera(45, width / height, 1, 10000)
  camera.position.set(0, 300, 400)
  camera.lookAt(0, 0, 0)
  
  // 创建渲染器
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.2
  containerRef.value.appendChild(renderer.domElement)
  
  // 创建CSS2D渲染器（用于标签）
  labelRenderer = new CSS2DRenderer()
  labelRenderer.setSize(width, height)
  labelRenderer.domElement.style.position = 'absolute'
  labelRenderer.domElement.style.top = '0'
  labelRenderer.domElement.style.pointerEvents = 'none'
  containerRef.value.appendChild(labelRenderer.domElement)
  
  // 创建控制器
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.autoRotate = autoRotate.value
  controls.autoRotateSpeed = 0.5
  controls.minDistance = 100
  controls.maxDistance = 800
  controls.maxPolarAngle = Math.PI / 2.2
  
  // 创建组
  nodeGroup = new THREE.Group()
  connectionGroup = new THREE.Group()
  flyLineGroup = new THREE.Group()
  scene.add(nodeGroup)
  scene.add(connectionGroup)
  scene.add(flyLineGroup)
  
  // 添加光照
  setupLights()
  
  // 添加地图
  await setupMap()
  
  // 创建节点
  updateNodes()
  
  // 更新统计
  updateStats()
  
  loading.value = false
  isInitialized.value = true
  
  // 初始化完成后更新节点和连线
  updateNodes()
  updateConnections()
  
  // 开始动画
  animate()
}

// 设置光照
const setupLights = () => {
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
  scene.add(ambientLight)
  
  const mainLight = new THREE.DirectionalLight(0xffffff, 0.8)
  mainLight.position.set(100, 200, 100)
  scene.add(mainLight)
  
  const fillLight = new THREE.DirectionalLight(0x4488ff, 0.3)
  fillLight.position.set(-100, 100, -100)
  scene.add(fillLight)
}

// ==================== 地图 ====================

const setupMap = async () => {
  try {
    createGroundGrid()
    const mapData = await loadMapData()
    if (mapData) {
      createProvinceOutlines(mapData)
    }
    if (showMapEffect.value) {
      createMapGlowEffect()
    }
  } catch (error) {
    console.error('加载地图失败:', error)
    createGroundGrid()
  }
}

const createGroundGrid = () => {
  const groundGeo = new THREE.PlaneGeometry(SCENE_SIZE * 2, SCENE_SIZE * 2)
  const groundMat = new THREE.MeshBasicMaterial({
    color: 0x0a1628,
    transparent: true,
    opacity: 0.9
  })
  const ground = new THREE.Mesh(groundGeo, groundMat)
  ground.rotation.x = -Math.PI / 2
  ground.position.y = -5
  scene.add(ground)
  
  const gridHelper = new THREE.GridHelper(SCENE_SIZE * 2, 50, 0x1a3a5c, 0x0d1f33)
  gridHelper.position.y = -4
  scene.add(gridHelper)
}

const loadMapData = async () => {
  // 尝试多个数据源（按优先级）
  const sources = [
    MAP_CONFIG.mapDataUrl,
    MAP_CONFIG.fallbackMapDataUrl
  ].filter(url => url) // 过滤掉空值
  
  for (const url of sources) {
    try {
      console.log(`尝试加载地图数据: ${url}`)
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10000) // 10秒超时
      
      const response = await fetch(url, {
        signal: controller.signal,
        headers: {
          'Accept': 'application/json'
        }
      })
      
      clearTimeout(timeoutId)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data = await response.json()
      console.log(`地图数据加载成功: ${url}, 包含 ${data.features?.length || 0} 个要素`)
      return data
    } catch (error) {
      console.warn(`加载地图数据失败 (${url}):`, error.message)
    }
  }
  
  console.error('所有地图数据源均不可用，将只显示网格背景')
  return null
}

const createProvinceOutlines = (mapData) => {
  if (!mapData || !mapData.features) return
  
  const provinceGroup = new THREE.Group()
  
  mapData.features.forEach((feature, index) => {
    const geometry = feature.geometry
    const coordinates = geometry.coordinates
    
    // 提取所有外环（处理 Polygon 和 MultiPolygon）
    let rings = []
    if (geometry.type === 'Polygon') {
      rings = coordinates  // coordinates 是二维数组: [[lon,lat],...]
    } else if (geometry.type === 'MultiPolygon') {
      // 取每个多边形的第一个环（外边界）
      rings = coordinates.map(polygon => polygon[0])
    } else {
      return  // 跳过非多边形类型
    }
    
    rings.forEach(ring => {
      const points = []
      ring.forEach(coord => {
        const [lon, lat] = coord
        const pos = lngLatToScene(lat, lon)
        points.push(new THREE.Vector3(pos.x, 0, pos.z))
      })
      
      if (points.length > 2) {
        const curve = new THREE.CatmullRomCurve3(points, true)
        const tubeGeo = new THREE.TubeGeometry(curve, points.length * 2, 0.3, 8, true)
        const tubeMat = new THREE.MeshBasicMaterial({
          color: 0x409EFF,
          transparent: true,
          opacity: 0.4
        })
        const tube = new THREE.Mesh(tubeGeo, tubeMat)
        provinceGroup.add(tube)
        
        const shape = new THREE.Shape()
        shape.moveTo(points[0].x, points[0].z)
        points.forEach(p => shape.lineTo(p.x, p.z))
        shape.closePath()
        
        const fillGeo = new THREE.ShapeGeometry(shape)
        const fillMat = new THREE.MeshBasicMaterial({
          color: 0x1a3a5c,
          transparent: true,
          opacity: 0.15,
          side: THREE.DoubleSide
        })
        const fill = new THREE.Mesh(fillGeo, fillMat)
        fill.rotation.x = -Math.PI / 2
        fill.position.y = -3
        provinceGroup.add(fill)
      }
    })
  })
  
  scene.add(provinceGroup)
}

const createMapGlowEffect = () => {
  const glowGeometry = new THREE.PlaneGeometry(SCENE_SIZE * 1.8, SCENE_SIZE * 1.8)
  const glowMaterial = new THREE.ShaderMaterial({
    uniforms: {
      time: { value: 0 },
      color: { value: new THREE.Color(0x00d4ff) }
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform float time;
      uniform vec3 color;
      varying vec2 vUv;
      
      void main() {
        float dist = distance(vUv, vec2(0.5));
        float alpha = smoothstep(0.5, 0.3, dist) * 0.3;
        alpha *= 0.5 + 0.5 * sin(time * 0.5);
        gl_FragColor = vec4(color, alpha);
      }
    `,
    transparent: true,
    side: THREE.DoubleSide,
    depthWrite: false
  })
  
  const glow = new THREE.Mesh(glowGeometry, glowMaterial)
  glow.rotation.x = -Math.PI / 2
  glow.position.y = -2
  glow.userData.isMapGlow = true
  scene.add(glow)
}

// ==================== 节点 ====================

const updateNodes = () => {
  if (!nodeGroup) return  // 等待初始化
  
  nodeGroup.clear()
  nodeObjects = []
  
  if (!showFacilities.value) return
  
  const selectedIds = props.selectedFacilities.map(f => f.id)
  
  props.candidates.forEach(cand => {
    const isSelected = selectedIds.includes(cand.id)
    const pos = lngLatToScene(cand.lat || cand.latitude, cand.lon || cand.longitude)
    const node = createFacilityNode(cand, pos, isSelected)
    node.userData = { ...cand, isSelected }
    nodeGroup.add(node)
    nodeObjects.push(node)
  })
  
  props.customers.forEach(cust => {
    const pos = lngLatToScene(cust.lat || cust.latitude, cust.lon || cust.longitude)
    const node = createCustomerNode(cust, pos)
    node.userData = { ...cust, isSelected: false }
    nodeGroup.add(node)
    nodeObjects.push(node)
  })
  
  updateStats()
}

const createFacilityNode = (data, position, isSelected) => {
  const group = new THREE.Group()
  group.position.copy(position)
  
  const color = isSelected ? 0xff6b6b : 0x409EFF
  const glowColor = isSelected ? 0xff6b6b : 0x409EFF
  
  const baseGeo = new THREE.CylinderGeometry(3, 4, 1, 6)
  const baseMat = new THREE.MeshStandardMaterial({
    color: color,
    emissive: glowColor,
    emissiveIntensity: 0.3,
    metalness: 0.5,
    roughness: 0.3
  })
  const base = new THREE.Mesh(baseGeo, baseMat)
  base.position.y = 0.5
  group.add(base)
  
  const ringGeo = new THREE.RingGeometry(4, 5, 32)
  const ringMat = new THREE.MeshBasicMaterial({
    color: glowColor,
    transparent: true,
    opacity: 0.5,
    side: THREE.DoubleSide
  })
  const ring = new THREE.Mesh(ringGeo, ringMat)
  ring.rotation.x = -Math.PI / 2
  ring.position.y = 1.1
  group.add(ring)
  
  if (isSelected) {
    const beamGeo = new THREE.CylinderGeometry(0.5, 0.5, 30, 8)
    const beamMat = new THREE.MeshBasicMaterial({
      color: 0xff6b6b,
      transparent: true,
      opacity: 0.4
    })
    const beam = new THREE.Mesh(beamGeo, beamMat)
    beam.position.y = 16
    group.add(beam)
  }
  
  const topGeo = new THREE.SphereGeometry(1.5, 16, 16)
  const topMat = new THREE.MeshBasicMaterial({ color: glowColor })
  const top = new THREE.Mesh(topGeo, topMat)
  top.position.y = 32
  group.add(top)
  
  const label = createLabel(data.name || data.id, isSelected)
  label.position.y = 40
  group.add(label)
  
  return group
}

const createCustomerNode = (data, position) => {
  const group = new THREE.Group()
  group.position.copy(position)
  
  const dotGeo = new THREE.SphereGeometry(1.5, 16, 16)
  const dotMat = new THREE.MeshBasicMaterial({ color: 0x67c23a })
  const dot = new THREE.Mesh(dotGeo, dotMat)
  dot.position.y = 2
  group.add(dot)
  
  const glowGeo = new THREE.RingGeometry(2, 3, 32)
  const glowMat = new THREE.MeshBasicMaterial({
    color: 0x67c23a,
    transparent: true,
    opacity: 0.5,
    side: THREE.DoubleSide
  })
  const glow = new THREE.Mesh(glowGeo, glowMat)
  glow.rotation.x = -Math.PI / 2
  glow.position.y = 2.1
  group.add(glow)
  
  return group
}

const createLabel = (text, isHighlight) => {
  const labelDiv = document.createElement('div')
  labelDiv.className = 'node-label' + (isHighlight ? ' highlight' : '')
  labelDiv.textContent = text
  
  const label = new CSS2DObject(labelDiv)
  return label
}

// ==================== 连线 ====================

const updateConnections = () => {
  if (!connectionGroup || !flyLineGroup) return  // 等待初始化
  
  connectionGroup.clear()
  flyLineGroup.clear()
  connectionObjects = []
  flyLineObjects = []
  
  if (!showConnections.value || !props.assignments) return
  
  Object.entries(props.assignments).forEach(([custId, facId]) => {
    const cust = props.customers.find(c => String(c.id) === String(custId))
    const fac = props.candidates.find(c => String(c.id) === String(facId))
    
    if (cust && fac) {
      const custLat = cust.lat || cust.latitude
      const custLon = cust.lon || cust.longitude
      const facLat = fac.lat || fac.latitude
      const facLon = fac.lon || fac.longitude
      
      const start = lngLatToScene(custLat, custLon)
      const end = lngLatToScene(facLat, facLon)
      
      if (showConnections.value) {
        createConnection(start, end, fac.isSelected ? 0xff6b6b : 0x409EFF)
      }
      
      if (showFlyLines.value) {
        createFlyLine(start, end)
      }
    }
  })
  
  updateStats()
}

const createConnection = (start, end, color) => {
  const midPoint = new THREE.Vector3(
    (start.x + end.x) / 2,
    30 + Math.random() * 20,
    (start.z + end.z) / 2
  )
  
  const curve = new THREE.QuadraticBezierCurve3(start, midPoint, end)
  const points = curve.getPoints(50)
  
  const geometry = new THREE.BufferGeometry().setFromPoints(points)
  const material = new THREE.LineBasicMaterial({
    color: color,
    transparent: true,
    opacity: 0.4
  })
  
  const line = new THREE.Line(geometry, material)
  connectionGroup.add(line)
  connectionObjects.push(line)
}

const createFlyLine = (start, end) => {
  const group = new THREE.Group()
  
  const midPoint = new THREE.Vector3(
    (start.x + end.x) / 2,
    30,
    (start.z + end.z) / 2
  )
  
  const curve = new THREE.QuadraticBezierCurve3(start, midPoint, end)
  const points = curve.getPoints(100)
  
  const geometry = new THREE.BufferGeometry().setFromPoints(points)
  const material = new THREE.LineBasicMaterial({
    color: 0x00ffff,
    transparent: true,
    opacity: 0.6
  })
  
  const line = new THREE.Line(geometry, material)
  group.add(line)
  
  const flyDotGeo = new THREE.SphereGeometry(1.5, 16, 16)
  const flyDotMat = new THREE.MeshBasicMaterial({ color: 0x00ffff })
  const flyDot = new THREE.Mesh(flyDotGeo, flyDotMat)
  group.add(flyDot)
  
  flyLineGroup.add(group)
  flyLineObjects.push({
    group,
    curve,
    flyDot,
    progress: Math.random()
  })
}

// ==================== 动画 ====================

const animate = () => {
  animationId = requestAnimationFrame(animate)
  
  controls.autoRotate = autoRotate.value
  controls.update()
  
  const time = Date.now() * 0.001
  
  nodeObjects.forEach((node, i) => {
    node.children.forEach(child => {
      if (child.geometry?.type === 'RingGeometry') {
        child.rotation.z = time * 0.5
      }
    })
    
    const pulse = Math.sin(time * 2 + i) * 0.1 + 1
    if (node.userData.isSelected) {
      node.children.forEach(child => {
        if (child.geometry?.type === 'CylinderGeometry' && child.geometry.parameters.radiusTop === 0.5) {
          child.scale.setScalar(pulse)
        }
      })
    }
  })
  
  flyLineObjects.forEach(flyLine => {
    flyLine.progress += 0.005
    if (flyLine.progress > 1) flyLine.progress = 0
    
    const point = flyLine.curve.getPoint(flyLine.progress)
    flyLine.flyDot.position.copy(point)
  })
  
  scene.children.forEach(child => {
    if (child.userData?.isMapGlow && child.material?.uniforms) {
      child.material.uniforms.time.value = time
    }
  })
  
  renderer.render(scene, camera)
  labelRenderer.render(scene, camera)
}

// ==================== 工具函数 ====================

const lngLatToScene = (lat, lon) => {
  const x = ((lon - BOUNDS.minLon) / (BOUNDS.maxLon - BOUNDS.minLon) - 0.5) * SCENE_SIZE
  const z = ((lat - BOUNDS.minLat) / (BOUNDS.maxLat - BOUNDS.minLat) - 0.5) * SCENE_SIZE
  return new THREE.Vector3(x, 0, z)
}

const updateStats = () => {
  const selectedIds = props.selectedFacilities.map(f => f.id)
  const connectedCustomers = Object.keys(props.assignments || {}).length
  
  stats.value = {
    nodes: props.candidates.length + props.customers.length,
    connections: Object.keys(props.assignments || {}).length,
    coverage: props.customers.length > 0 
      ? Math.round((connectedCustomers / props.customers.length) * 100) 
      : 0
  }
}

const getNodeIcon = (type) => {
  const icons = {
    warehouse: '🏭',
    factory: '🏭',
    station: '🚛',
    dc: '🚛',
    customer: '📍'
  }
  return icons[type] || '📍'
}

const getTypeName = (type) => {
  const names = {
    warehouse: '仓库',
    factory: '工厂',
    station: '配送站',
    dc: '配送中心',
    customer: '客户'
  }
  return names[type] || '未知'
}

const handleResize = () => {
  if (!containerRef.value || !camera || !renderer) return
  
  const width = containerRef.value.clientWidth
  const height = containerRef.value.clientHeight
  
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  
  renderer.setSize(width, height)
  if (labelRenderer) {
    labelRenderer.setSize(width, height)
  }
}

// ==================== 监听 ====================

// 等初始化完成后再响应数据变化
watch(() => [props.customers, props.candidates, props.selectedFacilities, props.assignments], 
  () => {
    if (isInitialized.value) {
      try {
        updateNodes()
        updateConnections()
      } catch (error) {
        console.error('更新网络数据失败:', error)
      }
    }
  }, 
  { deep: true }
)

watch(autoRotate, (val) => {
  if (controls) controls.autoRotate = val
})

watch(showFacilities, () => {
  if (isInitialized.value) {
    try {
      updateNodes()
    } catch (error) {
      console.error('更新节点失败:', error)
    }
  }
})

watch([showConnections, showFlyLines], () => {
  if (isInitialized.value) {
    try {
      updateConnections()
    } catch (error) {
      console.error('更新连线失败:', error)
    }
  }
})

watch(showMapEffect, (val) => {
  if (!isInitialized.value) return
  scene.children.forEach(child => {
    if (child.userData?.isMapGlow) {
      child.visible = val
    }
  })
})

// ==================== 生命周期 ====================

onMounted(() => {
  initScene()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  
  if (animationId) cancelAnimationFrame(animationId)
  
  // 停止所有动画
  if (pulseAnimationId) clearInterval(pulseAnimationId)
  
  // 清理 Three.js 资源
  if (renderer) {
    renderer.dispose()
    if (containerRef.value && renderer.domElement) {
      containerRef.value.removeChild(renderer.domElement)
    }
  }
  
  if (labelRenderer) {
    labelRenderer.dispose()
  }
  
  if (controls) controls.dispose()
  
  // 清理场景对象
  if (scene) {
    scene.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose()
      if (obj.material) {
        if (Array.isArray(obj.material)) {
          obj.material.forEach(m => m.dispose())
        } else {
          obj.material.dispose()
        }
      }
    })
  }
  
  // 清空引用
  nodeObjects = []
  connectionObjects = []
  flyLineObjects = []
})
</script>

<style scoped>
.network-3d-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: linear-gradient(180deg, #0a1628 0%, #0d1f33 100%);
  border-radius: 8px;
  overflow: hidden;
}

.scene-container {
  width: 100%;
  height: 100%;
  min-height: 600px;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(10, 22, 40, 0.95);
  color: #fff;
  z-index: 100;
}

.loading-overlay p {
  margin-top: 15px;
  font-size: 14px;
  color: #409EFF;
}

.title-panel {
  position: absolute;
  top: 20px;
  left: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  background: rgba(10, 22, 40, 0.9);
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 25px;
  backdrop-filter: blur(10px);
  z-index: 10;
}

.title-icon { font-size: 20px; }
.title-text { font-size: 16px; font-weight: 600; color: #fff; }

.control-panel {
  position: absolute;
  top: 80px;
  right: 20px;
  z-index: 10;
}

.control-card {
  width: 180px;
  background: rgba(10, 22, 40, 0.95);
  border: 1px solid rgba(64, 158, 255, 0.3);
}

.control-card :deep(.el-card__header) {
  background: transparent;
  color: #fff;
  padding: 10px 15px;
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
  font-size: 13px;
}

.control-card :deep(.el-card__body) { padding: 12px; }
.control-card :deep(.el-form-item) { margin-bottom: 8px; }
.control-card :deep(.el-form-item__label) { color: #aaa; font-size: 11px; }
.control-card :deep(.el-divider) { margin: 10px 0; }

.legend { display: flex; flex-direction: column; gap: 8px; }
.legend-item { display: flex; align-items: center; gap: 8px; color: #ccc; font-size: 11px; }

.dot { width: 10px; height: 10px; border-radius: 50%; }
.dot.warehouse { background: #ff6b6b; box-shadow: 0 0 8px #ff6b6b; }
.dot.station { background: #409EFF; box-shadow: 0 0 8px #409EFF; }
.dot.customer { background: #67c23a; box-shadow: 0 0 8px #67c23a; }
.dot.selected { background: #ff6b6b; }
.line-connection { width: 20px; height: 2px; background: linear-gradient(90deg, #409EFF, #67c23a); }

.stats-panel {
  position: absolute;
  bottom: 20px;
  left: 20px;
  display: flex;
  gap: 20px;
  padding: 15px 25px;
  background: rgba(10, 22, 40, 0.9);
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 15px;
  backdrop-filter: blur(10px);
  z-index: 10;
}

.stat-item { display: flex; flex-direction: column; align-items: center; }
.stat-value { font-size: 24px; font-weight: 700; color: #409EFF; }
.stat-label { font-size: 11px; color: #888; margin-top: 4px; }

.node-info-card {
  position: absolute;
  bottom: 100px;
  right: 20px;
  width: 220px;
  padding: 16px;
  background: rgba(10, 22, 40, 0.95);
  border: 1px solid rgba(64, 158, 255, 0.4);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  z-index: 10;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
  margin-bottom: 12px;
}

.node-icon { font-size: 20px; }
.node-name { flex: 1; font-size: 14px; font-weight: 600; color: #fff; }
.card-content { display: flex; flex-direction: column; gap: 8px; }
.info-row { display: flex; justify-content: space-between; font-size: 12px; }
.info-row .label { color: #888; }
.info-row .value { color: #fff; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s, transform 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateX(20px); }
</style>

<style>
.node-label {
  padding: 4px 8px;
  background: rgba(10, 22, 40, 0.9);
  border: 1px solid rgba(64, 158, 255, 0.5);
  border-radius: 4px;
  color: #fff;
  font-size: 11px;
  white-space: nowrap;
  pointer-events: none;
  user-select: none;
}

.node-label.highlight {
  background: rgba(255, 107, 107, 0.3);
  border-color: #ff6b6b;
  color: #ff6b6b;
}
</style>
