<template>
  <div class="case-page">
    <header class="page-hero">
      <h1>🗺️ GIS 地理 & 网络拓扑</h1>
      <p>果园/仓/门店/机场/C端聚类真实地理分布 + 物流网络图</p>
      <div class="hero-actions">
        <el-button size="small" :loading="loading" @click="load">刷新</el-button>
      </div>
    </header>
    <div class="kpi-grid">
      <div class="kpi-card"><span>节点</span><strong>{{ network?.summary?.node_count || 0 }}</strong></div>
      <div class="kpi-card"><span>边</span><strong>{{ network?.summary?.edge_count || 0 }}</strong></div>
      <div class="kpi-card"><span>果园</span><strong>{{ network?.summary?.orchard_count || 0 }}</strong></div>
      <div class="kpi-card"><span>仓库</span><strong>{{ network?.summary?.facility_count || 0 }}</strong></div>
      <div class="kpi-card"><span>门店</span><strong>{{ network?.summary?.b_store_count || 0 }}</strong></div>
      <div class="kpi-card"><span>真实性</span><strong>{{ network?.authenticity_level || '-' }}</strong></div>
    </div>
    <section class="panel">
      <div class="panel-title"><h2>🌐 地理地图</h2>
        <div class="legend">
          <span class="provider-pill">{{ mapProviderLabel }}</span>
          <span class="legend-item"><i class="dot" style="background:#52c41a"></i>果园</span>
          <span class="legend-item"><i class="dot" style="background:#1890ff"></i>仓</span>
          <span class="legend-item"><i class="dot" style="background:#faad14"></i>门店</span>
          <span class="legend-item"><i class="dot" style="background:#722ed1"></i>机场</span>
          <span class="legend-item"><i class="dot" style="background:#13c2c2"></i>C端聚类</span>
        </div>
      </div>
      <div id="case-gis-map" class="gis-map"></div>
    </section>
    <section class="panel">
      <h2>🔗 物流网络拓扑（ECharts graph）</h2>
      <div ref="graphRef" class="gis-graph"></div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getFoodSupplyNetwork, getFoodSupplyC2cClusters } from '@/api/foodSupplyCase'
import { loadMapEngine } from '@/utils/amapLoader'

const network = ref(null)
const clusters = ref(null)
const loading = ref(false)
const graphRef = ref(null)
const mapProvider = ref('pending')
const mapProviderReason = ref('')
let caseMap = null
let caseMapEngine = null
let caseMapOverlays = []

const mapProviderLabel = computed(() => {
  if (mapProvider.value === 'amap') return 'AMap JS API'
  if (mapProvider.value === 'leaflet') return `Leaflet 降级${mapProviderReason.value ? ': ' + mapProviderReason.value : ''}`
  return '地图加载中'
})

function clearCaseMap() {
  caseMapOverlays.forEach((item) => {
    try {
      if (item?.setMap) item.setMap(null)
      else if (item?.remove) item.remove()
    } catch (e) {}
  })
  caseMapOverlays = []
  if (caseMap) {
    try {
      if (caseMapEngine === 'amap') caseMap.destroy()
      else caseMap.remove()
    } catch (e) {}
  }
  caseMap = null
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function markerContent(color, label, size = 11) {
  return `<div style="display:flex;align-items:center;gap:4px;"><i style="display:inline-block;width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 0 16px ${color};"></i><span style="color:#dff7ff;font-size:10px;text-shadow:0 1px 4px #001;white-space:nowrap;">${escapeHtml(label)}</span></div>`
}

async function loadMap() {
  try {
    const el = document.getElementById('case-gis-map')
    if (!el) return
    clearCaseMap()
    const engine = await loadMapEngine()
    mapProvider.value = engine.engine
    mapProviderReason.value = engine.amapError || ''
    const c = { orchard: '#52c41a', facility: '#1890ff', b_store: '#faad14', origin_airport: '#722ed1', freight_airport: '#eb2f96' }
    const bounds = []
    if (engine.engine === 'amap') {
      const AMap = engine.AMap
      caseMapEngine = 'amap'
      caseMap = new AMap.Map(el, { center: [117.5, 32], zoom: 5, pitch: 42, viewMode: '3D', mapStyle: 'amap://styles/darkblue' })
      try {
        caseMap.addControl(new AMap.Scale())
        caseMap.addControl(new AMap.ToolBar({ position: { top: '16px', right: '16px' } }))
        caseMap.addControl(new AMap.MapType({ defaultType: 0, showRoad: true }))
        const traffic = new AMap.TileLayer.Traffic({ autoRefresh: true, interval: 180 })
        traffic.setMap(caseMap)
        caseMapOverlays.push(traffic)
      } catch (e) {}
      ;(network.value?.nodes || []).forEach(n => {
        if (!n.lon || !n.lat) return
        const marker = new AMap.Marker({
          map: caseMap,
          position: [Number(n.lon), Number(n.lat)],
          title: n.name,
          offset: new AMap.Pixel(-8, -8),
          content: markerContent(c[n.node_type] || '#999', ['orchard', 'facility'].includes(n.node_type) ? n.name : '', n.node_type === 'facility' ? 15 : 10),
        })
        caseMapOverlays.push(marker)
        bounds.push(marker)
      })
      ;(clusters.value?.clusters || []).forEach(cl => {
        if (!cl.lon || !cl.lat) return
        const marker = new AMap.Marker({
          map: caseMap,
          position: [Number(cl.lon), Number(cl.lat)],
          title: cl.region,
          offset: new AMap.Pixel(-8, -8),
          content: markerContent('#13c2c2', `${cl.region || ''} ${cl.orders || 0}单`, 13),
        })
        caseMapOverlays.push(marker)
        bounds.push(marker)
      })
      if (bounds.length) caseMap.setFitView(bounds, false, [70, 70, 70, 70], 6)
    } else {
      const L = engine.L
      caseMapEngine = 'leaflet'
      if (el._leaflet_id) el._leaflet_id = null
      caseMap = L.map('case-gis-map').setView([32, 117.5], 5)
      L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', { subdomains: ['1', '2', '3', '4'], attribution: '© 高德瓦片 / Leaflet fallback', maxZoom: 18 }).addTo(caseMap)
      ;(network.value?.nodes || []).forEach(n => {
        if (!n.lon || !n.lat) return
        const marker = L.circleMarker([n.lat, n.lon], { radius: 5, color: c[n.node_type] || '#999', fillColor: c[n.node_type] || '#999', fillOpacity: 0.85 }).addTo(caseMap).bindPopup(`<b>${n.node_type}</b><br/>${n.name}`)
        caseMapOverlays.push(marker)
      })
      ;(clusters.value?.clusters || []).forEach(cl => {
        if (!cl.lon || !cl.lat) return
        const marker = L.circleMarker([cl.lat, cl.lon], { radius: 7, color: '#13c2c2', fillColor: '#13c2c2', fillOpacity: 0.6 }).addTo(caseMap).bindPopup(`<b>C端聚类</b><br/>${cl.region}<br/>${cl.orders} 单`)
        caseMapOverlays.push(marker)
      })
    }
  } catch (e) {
    mapProvider.value = 'failed'
    mapProviderReason.value = e.message || 'MAP_ENGINE_UNAVAILABLE'
    ElMessage.error('地图加载失败：' + mapProviderReason.value)
  }
}

function renderGraph() {
  if (!graphRef.value || !network.value) return
  const chart = echarts.init(graphRef.value)
  const colorMap = { orchard: '#52c41a', facility: '#1890ff', b_store: '#faad14', origin_airport: '#722ed1', freight_airport: '#eb2f96' }
  const cats = ['orchard', 'facility', 'b_store', 'origin_airport', 'freight_airport']
  const nodes = (network.value.nodes || []).filter(n => n.node_code).slice(0, 120).map(n => ({
    id: n.node_code, name: n.name, category: cats.indexOf(n.node_type) >= 0 ? n.node_type : 'b_store',
    symbolSize: n.node_type === 'facility' ? 28 : (n.node_type === 'orchard' ? 22 : 12),
    itemStyle: { color: colorMap[n.node_type] || '#999' },
  }))
  const nodeIds = new Set(nodes.map(n => n.id))
  const links = (network.value.edges || []).slice(0, 150).filter(e => nodeIds.has(e.source) && nodeIds.has(e.target)).map(e => ({ source: e.source, target: e.target }))
  chart.setOption({
    tooltip: { trigger: 'item', formatter: (p) => p.dataType === 'node' ? `${p.data.category}: ${p.data.name}` : `${p.data.source} → ${p.data.target}` },
    legend: { data: cats, textStyle: { color: '#aac', fontSize: 11 }, top: 0, orient: 'horizontal', left: 'center' },
    series: [{
      type: 'graph', layout: 'force', roam: true, width: '100%', height: '92%',
      force: { repulsion: 140, edgeLength: [60, 120], gravity: 0.08, layoutAnimation: true },
      categories: cats.map(name => ({ name })),
      data: nodes, links,
      lineStyle: { color: '#445', opacity: 0.4, width: 1.5, curveness: 0.1 },
      label: { show: true, position: 'right', color: '#cfe5ff', fontSize: 10, formatter: (p) => ['facility', 'orchard'].includes(p.data.category) ? p.data.name : '' },
      emphasis: { focus: 'adjacency', lineStyle: { width: 3, color: '#5eead4' }, label: { fontSize: 12, color: '#5eead4' } },
      scaleLimit: { min: 0.5, max: 3 },
    }],
  })
}

async function load() {
  loading.value = true
  try {
    const [net, cl] = await Promise.all([getFoodSupplyNetwork(), getFoodSupplyC2cClusters({ cluster_limit: 30 })])
    network.value = net; clusters.value = cl
    await loadMap(); renderGraph()
  } catch (e) { ElMessage.error('GIS 加载失败：' + (e.message || '后端未启动')) }
  finally { loading.value = false }
}
onMounted(load)
onBeforeUnmount(clearCaseMap)
</script>

<style scoped>
.case-page { color: #e6f0ff; }
.page-hero { margin-bottom: 18px; }
.page-hero h1 { margin: 0 0 4px; font-size: 22px; color: #a8d8ff; }
.page-hero p { margin: 0 0 10px; color: #7a8fb0; font-size: 13px; }
.hero-actions { display: flex; gap: 12px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 12px; margin-bottom: 18px; }
.kpi-card { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 12px; display: flex; flex-direction: column; gap: 4px; }
.kpi-card span { font-size: 11px; color: #7a8fb0; }
.kpi-card strong { font-size: 20px; color: #5eead4; }
.panel { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.panel-title { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.panel h2 { margin: 0; font-size: 15px; color: #a8d8ff; }
.legend { display: flex; gap: 12px; flex-wrap: wrap; }
.provider-pill { display: inline-flex; align-items: center; min-height: 22px; padding: 3px 8px; border-radius: 999px; border: 1px solid rgba(94,234,212,0.25); background: rgba(94,234,212,0.08); color: #5eead4; font-size: 11px; }
.legend-item { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: #9bb3d4; }
.legend-item .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
.gis-map { height: 440px; width: 100%; border-radius: 8px; overflow: hidden; border: 1px solid rgba(120,200,255,0.12); }
.gis-graph { height: 380px; width: 100%; }
</style>
