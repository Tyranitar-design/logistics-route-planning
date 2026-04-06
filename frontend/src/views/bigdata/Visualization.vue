<template>
  <div class="vis-page">
    <div class="vis-header">
      <h2>🎨 数据可视化中心</h2>
    </div>

    <div class="vis-tabs">
      <div class="vis-tab" :class="{ active: cur === 'heatmap' }" @click="cur='heatmap'">🔥 中国地图热力图</div>
      <div class="vis-tab" :class="{ active: cur === 'network' }" @click="cur='network'">🕸️ 供应链网络</div>
      <div class="vis-tab" :class="{ active: cur === 'flow' }" @click="cur='flow'">⚡ 数据流动画</div>
      <div class="vis-tab" :class="{ active: cur === 'globe' }" @click="cur='globe'">🌍 3D地球</div>
    </div>

    <!-- 热力图面板 -->
    <div v-if="cur === 'heatmap'" class="heatmap-panel">
      <div class="action-bar">
        <el-button type="primary" @click="loadHeatmap" :loading="loading">🔄 加载订单数据</el-button>
        <el-select v-model="dataType" style="width: 140px" size="small">
          <el-option value="orders" label="订单分布" />
          <el-option value="cost" label="成本分布" />
          <el-option value="routes" label="路线密度" />
        </el-select>
      </div>

      <div v-if="mapData.length" class="map-box">
        <div class="map-chart" ref="mapRef"></div>
      </div>
      <div v-else-if="!loading" class="empty-hint">
        <p>🌍 点击「加载订单数据」查看全国订单热力分布</p>
      </div>

      <!-- 排行榜 -->
      <div v-if="topCities.length" class="top-list">
        <h4>📊 订单量 TOP 10 城市</h4>
        <div class="top-item" v-for="(city, i) in topCities" :key="i">
          <span class="top-rank" :class="i < 3 ? 'top' + i : ''">{{ i + 1 }}</span>
          <div class="top-bar-wrap">
            <span class="top-name">{{ city.name }}</span>
            <div class="top-bar"><div class="top-bar-fill" :style="{ width: city.pct + '%' }"></div></div>
          </div>
          <span class="top-val">{{ city.value }}</span>
        </div>
      </div>
    </div>

    <!-- 供应链网络面板 -->
    <div v-if="cur === 'network'" class="net-panel">
      <div class="action-bar">
        <el-button type="primary" @click="loadNetwork" :loading="netLoading">🕸️ 加载网络拓扑</el-button>
        <el-select v-model="netLayout" style="width: 120px" size="small">
          <el-option value="force" label="力导向" />
          <el-option value="circular" label="环形" />
        </el-select>
      </div>

      <div v-if="netNodes.length" class="map-box">
        <div class="net-chart" ref="netRef"></div>
      </div>
      <div v-else-if="!netLoading" class="empty-hint">
        <p>🕸️ 点击「加载网络拓扑」查看供应链关系</p>
      </div>

      <!-- 节点统计 -->
      <div v-if="netCategories.length" class="cat-row">
        <div class="cat-card" v-for="cat in netCategories" :key="cat.name">
          <span class="cat-dot" :style="{ background: cat.color }"></span>
          <span class="cat-name">{{ cat.name }}</span>
          <span class="cat-count">{{ cat.count }}</span>
        </div>
      </div>
    </div>

    <!-- 数据流动画面板 -->
    <div v-if="cur === 'flow'" class="flow-panel">
      <div class="action-bar">
        <el-button type="primary" @click="startFlow" :loading="flowLoading">⚡ 启动流动动画</el-button>
        <el-button v-if="flowRunning" @click="stopFlow">⏸️ 暂停</el-button>
        <el-select v-model="flowSpeed" style="width: 120px" size="small">
          <el-option value="slow" label="🐢 慢速" />
          <el-option value="normal" label="🚗 正常" />
          <el-option value="fast" label="🚀 快速" />
        </el-select>
        <span class="flow-status" v-if="flowRunning">🟢 运行中 · {{ flowPackets }} 个包</span>
      </div>
      <div class="map-box"><div class="flow-chart" ref="flowRef"></div></div>
      <div v-if="flowLogs.length" class="flow-log">
        <h4>📋 实时日志</h4>
        <div class="log-item" v-for="(log, i) in flowLogs.slice(-8).reverse()" :key="i">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-msg">{{ log.msg }}</span>
          <span>{{ log.status === 'success' ? '✅' : '⏳' }}</span>
        </div>
      </div>
    </div>

    <!-- 3D地球面板 -->
    <div v-if="cur === 'globe'" class="globe-panel">
      <div class="action-bar">
        <el-button type="primary" @click="loadGlobe" :loading="globeLoading">🌍 加载3D地球</el-button>
        <el-button v-if="globeAutoRotate !== undefined" @click="globeAutoRotate = !globeAutoRotate">
          {{ globeAutoRotate ? '⏸️ 停止旋转' : '🔄 自动旋转' }}
        </el-button>
      </div>
      <div class="map-box"><div class="globe-chart" ref="globeRef"></div></div>
      <div v-if="globeRoutes.length" class="globe-info">
        <h4>✈️ 活跃物流线路</h4>
        <div class="gr-item" v-for="(r, i) in globeRoutes" :key="i">
          <span class="gr-from">{{ r.from }}</span>
          <span class="gr-arrow">➡️</span>
          <span class="gr-to">{{ r.to }}</span>
          <span class="gr-count">{{ r.count }} 单</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

const cur = ref('heatmap')
const loading = ref(false)
const dataType = ref('orders')
const mapData = ref([])
const topCities = ref([])
const mapRef = ref(null)

// === 供应链网络 ===
const netLoading = ref(false)
const netLayout = ref('force')
const netNodes = ref([])
const netCategories = ref([])
const netRef = ref(null)

const catColors = { '总仓': '#00d4ff', '分仓': '#2ed573', '配送站': '#ffa502', '供应商': '#a29bfe', '客户': '#ff6b6b', '中转站': '#eccc68' }

function loadNetwork() {
  netLoading.value = true
  const types = ['总仓', '分仓', '配送站', '供应商', '客户', '中转站']
 const cities = ['北京', '上海', '广州', '深圳', '成都', '武汉', '杭州', '南京', '重庆', '西安', '长沙', '郑州', '沈阳', '哈尔滨', '昆明', '福州', '济南', '兰州']
  const nodes = cities.map((city, i) => ({
    name: city + types[i % types.length], type: types[i % types.length],
    symbolSize: 30 + Math.random() * 30, value: Math.floor(Math.random() * 80) + 20
  }))
  const links = []
  for (let i = 0; i < nodes.length; i++) {
    const count = 1 + Math.floor(Math.random() * 2)
    for (let j = 0; j < count; j++) {
      const target = (i + 1 + Math.floor(Math.random() * 3)) % nodes.length
      if (target !== i) links.push({ source: i, target, value: Math.floor(Math.random() * 40) + 10 })
    }
  }
  netNodes.value = nodes
  netCategories.value = types.map(t => ({ name: t, color: catColors[t] || '#888', count: nodes.filter(n => n.type === t).length }))
  nextTick(() => { if (netNodes.value.length) renderNetwork(nodes, links) })
  netLoading.value = false
}

function renderNetwork(nodes, links) {
  if (!netRef.value || !echarts) return
  const chart = echarts.init(netRef.value)
  const categories = Object.entries(catColors).map(([name, color]) => ({ name, itemStyle: { color } }))
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', backgroundColor: 'rgba(0,0,0,0.85)', borderColor: '#333', textStyle: { color: '#fff', fontSize: 13 } },
    legend: { data: categories.map(c => c.name), textStyle: { color: '#aaa' }, top: 5, orient: 'vertical', right: 10 },
    series: [{
      type: 'graph', layout: netLayout.value, roam: true, draggable: true,
      force: netLayout.value === 'force' ? { repulsion: 280, gravity: 0.04, edgeLength: [100, 250] } : undefined,
      circular: netLayout.value === 'circular' ? { rotateLabel: true } : undefined,
      categories,
      data: nodes.map((n, i) => ({ ...n, category: Object.keys(catColors).indexOf(n.type) >= 0 ? Object.keys(catColors).indexOf(n.type) : 0, label: { show: true, color: '#ccc', fontSize: 11 } })),
      links: links.map(l => ({ ...l, lineStyle: { color: 'rgba(0,212,255,0.15)', width: Math.max(1, (l.value || 10) / 20), curveness: 0.2 } })),
      emphasis: { focus: 'adjacency', lineStyle: { width: 4 } },
      animationDuration: 1200, animationEasingUpdate: 'quinticInOut'
    }]
  })
  window.addEventListener('resize', () => chart.resize())
}

// === 数据流动画 ===
const flowLoading = ref(false)
const flowRunning = ref(false)
const flowSpeed = ref('normal')
const flowPackets = ref(0)
const flowLogs = ref([])
const flowRef = ref(null)
let flowTimer = null
let flowChart = null

const speedMs = { slow: 3000, normal: 1500, fast: 600 }
const routes = [
  ['北京','上海'],['广州','成都'],['深圳','杭州'],['上海','武汉'],['成都','西安'],
  ['南京','重庆'],['武汉','长沙'],['杭州','福州'],['重庆','昆明'],['郑州','济南']
]

function startFlow() {
  if (flowRunning.value) return
  flowLoading.value = true
  flowRunning.value = true
  flowPackets.value = 0
  flowLogs.value = []
  nextTick(() => initFlowChart())
  flowLoading.value = false
  const tick = () => {
    const [from, to] = routes[Math.floor(Math.random() * routes.length)]
    flowPackets.value++
    const isFast = Math.random() > 0.3
    flowLogs.value.push({ time: new Date().toLocaleTimeString(), msg: `${from} → ${to}`, status: isFast ? 'success' : 'pending' })
    if (flowLogs.value.length > 50) flowLogs.value = flowLogs.value.slice(-30)
    if (flowChart) addFlowPacket(from, to)
    flowTimer = setTimeout(tick, speedMs[flowSpeed.value] + Math.random() * 500)
  }
  tick()
}

// === 3D地球 ===
const globeLoading = ref(false)
const globeAutoRotate = ref(true)
const globeRoutes = ref([])
const globeRef = ref(null)

const globeCityData = [
  { name: '北京', coord: [116.46, 39.92] },
  { name: '上海', coord: [121.48, 31.22] },
  { name: '广州', coord: [113.23, 23.16] },
  { name: '深圳', coord: [114.07, 22.62] },
  { name: '成都', coord: [104.06, 30.67] },
  { name: '武汉', coord: [114.31, 30.52] },
  { name: '杭州', coord: [120.19, 30.26] },
  { name: '西安', coord: [108.95, 34.27] },
  { name: '重庆', coord: [106.54, 29.59] },
  { name: '南京', coord: [118.78, 32.04] },
  { name: '长沙', coord: [112.94, 28.23] },
  { name: '郑州', coord: [113.65, 34.76] }
]

function loadGlobe() {
  globeLoading.value = true
  const pairs = []
  const routeMap = {}
  for (let i = 0; i < 15; i++) {
    const a = Math.floor(Math.random() * globeCityData.length)
    let b = (a + 1 + Math.floor(Math.random() * 4)) % globeCityData.length
    const from = globeCityData[a].name, to = globeCityData[b].name
    pairs.push({ from: globeCityData[a].coord, to: globeCityData[b].coord })
    const key = from + '→' + to
    routeMap[key] = (routeMap[key] || 0) + 1
  }
  globeRoutes.value = Object.entries(routeMap).map(([k, v]) => {
    const [f, t] = k.split('→')
    return { from: f, to: t, count: v }
  }).sort((a, b) => b.count - a.count).slice(0, 8)

  nextTick(() => {
    if (!globeRef.value || !echarts) return
    const chart = echarts.init(globeRef.value)
    chart.setOption({
      backgroundColor: 'transparent',
      geo: {
        map: 'china', roam: false, zoom: 1.15,
        itemStyle: { areaColor: '#0d1b2a', borderColor: '#1a4a6e', borderWidth: 0.8 },
        emphasis: { disabled: true }, label: { show: false },
        regions: globeCityData.map(c => ({
          name: c.name, itemStyle: { areaColor: '#0d1b2a' }
        }))
      },
      series: [
        {
          name: '城市', type: 'effectScatter', coordinateSystem: 'geo', zlevel: 2,
          symbol: 'circle', symbolSize: 8,
          rippleEffect: { brushType: 'stroke', scale: 4, period: 3 },
          data: globeCityData.map(c => ({ name: c.name, value: [...c.coord, 50] })),
          itemStyle: { color: '#00d4ff', shadowBlur: 15, shadowColor: 'rgba(0,212,255,0.5)' },
          label: { show: true, formatter: '{b}', position: 'right', color: '#aaa', fontSize: 11 }
        },
        {
          name: '物流线路', type: 'lines', coordinateSystem: 'geo', zlevel: 2,
          effect: { show: true, period: 4 + Math.random() * 2, trailLength: 0.5, symbol: 'arrow', symbolSize: 5, color: '#ffa502' },
          lineStyle: { width: 1, color: 'rgba(255,165,2,0.1)', curveness: 0.3 },
          data: pairs.map(p => ({ coords: [p.from, p.to] }))
        }
      ]
    })
    window.addEventListener('resize', () => chart.resize())
    ElMessage.success('3D地球加载完成！')
  })
  globeLoading.value = false
}

function stopFlow() { flowRunning.value = false; clearTimeout(flowTimer) }

function initFlowChart() {
  if (!flowRef.value || !echarts) return
  flowChart = echarts.init(flowRef.value)
  const allCities = [...new Set(routes.flat())]
  const positions = {}
  const r = 300
  allCities.forEach((city, i) => {
    const angle = (i / allCities.length) * Math.PI * 2
    positions[city] = [320 + Math.cos(angle) * r, 280 + Math.sin(angle) * r * 0.7]
  })
  flowChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { show: false },
    xAxis: { show: false, min: 0, max: 640 },
    yAxis: { show: false, min: 0, max: 560 },
    series: [
      { type: 'graph', layout: 'none', data: allCities.map(c => ({ name: c, x: positions[c][0], y: positions[c][1], symbolSize: 35, itemStyle: { color: '#00d4ff', shadowBlur: 15, shadowColor: 'rgba(0,212,255,0.4)' }, label: { show: true, color: '#ccc', fontSize: 12, formatter: '{b}' } })), silent: true },
      { type: 'lines', coordinateSystem: 'cartesian2d', polyline: false, effect: { show: true, period: 3, trailLength: 0.4, symbol: 'circle', symbolSize: 4, color: '#00d4ff' }, lineStyle: { width: 0 }, data: [] }
    ]
  })
  window.addEventListener('resize', () => flowChart?.resize())
}

function addFlowPacket(from, to) {
  if (!flowChart || !cityCoords[from] || !cityCoords[to]) return
  flowChart.setOption({ series: [{ id: 1, data: [{ coords: [cityCoords[from], cityCoords[to]] }] }] })
}

const cityCoords = {
  '北京':[116.46,39.92],'上海':[121.48,31.22],'广州':[113.23,23.16],'深圳':[114.07,22.62],
  '成都':[104.06,30.67],'杭州':[120.19,30.26],'武汉':[114.31,30.52],'南京':[118.78,32.04],
  '重庆':[106.54,29.59],'西安':[108.95,34.27],'天津':[117.2,39.13],'苏州':[120.62,31.32],
  '郑州':[113.65,34.76],'长沙':[112.94,28.23],'沈阳':[123.38,41.8],'哈尔滨':[126.63,45.75],
  '大连':[121.62,38.92],'昆明':[102.73,25.04],'福州':[119.3,26.08],'厦门':[118.1,24.46],
  '济南':[117.0,36.65],'青岛':[120.33,36.07],'合肥':[117.27,31.86],'南昌':[115.89,28.68],
  '石家庄':[114.48,38.03],'太原':[112.55,37.87],'贵阳':[106.71,26.57],'南宁':[108.33,22.84],
  '兰州':[103.73,36.03],'乌鲁木齐':[87.68,43.77],'拉萨':[91.11,29.97],'呼和浩特':[111.65,40.82]
}

function loadHeatmap() {
  loading.value = true
  // 模拟数据
  const cities = Object.keys(cityCoords)
  const raw = cities.map(name => ({
    name, value: Math.floor(Math.random() * 800) + 50, coord: cityCoords[name]
  })).sort((a, b) => b.value - a.value)

  mapData.value = raw
  const maxVal = raw[0].value
  topCities.value = raw.slice(0, 10).map(c => ({
    name: c.name, value: c.value, pct: Math.round(c.value / maxVal * 100)
  }))

  nextTick(() => { if (mapData.value.length) renderMap() })
  loading.value = false
}

function renderMap() {
  if (!mapRef.value || !echarts) { ElMessage.warning('ECharts未加载'); return }

  // 动态加载中国地图
  fetch('https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json')
    .then(r => r.json())
    .then(china => {
      echarts.registerMap('china', china)
      const chart = echarts.init(mapRef.value)
      const maxVal = Math.max(...mapData.value.map(d => d.value))

      chart.setOption({
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'item', backgroundColor: 'rgba(0,0,0,0.85)', borderColor: '#00d4ff',
          textStyle: { color: '#fff' },
          formatter: p => p.seriesType === 'map'
            ? `<b>${p.name}</b><br/>订单量：<span style="color:#ffa502;font-size:16px">${p.value || 0}</span>`
            : `${p.name}<br/>订单量：${p.value[2] || 0}`
        },
        visualMap: {
          min: 0, max: maxVal, left: 20, bottom: 20,
          text: ['高', '低'], textStyle: { color: '#aaa' },
          inRange: { color: ['#0a1628', '#0d2137', '#1a4a6e', '#2ed573', '#ffa502', '#ff4757'] },
          calculable: true
        },
        geo: {
          map: 'china', roam: true, zoom: 1.2,
          itemStyle: { areaColor: '#0d1b2a', borderColor: '#1b3a5c', borderWidth: 1 },
          emphasis: { itemStyle: { areaColor: '#1a3a5c', borderColor: '#00d4ff' } },
          label: { show: false }
        },
        series: [
          {
            name: '订单热力', type: 'map', map: 'china', geoIndex: 0,
            data: mapData.value.map(d => ({ name: d.name, value: d.value }))
          },
          {
            name: '重点城市', type: 'effectScatter', coordinateSystem: 'geo',
            data: mapData.value.slice(0, 15).map(d => ({ name: d.name, value: [...d.coord, d.value] })),
            symbolSize: val => Math.max(8, val[2] / 60),
            rippleEffect: { brushType: 'stroke', scale: 3, period: 4 },
            itemStyle: { color: '#ffa502', shadowBlur: 10, shadowColor: 'rgba(255,165,2,0.5)' },
            label: { show: true, formatter: '{b}', position: 'right', color: '#aaa', fontSize: 11 }
          },
          {
            name: '物流线路', type: 'lines', coordinateSystem: 'geo', zlevel: 2,
            effect: { show: true, period: 5, trailLength: 0.3, symbol: 'arrow', symbolSize: 5, color: '#00d4ff' },
            lineStyle: { color: 'rgba(0,212,255,0.15)', width: 1, curveness: 0.3 }
          }
        ]
      })
      window.addEventListener('resize', () => chart.resize())
      ElMessage.success('地图加载完成！')
    })
    .catch(() => {
      // 地图加载失败时用散点图兜底
      const chart = echarts.init(mapRef.value)
      chart.setOption({
        backgroundColor: 'transparent',
        tooltip: { backgroundColor: 'rgba(0,0,0,0.85)', textStyle: { color: '#fff' } },
        xAxis: { show: false, min: 100, max: 125 },
        yAxis: { show: false, min: 18, max: 50 },
        series: [{
          type: 'scatter', symbolSize: val => Math.max(10, val[2] / 50),
          data: mapData.value.map(d => ({ name: d.name, value: [...d.coord, d.value] })),
          itemStyle: { color: '#ffa502', shadowBlur: 15, shadowColor: 'rgba(255,165,2,0.4)' },
          label: { show: true, formatter: '{b}', position: 'right', color: '#aaa', fontSize: 11 }
        }]
      })
      window.addEventListener('resize', () => chart.resize())
    })
}
</script>

<style scoped>
.vis-page { padding: 24px; }
.vis-header h2 { color: #00d4ff; margin: 0 0 20px; font-size: 20px; }
.vis-tabs { display: flex; gap: 8px; margin-bottom: 24px; }
.vis-tab {
  padding: 10px 20px; background: rgba(0,0,0,0.2); border-radius: 10px;
  color: #888; font-size: 14px; cursor: pointer; border: 1px solid rgba(255,255,255,0.05);
  transition: all 0.3s;
}
.vis-tab.active { color: #00d4ff; background: rgba(0,212,255,0.08); border-color: rgba(0,212,255,0.3); font-weight: 600; }
.action-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }

.map-box { background: rgba(0,0,0,0.2); border-radius: 14px; padding: 16px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 20px; }
.map-chart { width: 100%; height: 520px; }

.empty-hint { text-align: center; padding: 120px 0; color: #555; font-size: 15px; }

.top-list { background: rgba(0,0,0,0.2); border-radius: 14px; padding: 20px; border: 1px solid rgba(255,255,255,0.05); }
.top-list h4 { color: #ffa502; margin: 0 0 14px; font-size: 15px; }
.top-item { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.top-rank {
  width: 24px; height: 24px; border-radius: 6px; display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; color: #888; background: rgba(255,255,255,0.06);
}
.top-rank.top0 { background: rgba(255,215,0,0.2); color: #ffd700; }
.top-rank.top1 { background: rgba(192,192,192,0.2); color: #c0c0c0; }
.top-rank.top2 { background: rgba(205,127,50,0.2); color: #cd7f32; }
.top-bar-wrap { flex: 1; display: flex; align-items: center; gap: 10px; }
.top-name { color: #ccc; font-size: 13px; width: 60px; flex-shrink: 0; }
.top-bar { flex: 1; height: 8px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; }
.top-bar-fill { height: 100%; background: linear-gradient(90deg, #00d4ff, #ffa502); border-radius: 4px; transition: width 0.6s ease; }
.top-val { color: #ffa502; font-size: 14px; font-weight: 700; width: 40px; text-align: right; }

/* 供应链网络 */
.net-chart { width: 100%; height: 500px; }
.cat-row { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; margin-top: 20px; }
.cat-card { display: flex; align-items: center; gap: 8px; background: rgba(0,0,0,0.15); padding: 12px 16px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.03); }
.cat-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.cat-name { color: #ccc; font-size: 13px; flex: 1; }
.cat-count { color: #00d4ff; font-size: 16px; font-weight: 700; }

/* 数据流动画 */
.flow-chart { width: 100%; height: 450px; }
.flow-status { color: #2ed573; font-size: 13px; }
.flow-log { background: rgba(0,0,0,0.2); border-radius: 14px; padding: 16px 20px; border: 1px solid rgba(255,255,255,0.05); margin-top: 16px; }
.flow-log h4 { color: #00d4ff; margin: 0 0 12px; }
.log-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.03); font-size: 13px; }
.log-time { color: #555; font-size: 12px; width: 80px; }
.log-msg { flex: 1; color: #ccc; }
.log-item:last-child { border-bottom: none; }

/* 3D地球 */
.globe-chart { width: 100%; height: 500px; }
.globe-info { background: rgba(0,0,0,0.2); border-radius: 14px; padding: 16px 20px; border: 1px solid rgba(255,255,255,0.05); margin-top: 16px; }
.globe-info h4 { color: #ffa502; margin: 0 0 12px; }
.gr-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.03); font-size: 13px; }
.gr-item:last-child { border-bottom: none; }
.gr-from { color: #00d4ff; width: 60px; }
.gr-arrow { color: #555; }
.gr-to { color: #2ed573; width: 60px; }
.gr-count { margin-left: auto; color: #ffa502; font-weight: 700; }

.coming-soon { text-align: center; padding: 80px 0; }
.cs-icon { font-size: 48px; margin-bottom: 16px; }
.coming-soon h3 { color: #888; margin-bottom: 8px; }
.coming-soon p { color: #555; font-size: 14px; }
</style>
