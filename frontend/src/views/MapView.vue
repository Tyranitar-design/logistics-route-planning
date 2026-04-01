<template>
  <div class="map-view">
    <el-row :gutter="20">
      <!-- 左侧地图 -->
      <el-col :span="18">
        <el-card>
          <div class="map-toolbar">
            <el-radio-group v-model="mapType" size="small" @change="switchMapLayer">
              <el-radio-button value="standard" label="standard">标准地图</el-radio-button>
              <el-radio-button value="traffic" label="traffic">实时路况</el-radio-button>
              <el-radio-button value="satellite" label="satellite">卫星图</el-radio-button>
            </el-radio-group>
            <el-checkbox v-model="showTraffic" @change="toggleTraffic" style="margin-left: 15px">
              显示路况
            </el-checkbox>
            <el-button 
              type="primary" 
              size="small" 
              style="margin-left: 15px"
              @click="showTrafficPanel = !showTrafficPanel"
              :disabled="!recommendResult"
            >
              🚦 路况规避
            </el-button>
          </div>
          <div id="map" class="map-container"></div>
          
          <!-- 路况规避面板 -->
          <transition name="slide-up">
            <div v-if="showTrafficPanel && recommendResult" class="traffic-panel">
              <TrafficMonitor
                v-if="currentRouteCoords.origin && currentRouteCoords.destination"
                :origin="currentRouteCoords.origin"
                :destination="currentRouteCoords.destination"
                :auto-start="true"
                @route-change="handleRouteChange"
                @traffic-update="handleTrafficUpdate"
              />
            </div>
          </transition>
        </el-card>
      </el-col>
      
      <!-- 右侧控制面板 -->
      <el-col :span="6">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>🗺️ 路线规划</span>
              <el-tag size="small" type="success" v-if="useAmap">高德地图</el-tag>
              <el-tag size="small" type="info" v-else>本地算法</el-tag>
            </div>
          </template>
          
          <el-form :model="routeForm" label-width="80px" size="small">
            <el-form-item label="数据源">
              <el-switch
                v-model="useAmap"
                active-text="高德地图"
                inactive-text="本地算法"
              />
            </el-form-item>
            
            <el-form-item label="起点">
              <el-select v-model="routeForm.startNode" placeholder="选择起点" style="width: 100%" filterable>
                <el-option
                  v-for="node in nodes"
                  :key="node.id"
                  :label="`${node.name} (${getTypeText(node.type)})`"
                  :value="node.id"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="终点">
              <el-select v-model="routeForm.endNode" placeholder="选择终点" style="width: 100%" filterable>
                <el-option
                  v-for="node in nodes"
                  :key="node.id"
                  :label="`${node.name} (${getTypeText(node.type)})`"
                  :value="node.id"
                />
              </el-select>
            </el-form-item>
            
            <!-- 高德地图特有选项 -->
            <template v-if="useAmap">
              <el-form-item label="路线策略">
                <el-select v-model="routeForm.strategy" style="width: 100%">
                  <el-option label="速度优先（推荐）" :value="0" />
                  <el-option label="费用优先（不走收费路段）" :value="1" />
                  <el-option label="距离优先（最短距离）" :value="2" />
                  <el-option label="躲避拥堵" :value="4" />
                  <el-option label="多路线对比" :value="5" />
                </el-select>
              </el-form-item>
            </template>
            
            <!-- 本地算法选项 -->
            <template v-else>
              <el-form-item label="优化目标">
                <el-radio-group v-model="routeForm.optimizeBy">
                  <el-radio value="distance">最短距离</el-radio>
                  <el-radio value="time">最短时间</el-radio>
                  <el-radio value="cost">最低成本</el-radio>
                </el-radio-group>
              </el-form-item>
              
              <el-form-item label="算法选择">
                <el-select v-model="routeForm.algorithm" style="width: 100%">
                  <el-option label="Dijkstra（经典最短路径）" value="dijkstra" />
                  <el-option label="A*（启发式搜索）" value="astar" />
                </el-select>
              </el-form-item>
            </template>
            
            <el-form-item>
              <el-button type="primary" @click="handleRecommend" :loading="loading" style="width: 100%">
                🚀 规划路线
              </el-button>
            </el-form-item>
            
            <el-form-item>
              <el-button @click="handleCompare" :loading="compareLoading" style="width: 100%">
                📊 对比两种方案
              </el-button>
            </el-form-item>
          </el-form>
          
          <!-- 推荐结果 -->
          <div v-if="recommendResult" class="recommend-result">
            <el-divider />
            <h4>📊 规划结果</h4>
            
            <!-- 路况状态（高德） -->
            <div v-if="recommendResult.traffic_info" class="traffic-status">
              <el-tag :type="getTrafficTagType(recommendResult.traffic_info.evaluation)">
                {{ recommendResult.traffic_info.evaluation || '路况未知' }}
              </el-tag>
            </div>
            
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="总距离">
                {{ recommendResult.distance_km || recommendResult.total_distance }} 公里
              </el-descriptions-item>
              <el-descriptions-item label="预计时间">
                {{ recommendResult.duration_minutes || recommendResult.total_time * 60 }} 分钟
              </el-descriptions-item>
              <!-- 天气调整后的时间 -->
              <el-descriptions-item label="天气调整" v-if="recommendResult.weather_adjusted">
                <el-tag type="warning" size="small">
                  {{ recommendResult.adjusted_duration_minutes }} 分钟
                </el-tag>
                <span style="color: #909399; font-size: 12px; margin-left: 5px">
                  (延误风险 {{ (recommendResult.delay_risk * 100).toFixed(0) }}%)
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="过路费" v-if="recommendResult.tolls">
                {{ recommendResult.tolls }} 元
              </el-descriptions-item>
              <el-descriptions-item label="预估成本" v-if="recommendResult.total_cost">
                {{ recommendResult.total_cost }} 元
              </el-descriptions-item>
              <el-descriptions-item label="数据来源">
                <el-tag size="small" :type="recommendResult.source === 'amap' ? 'success' : 'info'">
                  {{ recommendResult.source === 'amap' ? '高德地图' : '本地算法' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="天气影响" v-if="recommendResult.weather_impact">
                <el-tag size="small" :type="getWeatherImpactType(recommendResult.weather_impact)">
                  {{ recommendResult.weather_impact }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
            
            <!-- 天气建议 -->
            <div v-if="recommendResult.weather_suggestions && recommendResult.weather_suggestions.length > 0" 
                 class="weather-suggestions">
              <el-alert type="warning" :closable="false" style="margin-top: 10px">
                <template #title>
                  <span style="font-weight: bold">🌤️ 天气运输建议</span>
                </template>
                <ul style="margin: 5px 0; padding-left: 20px; font-size: 12px">
                  <li v-for="(suggestion, index) in recommendResult.weather_suggestions.slice(0, 3)" 
                      :key="index">
                    {{ suggestion }}
                  </li>
                </ul>
              </el-alert>
            </div>
            
            <!-- 途经节点 -->
            <div v-if="recommendResult.path && recommendResult.path.length > 0" style="margin-top: 15px">
              <h5>途经节点：</h5>
              <el-tag v-for="(node, index) in recommendResult.path" :key="index" style="margin: 2px">
                {{ node?.name || '未知' }}
              </el-tag>
            </div>
            
            <!-- 路段详情（高德） -->
            <div v-if="recommendResult.steps && recommendResult.steps.length > 0" style="margin-top: 15px">
              <el-collapse>
                <el-collapse-item title="📝 详细路段" name="steps">
                  <div v-for="(step, index) in recommendResult.steps.slice(0, 10)" :key="index" class="step-item">
                    <div>{{ step.instruction }}</div>
                    <div class="step-meta">
                      <span>{{ step.distance }}米</span>
                      <span>{{ step.duration }}秒</span>
                      <el-tag v-if="step.toll_road" size="small" type="warning">收费</el-tag>
                    </div>
                  </div>
                  <div v-if="recommendResult.steps.length > 10" style="color: #909399; font-size: 12px">
                    还有 {{ recommendResult.steps.length - 10 }} 个路段...
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
          
          <!-- 对比结果 -->
          <div v-if="compareResult" class="compare-result">
            <el-divider />
            <h4>📈 方案对比</h4>
            
            <el-table :data="compareTableData" size="small" border>
              <el-table-column prop="label" label="指标" width="80" />
              <el-table-column prop="amap" label="高德地图">
                <template #default="{ row }">
                  <span :class="{ 'highlight': row.amapBetter }">{{ row.amap }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="local" label="本地算法">
                <template #default="{ row }">
                  <span :class="{ 'highlight': row.localBetter }">{{ row.local }}</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
        
        <!-- 实时路况卡片 -->
        <el-card style="margin-top: 15px">
          <template #header>
            <span>🚗 实时路况</span>
            <el-button size="small" text @click="refreshTraffic">刷新</el-button>
          </template>
          <div v-if="currentTraffic" class="traffic-info">
            <el-tag :type="getTrafficTagType(currentTraffic.evaluation)" size="large">
              {{ currentTraffic.evaluation || '未知' }}
            </el-tag>
            <div style="margin-top: 10px; font-size: 13px; color: #606266">
              当前路况：{{ getTrafficStatusText(currentTraffic.status) }}
            </div>
          </div>
          <div v-else style="color: #909399; font-size: 13px">
            选择节点后可查看周边路况
          </div>
        </el-card>
        
        <!-- 天气信息卡片 -->
        <el-card style="margin-top: 15px">
          <template #header>
            <span>🌤️ 天气信息</span>
          </template>
          <WeatherCard 
            :node-id="routeForm.startNode" 
            @weather-loaded="onWeatherLoaded"
          />
        </el-card>
        
        <!-- 图例 -->
        <el-card style="margin-top: 15px">
          <template #header>
            <span>📍 图例</span>
          </template>
          <div class="legend">
            <div class="legend-item">
              <span class="legend-color" style="background: #409EFF"></span>
              <span>仓库</span>
            </div>
            <div class="legend-item">
              <span class="legend-color" style="background: #67C23A"></span>
              <span>配送站</span>
            </div>
            <div class="legend-item">
              <span class="legend-color" style="background: #E6A23C"></span>
              <span>中转站</span>
            </div>
            <div class="legend-item">
              <span class="legend-color" style="background: #F56C6C"></span>
              <span>客户点</span>
            </div>
          </div>
          <el-divider />
          <div class="legend">
            <div class="legend-item">
              <span class="legend-line" style="background: #67C23A"></span>
              <span>畅通</span>
            </div>
            <div class="legend-item">
              <span class="legend-line" style="background: #E6A23C"></span>
              <span>缓行</span>
            </div>
            <div class="legend-item">
              <span class="legend-line" style="background: #F56C6C"></span>
              <span>拥堵</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getNodes } from '@/api/nodes'
import { recommendRoute } from '@/api/routes'
import { getMapNodes, getMapRoutes } from '@/api/map'
import { drivingRoute, multiRoute, trafficAtNode, compareRoutes } from '@/api/amap'
import WeatherCard from '@/components/WeatherCard.vue'
import TrafficMonitor from '@/components/TrafficMonitor.vue'

const nodes = ref([])
const showTrafficPanel = ref(false)
const currentRouteCoords = ref({
  origin: '',
  destination: ''
})
const loading = ref(false)
const compareLoading = ref(false)
const recommendResult = ref(null)
const compareResult = ref(null)
const currentTraffic = ref(null)
const currentWeather = ref(null)  // 当前天气数据
const useAmap = ref(true)
const showTraffic = ref(false)
const mapType = ref('standard')

const routeForm = ref({
  startNode: null,
  endNode: null,
  optimizeBy: 'distance',
  algorithm: 'dijkstra',
  strategy: 0
})

let map = null
let markers = []
let routeLines = []
let trafficLayer = null
let currentTileLayer = null

const typeColors = {
  warehouse: '#409EFF',
  station: '#67C23A',
  transfer: '#E6A23C',
  customer: '#F56C6C'
}

const trafficColors = {
  '1': '#67C23A',  // 畅通
  '2': '#E6A23C',  // 缓行
  '3': '#F56C6C',  // 拥堵
  '4': '#909399'   // 严重拥堵
}

const getTypeText = (type) => {
  const map = { warehouse: '仓库', station: '配送站', transfer: '中转站', customer: '客户点' }
  return map[type] || type
}

const getOptimizeText = (optimize) => {
  const map = { distance: '最短距离', time: '最短时间', cost: '最低成本' }
  return map[optimize] || optimize
}

const getTrafficTagType = (evaluation) => {
  if (!evaluation) return 'info'
  if (evaluation.includes('畅通')) return 'success'
  if (evaluation.includes('缓行')) return 'warning'
  if (evaluation.includes('拥堵')) return 'danger'
  return 'info'
}

const getWeatherImpactType = (impact) => {
  if (impact === '无影响') return 'success'
  if (impact === '轻微影响') return 'info'
  if (impact === '中度影响') return 'warning'
  if (impact === '严重影响') return 'danger'
  return 'danger'
}

const getTrafficStatusText = (status) => {
  const map = {
    '1': '畅通',
    '2': '缓行',
    '3': '拥堵',
    '4': '严重拥堵'
  }
  return map[status] || '未知'
}

// 对比表格数据
const compareTableData = computed(() => {
  if (!compareResult.value) return []
  
  const amap = compareResult.value.amap
  const local = compareResult.value.local
  
  if (!amap && !local) return []
  
  const data = []
  
  // 距离
  const amapDist = amap?.routes?.[0]?.distance ? (amap.routes[0].distance / 1000).toFixed(2) : '-'
  const localDist = local?.distance_km?.toFixed(2) || '-'
  data.push({
    label: '距离(km)',
    amap: amapDist,
    local: localDist,
    amapBetter: amapDist !== '-' && localDist !== '-' && parseFloat(amapDist) < parseFloat(localDist),
    localBetter: amapDist !== '-' && localDist !== '-' && parseFloat(localDist) < parseFloat(amapDist)
  })
  
  // 时间
  const amapTime = amap?.routes?.[0]?.duration ? Math.round(amap.routes[0].duration / 60) : '-'
  const localTime = local?.duration_minutes ? Math.round(local.duration_minutes) : '-'
  data.push({
    label: '时间(分)',
    amap: amapTime,
    local: localTime,
    amapBetter: amapTime !== '-' && localTime !== '-' && amapTime < localTime,
    localBetter: amapTime !== '-' && localTime !== '-' && localTime < amapTime
  })
  
  // 过路费（仅高德）
  if (amap?.routes?.[0]?.tolls) {
    data.push({
      label: '过路费(元)',
      amap: amap.routes[0].tolls.toFixed(2),
      local: local?.cost?.toFixed(2) || '-',
      amapBetter: false,
      localBetter: false
    })
  }
  
  return data
})

onMounted(async () => {
  // 加载节点数据
  try {
    const res = await getNodes()
    nodes.value = res.nodes
  } catch (error) {
    console.error('加载节点失败:', error)
  }
  
  // 等待DOM渲染完成后初始化地图
  await nextTick()
  initMap()
})

const initMap = async () => {
  // 动态加载Leaflet
  if (!window.L) {
    // 加载CSS
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
    document.head.appendChild(link)
    
    // 加载JS
    await new Promise((resolve) => {
      const script = document.createElement('script')
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
      script.onload = resolve
      document.head.appendChild(script)
    })
  }
  
  const L = window.L
  if (!L) {
    console.warn('Leaflet 未加载')
    return
  }
  
  // 初始化地图 - 中国中心
  map = L.map('map').setView([35.8617, 104.1954], 4)
  
  // 默认使用高德标准地图
  currentTileLayer = L.tileLayer(
    'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
    {
      subdomains: ['1', '2', '3', '4'],
      attribution: '© 高德地图',
      maxZoom: 18
    }
  ).addTo(map)
  
  // 加载地图数据
  await loadMapData()
}

const switchMapLayer = () => {
  const L = window.L
  if (!L || !map) return
  
  // 移除当前图层
  if (currentTileLayer) {
    map.removeLayer(currentTileLayer)
  }
  if (trafficLayer) {
    map.removeLayer(trafficLayer)
    trafficLayer = null
  }
  
  // 根据类型添加新图层
  switch (mapType.value) {
    case 'standard':
      currentTileLayer = L.tileLayer(
        'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
        { subdomains: ['1', '2', '3', '4'], attribution: '© 高德地图', maxZoom: 18 }
      ).addTo(map)
      break
    case 'traffic':
      // 使用高德实时路况地图样式
      currentTileLayer = L.tileLayer(
        'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
        { subdomains: ['1', '2', '3', '4'], attribution: '© 高德地图', maxZoom: 18 }
      ).addTo(map)
      // 路况图层使用替代方案
      trafficLayer = L.tileLayer(
        'https://wprd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&style=9&x={x}&y={y}&z={z}',
        { subdomains: ['1', '2', '3', '4'], maxZoom: 18 }
      ).addTo(map)
      break
    case 'satellite':
      currentTileLayer = L.tileLayer(
        'https://webst0{s}.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}',
        { subdomains: ['1', '2', '3', '4'], attribution: '© 高德地图', maxZoom: 18 }
      ).addTo(map)
      break
  }
}

const toggleTraffic = () => {
  const L = window.L
  if (!L || !map) return
  
  if (showTraffic.value && !trafficLayer) {
    // 使用高德 style=9 显示路况
    trafficLayer = L.tileLayer(
      'https://wprd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&style=9&x={x}&y={y}&z={z}',
      { subdomains: ['1', '2', '3', '4'], maxZoom: 18 }
    ).addTo(map)
  } else if (!showTraffic.value && trafficLayer) {
    map.removeLayer(trafficLayer)
    trafficLayer = null
  }
}

const loadMapData = async () => {
  try {
    // 获取节点数据
    const nodesRes = await getMapNodes()
    const L = window.L
    
    // 清除旧标记
    markers.forEach(m => map.removeLayer(m))
    markers = []
    
    // 添加节点标记
    nodesRes.features.forEach(feature => {
      const [lng, lat] = feature.geometry.coordinates
      const props = feature.properties
      
      const color = typeColors[props.type] || '#409EFF'
      
      const marker = L.circleMarker([lat, lng], {
        radius: 8,
        fillColor: color,
        color: '#fff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
      }).addTo(map)
      
      marker.bindPopup(`
        <b>${props.name}</b><br>
        类型: ${props.typeText}<br>
        地址: ${props.address || '-'}<br>
        联系人: ${props.contact || '-'}<br>
        电话: ${props.phone || '-'}
      `)
      
      // 点击标记时加载路况
      marker.on('click', () => loadNodeTraffic(props.id))
      
      markers.push(marker)
    })
    
    // 获取路线数据
    const routesRes = await getMapRoutes()
    
    // 清除旧路线
    routeLines.forEach(l => map.removeLayer(l))
    routeLines = []
    
    // 添加路线
    routesRes.features.forEach(feature => {
      const coords = feature.geometry.coordinates.map(c => [c[1], c[0]])
      const props = feature.properties
      
      const line = L.polyline(coords, {
        color: '#409EFF',
        weight: 3,
        opacity: 0.6
      }).addTo(map)
      
      line.bindPopup(`
        <b>${props.name}</b><br>
        距离: ${props.distance} km<br>
        时长: ${props.duration} h<br>
        成本: ${props.cost} 元
      `)
      
      routeLines.push(line)
    })
    
  } catch (error) {
    console.error('加载地图数据失败:', error)
  }
}

const loadNodeTraffic = async (nodeId) => {
  try {
    const res = await trafficAtNode(nodeId)
    if (res.success && res.data) {
      currentTraffic.value = res.data
    } else {
      // 服务不可用时不报错，只显示提示
      currentTraffic.value = {
        evaluation: '路况服务暂不可用',
        status: null,
        available: false
      }
    }
  } catch (error) {
    // 静默处理错误，不影响用户体验
    currentTraffic.value = {
      evaluation: '路况查询失败',
      status: null,
      available: false
    }
  }
}

const refreshTraffic = () => {
  if (routeForm.value.startNode) {
    loadNodeTraffic(routeForm.value.startNode)
  } else {
    ElMessage.info('请先选择一个节点')
  }
}

// 处理路况监控的路线变更
const handleRouteChange = (routeData) => {
  if (routeData.polyline) {
    drawAmapRoute(routeData.polyline)
    ElMessage.success(`已切换至${routeData.strategy}路线`)
  }
}

// 处理路况更新
const handleTrafficUpdate = (data) => {
  if (data.hasCongestion) {
    ElMessage.warning(`检测到${data.congestions.length}处拥堵路段`)
  }
}

const handleRecommend = async () => {
  if (!routeForm.value.startNode || !routeForm.value.endNode) {
    ElMessage.warning('请选择起点和终点')
    return
  }
  
  if (routeForm.value.startNode === routeForm.value.endNode) {
    ElMessage.warning('起点和终点不能相同')
    return
  }
  
  loading.value = true
  compareResult.value = null
  showTrafficPanel.value = false // 重置路况面板
  
  try {
    // 获取起点和终点的坐标
    const startNode = nodes.value.find(n => n.id === routeForm.value.startNode)
    const endNode = nodes.value.find(n => n.id === routeForm.value.endNode)
    
    if (startNode && endNode) {
      currentRouteCoords.value = {
        origin: `${startNode.longitude || startNode.lng},${startNode.latitude || startNode.lat}`,
        destination: `${endNode.longitude || endNode.lng},${endNode.latitude || endNode.lat}`
      }
    }
    
    if (useAmap.value) {
      // 使用高德地图 API
      const res = await drivingRoute({
        origin: routeForm.value.startNode,
        destination: routeForm.value.endNode,
        strategy: routeForm.value.strategy,
        show_traffic: true
      })
      
      if (res.success) {
        recommendResult.value = {
          ...res.data,
          source: 'amap'
        }
        ElMessage.success('高德地图路线规划成功！')
        
        // 在地图上绘制路线
        drawAmapRoute(res.data.polyline)
      } else {
        ElMessage.error(res.error || '规划失败')
      }
    } else {
      // 使用本地算法
      const res = await recommendRoute({
        start_node_id: routeForm.value.startNode,
        end_node_id: routeForm.value.endNode,
        optimize_by: routeForm.value.optimizeBy,
        algorithm: routeForm.value.algorithm
      })
      
      if (res.success) {
        recommendResult.value = {
          ...res,
          distance_km: res.total_distance,
          duration_minutes: res.total_time * 60,
          source: 'local'
        }
        ElMessage.success(`路线规划成功！使用 ${res.algorithm} 算法`)
        
        // 在地图上绘制路线
        highlightRoute(res.path)
      } else {
        ElMessage.error(res.error || '规划失败')
      }
    }
  } catch (error) {
    console.error('路线规划失败:', error)
    ElMessage.error('路线规划失败')
  } finally {
    loading.value = false
  }
}

const handleCompare = async () => {
  if (!routeForm.value.startNode || !routeForm.value.endNode) {
    ElMessage.warning('请选择起点和终点')
    return
  }
  
  compareLoading.value = true
  
  try {
    const res = await compareRoutes(routeForm.value.startNode, routeForm.value.endNode)
    
    if (res.success) {
      compareResult.value = res
      ElMessage.success('对比完成！')
    } else {
      ElMessage.error(res.error || '对比失败')
    }
  } catch (error) {
    console.error('对比失败:', error)
    ElMessage.error('对比失败')
  } finally {
    compareLoading.value = false
  }
}

const drawAmapRoute = (polyline) => {
  const L = window.L
  if (!L || !map || !polyline || polyline.length < 2) return
  
  // 清除之前的路线
  routeLines.forEach(l => map.removeLayer(l))
  routeLines = []
  
  // 转换坐标 [[lng, lat], ...] -> [[lat, lng], ...]
  const coords = polyline.map(p => [p[1], p[0]])
  
  // 绘制路线
  const line = L.polyline(coords, {
    color: '#409EFF',
    weight: 5,
    opacity: 0.8
  }).addTo(map)
  
  routeLines.push(line)
  
  // 添加起点终点标记
  const startMarker = L.circleMarker(coords[0], {
    radius: 10,
    fillColor: '#67C23A',
    color: '#fff',
    weight: 2,
    opacity: 1,
    fillOpacity: 1
  }).addTo(map)
  startMarker.bindPopup('起点')
  routeLines.push(startMarker)
  
  const endMarker = L.circleMarker(coords[coords.length - 1], {
    radius: 10,
    fillColor: '#F56C6C',
    color: '#fff',
    weight: 2,
    opacity: 1,
    fillOpacity: 1
  }).addTo(map)
  endMarker.bindPopup('终点')
  routeLines.push(endMarker)
  
  // 调整地图视野
  map.fitBounds(line.getBounds(), { padding: [50, 50] })
}

const highlightRoute = (path) => {
  const L = window.L
  if (!L || !map || !path || path.length < 2) return
  
  // 清除之前的高亮
  routeLines.forEach(l => map.removeLayer(l))
  routeLines = []
  
  // 绘制高亮路线
  const coords = path
    .filter(node => node && node.latitude && node.longitude)
    .map(node => [node.latitude, node.longitude])
  
  if (coords.length >= 2) {
    const line = L.polyline(coords, {
      color: '#F56C6C',
      weight: 5,
      opacity: 1
    }).addTo(map)
    
    routeLines.push(line)
    
    // 调整地图视野
    map.fitBounds(line.getBounds(), { padding: [50, 50] })
  }
}

// 天气加载完成回调
const onWeatherLoaded = (weatherData) => {
  currentWeather.value = weatherData
  
  // 如果有运输影响信息，显示提示
  if (weatherData.transport_impact) {
    const impact = weatherData.transport_impact
    
    // 根据影响等级显示不同提示
    if (impact.impact_level === '严重影响' || impact.impact_level === '极端影响，建议暂停运输') {
      ElMessage.warning(`⚠️ ${impact.impact_level}：${impact.safety_warning || '请注意运输安全'}`)
    } else if (impact.impact_level === '中度影响') {
      ElMessage.info(`🔶 天气对运输有中度影响，建议适当调整计划`)
    }
    
    // 如果路线规划结果已存在，重新计算考虑天气影响
    if (recommendResult.value) {
      applyWeatherToRoute(impact)
    }
  }
}

// 应用天气影响到路线规划结果
const applyWeatherToRoute = (impact) => {
  if (!recommendResult.value || !impact) return
  
  // 计算天气调整后的时间
  const originalTime = recommendResult.value.duration_minutes || recommendResult.value.total_time * 60
  const adjustedTime = originalTime * (1 + impact.delay_risk)
  
  // 计算天气调整后的速度
  const speedReduction = impact.speed_reduction || 0
  
  // 更新结果
  recommendResult.value = {
    ...recommendResult.value,
    weather_adjusted: true,
    original_duration_minutes: originalTime,
    adjusted_duration_minutes: Math.round(adjustedTime),
    delay_risk: impact.delay_risk,
    speed_reduction: speedReduction,
    weather_impact: impact.impact_level,
    weather_suggestions: impact.suggestions || []
  }
  
  ElMessage.success(`已根据天气调整预估时间：${Math.round(originalTime)}分钟 → ${Math.round(adjustedTime)}分钟`)
}

// 监听起点变化，加载路况
watch(() => routeForm.value.startNode, (newVal) => {
  if (newVal) {
    loadNodeTraffic(newVal)
  }
})
</script>

<style scoped>
.map-view {
  height: calc(100vh - 140px);
}

.map-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.map-container {
  width: 100%;
  height: calc(100vh - 260px);
  min-height: 500px;
  border-radius: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.recommend-result {
  margin-top: 10px;
}

.recommend-result h4 {
  margin-bottom: 10px;
  color: #303133;
}

.recommend-result h5 {
  margin: 10px 0 5px;
  color: #606266;
}

.traffic-status {
  margin-bottom: 10px;
}

.step-item {
  padding: 8px 0;
  border-bottom: 1px solid #eee;
  font-size: 13px;
}

.step-item:last-child {
  border-bottom: none;
}

.step-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.step-meta span {
  margin-right: 10px;
}

.compare-result h4 {
  margin-bottom: 10px;
  color: #303133;
}

.highlight {
  color: #67C23A;
  font-weight: bold;
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
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: inline-block;
}

.legend-line {
  width: 30px;
  height: 4px;
  border-radius: 2px;
  display: inline-block;
}

.traffic-info {
  text-align: center;
}

.weather-suggestions ul {
  list-style-type: disc;
}

.weather-suggestions li {
  margin: 3px 0;
}

/* 路况规避面板 */
.traffic-panel {
  position: absolute;
  bottom: 20px;
  left: 20px;
  right: 20px;
  max-width: 400px;
  z-index: 1000;
  background: rgba(10, 14, 39, 0.95);
  border-radius: 12px;
  backdrop-filter: blur(10px);
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
