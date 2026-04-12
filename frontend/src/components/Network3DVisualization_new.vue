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
          <div class="info-row">
            <span class="label">坐标</span>
            <span class="value">{{ selectedNode.lng?.toFixed(2) }}, {{ selectedNode.lat?.toFixed(2) }}</span>
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
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js'
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
  // 地图数据
  mapDataUrl: 'https://z2586300277.github.io/3d-file-server/files/json/china.json',
  // 纹理
  textureUrl: 'https://z2586300277.github.io/three-editor/dist/files/channels/texture.png',
  // 光柱纹理
  lightColumnUrl: 'https://z2586300277.github.io/3d-file-server/images/channels/lightMap.png',
  // 场景参数
  sceneParams: {
    background: 0x0a1628,
    cameraPosition: { x: 0, y: 200, z: 400 },
    cameraNear: 0.1,
    cameraFar: 10000
  }
}

// 中国区域经纬度边界
const BOUNDS = {
  minLon: 73,
  maxLon: 135,
  minLat: 18,
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
  
  // 开始动画
  animate()
}

// 设置光照
const setupLights = () => {
  // 环境光
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
  scene.add(ambientLight)
  
  // 主方向光
  const mainLight = new THREE.DirectionalLight(0xffffff, 0.8)
  mainLight.position.set(100, 200, 100)
  scene.add(mainLight)
  
  // 补光
  const fillLight = new THREE.DirectionalLight(0x4488ff, 0.3)
  fillLight.position.set(-100, 100, -100)
  scene.add(fillLight)
}

// ==================== 地图 ====================

const setupMap = async () => {
  try {
    // 创建地面网格
    createGroundGrid()
    
    // 加载地图数据
    const mapData = await loadMapData()
    
    // 创建简化地图（省份轮廓）
    createProvinceOutlines(mapData)
    
    // 添加地图光效
    if (showMapEffect.value) {
      createMapGlowEffect()
    }
  } catch (error) {
    console.error('加载地图失败:', error)
    // 创建备用网格
    createGroundGrid()
  }
}

const createGroundGrid = () => {
  // 地面
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
  
  // 网格线
  const gridHelper = new THREE.GridHelper(SCENE_SIZE * 2, 50, 0x1a3a5c, 0x0d1f33)
  gridHelper.position.y = -4
  scene.add(gridHelper)
}

const loadMapData = async () => {
  try {
    const response = await fetch(MAP_CONFIG.mapDataUrl)
    return await response.json()
  } catch (error) {
    console.error('加载地图数据失败:', error)
    return null
  }
}

const createProvinceOutlines = (mapData) => {
  if (!mapData || !mapData.features) return
  
  const provinceGroup = new THREE.Group()
  
  mapData.features.forEach((feature, index) => {
    const coordinates = feature.geometry.coordinates
    
    // 处理多边形和多多边形
    const rings = Array.isArray(coordinates[0][0]) ? coordinates : [coordinates]
    
    rings.forEach(ring => {
      const points = []
      ring.forEach(coord => {
        const [lon, lat] = coord
        const pos = lngLatToScene(lat, lon)
        points.push(new THREE.Vector3(pos.x, 0, pos.z))
      })
      
      if (points.length > 2) {
        // 创建省份轮廓线
        const curve = new THREE.CatmullRomCurve3(points, true)
        const tubeGeo = new THREE.TubeGeometry(curve, points.length * 2, 0.3, 8, true)
        const tubeMat = new THREE.MeshBasicMaterial({
          color: 0x409EFF,
          transparent: true,
          opacity: 0.4
        })
        const tube = new THREE.Mesh(tubeGeo, tubeMat)
        provinceGroup.add(tube)
        
        // 填充面
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
  // 创建发光边缘
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
  scene.add(glow)
  
  // 存储引用用于动画
  glow.userData.isMapGlow = true
}

// ==================== 节点 ====================

const updateNodes = () => {
  // 清除旧节点
  nodeGroup.clear()
  nodeObjects = []
  
  if (!showFacilities.value) return
  
  const selectedIds = props.selectedFacilities.map(f => f.id)
  
  // 添加候选设施节点
  props.candidates.forEach(cand => {
    const isSelected = selectedIds.includes(cand.id)
    const pos = lngLatToScene(cand.lat, cand.lon)
    const node = createFacilityNode(cand, pos, isSelected)
    node.userData = { ...cand, isSelected }
    nodeGroup.add(node)
    nodeObjects.push(node)
  })
  
  // 添加客户节点
  props.customers.forEach(cust => {
    const pos = lngLatToScene(cust.lat, cust.lon)
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
  
  // 节点颜色
  const color = isSelected ? 0xff6b6b : 0x409EFF
  const glowColor = isSelected ? 0xff6b6b : 0x409EFF
  
  // 底座
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
  
  // 发光环
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
  
  // 如果选中，添加光柱
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
  
  // 顶部闪烁点
  const topGeo = new THREE.SphereGeometry(1.5, 16, 16)
  const topMat = new THREE.MeshBasicMaterial({ color: glowColor })
  const top = new THREE.Mesh(topGeo, topMat)
  top.position.y = 32
  group.add(top)
  
  // 标签
  const label = createLabel(data.name || data.id, isSelected)
  label.position.y = 40
  group.add(label)
  
  return group
}

const createCustomerNode = (data, position) => {
  const group = new THREE.Group()
  group.position.copy(position)
  
  // 客户点（小圆点）
  const dotGeo = new THREE.SphereGeometry(1.5, 16, 16)
  const dotMat = new THREE.MeshBasicMaterial({ color: 0x67c23a })
  const dot = new THREE.Mesh(dotGeo, dotMat)
  dot.position.y = 2
  group.add(dot)
  
  // 光晕
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
  labelDiv.className = 'node-label'
  labelDiv.textContent = text
  if (isHighlight) {
    labelDiv.classList.add('highlight')
  }
  
  const label = new CSS2DObject(labelDiv)
  return label
}

// ==================== 连线 ====================

const updateConnections = () => {
  connectionGroup.clear()
  flyLineGroup.clear()
  connectionObjects = []
  flyLineObjects = []
  
  if (!showConnections.value || !props.assignments) return
  
  // 创建静态连线
  Object.entries(props.assignments).forEach(([custId, facId]) => {
    const cust = props.customers.find(c => String(c.id) === String(custId))
    const fac = props.candidates.find(c => String(c.id) === String(facId))
    
    if (cust && fac) {
      const start = lngLatToScene(cust.lat, cust.lon)
      const end = lngLatToScene(fac.lat, fac.lon)
      
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
  // 创建弧线
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
  // 创建飞线动画
  const group = new THREE.Group()
  
  // 基础线
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
  
  // 飞点
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
  
  // 更新控制器
  controls.autoRotate = autoRotate.value
  controls.update()
  
  // 动画节点
  const time = Date.now() * 0.001
  
  nodeObjects.forEach((node, i) => {
    // 旋转光环
    node.children.forEach(child => {
      if (child.geometry?.type === 'RingGeometry') {
        child.rotation.z = time * 0.5
      }
    })
    
    // 脉冲效果
    const pulse = Math.sin(time * 2 + i) * 0.1 + 1
    if (node.userData.isSelected) {
      node.children.forEach(child => {
        if (child.geometry?.type === 'CylinderGeometry' && child.geometry.parameters.radiusTop === 0.5) {
          child.scale.setScalar(pulse)
        }
      })
    }
  })
  
  // 动画飞线
  flyLineObjects.forEach(flyLine => {
    flyLine.progress += 0.005
    if (flyLine.progress > 1) flyLine.progress = 0
    
    const point = flyLine.curve.getPoint(flyLine.progress)
    flyLine.flyDot.position.copy(point)
  })
  
  // 地图发光效果
  scene.children.forEach(child => {
    if (child.userData?.isMapGlow && child.material?.uniforms) {
      child.material.uniforms.time.value = time
    }
  })
  
  // 渲染
  renderer.render(scene, camera)
  labelRenderer.render(scene, camera)
}

// ==================== 工具函数 ====================

// 经纬度转场景坐标
const lngLatToScene = (lat, lon) => {
  const x = ((lon - BOUNDS.minLon) / (BOUNDS.maxLon - BOUNDS.minLon) - 0.5) * SCENE_SIZE
  const z = ((lat - BOUNDS.minLat) / (BOUNDS.maxLat - BOUNDS.minLat) - 0.5) * SCENE_SIZE
  return new THREE.Vector3(x, 0, z)
}

// 更新统计
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

// 获取节点图标
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

// 获取类型名称
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

// 点击事件
const onNodeClick = (event) => {
  if (event.point) {
    // 找到最近的节点
    let closest = null
    let minDist = Infinity
    
    nodeObjects.forEach(node => {
      const dist = node.position.distanceTo(event.point)
      if (dist < minDist && dist < 20) {
        minDist = dist
        closest = node.userData
      }
    })
    
    if (closest) {
      selectedNode.value = closest
      emit('node-click', closest)
    }
  }
}

// 窗口调整
const handleResize = () => {
  if (!containerRef.value || !camera || !renderer) return
  
  const width = containerRef.value.clientWidth
  const height = containerRef.value.clientHeight
  
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  
  renderer.setSize(width, height)
  labelRenderer.setSize(width, height)
}

// ==================== 监听 ====================

watch(() => [props.customers, props.candidates, props.selectedFacilities, props.assignments], 
  () => {
    updateNodes()
    updateConnections()
  }, 
  { deep: true }
)

watch(autoRotate, (val) => {
  if (controls) controls.autoRotate = val
})

watch(showFacilities, () => updateNodes())

watch([showConnections, showFlyLines], () => updateConnections())

watch(showMapEffect, (val) => {
  // 地图发光效果切换
  scene.children.forEach(child => {
    if (child.userData?.isMapGlow) {
      child.visible = val
    }
  })
})

// ==================== 生命周期 ====================

onMounted(() => {
  initScene()
  
  // 添加点击事件
  if (renderer?.domElement) {
    renderer.domElement.addEventListener('click', onNodeClick)
  }
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  
  if (renderer?.domElement) {
    renderer.domElement.removeEventListener('click', onNodeClick)
  }
  
  if (animationId) cancelAnimationFrame(animationId)
  
  // 清理
  if (renderer) {
    renderer.dispose()
    containerRef.value?.removeChild(renderer.domElement)
  }
  
  if (labelRenderer) {
    labelRenderer.dispose()
  }
  
  if (controls) controls.dispose()
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

/* 加载 */
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

/* 标题 */
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

.title-icon {
  font-size: 20px;
}

.title-text {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

/* 控制面板 */
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

.control-card :deep(.el-card__body) {
  padding: 12px;
}

.control-card :deep(.el-form-item) {
  margin-bottom: 8px;
}

.control-card :deep(.el-form-item__label) {
  color: #aaa;
  font-size: 11px;
}

.control-card :deep(.el-divider) {
  margin: 10px 0;
}

.legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ccc;
  font-size: 11px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot.warehouse { background: #ff6b6b; box-shadow: 0 0 8px #ff6b6b; }
.dot.station { background: #409EFF; box-shadow: 0 0 8px #409EFF; }
.dot.customer { background: #67c23a; box-shadow: 0 0 8px #67c23a; }
.dot.selected { background: #ff6b6b; }

.line-connection {
  width: 20px;
  height: 2px;
  background: linear-gradient(90deg, #409EFF, #67c23a);
}

/* 统计面板 */
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

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #409EFF;
}

.stat-label {
  font-size: 11px;
  color: #888;
  margin-top: 4px;
}

/* 节点信息卡片 */
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

.node-icon {
  font-size: 20px;
}

.node-name {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.info-row .label {
  color: #888;
}

.info-row .value {
  color: #fff;
}

/* 动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>

<style>
/* 全局样式 - 节点标签 */
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
