<template>
  <div class="replay-shell">
    <div class="replay-toolbar">
      <div class="engine-badge" :class="engine">
        <span>{{ engineLabel }}</span>
        <strong>{{ truth.authenticity_level || '-' }}</strong>
      </div>
      <el-radio-group v-model="layerMode" size="small" @change="syncLayers">
        <el-radio-button value="road">路网</el-radio-button>
        <el-radio-button value="satellite">卫星</el-radio-button>
        <el-radio-button value="traffic">交通</el-radio-button>
      </el-radio-group>
      <el-button-group>
        <el-button size="small" type="primary" :disabled="!canReplay" @click="play">{{ playing ? '播放中' : '播放' }}</el-button>
        <el-button size="small" :disabled="!canReplay || !playing" @click="pause">暂停</el-button>
        <el-button size="small" :disabled="!frameCount" @click="reset">重置</el-button>
      </el-button-group>
      <el-select v-model="speed" size="small" class="speed-select" @change="restartIfPlaying">
        <el-option label="0.7x" :value="0.7" />
        <el-option label="1x" :value="1" />
        <el-option label="1.5x" :value="1.5" />
        <el-option label="2x" :value="2" />
      </el-select>
      <span class="fallback-text">{{ truth.fallback_reason || 'REAL_PROVIDER_OK' }}</span>
    </div>

    <div class="replay-grid">
      <div class="map-wrap">
        <div ref="mapRef" class="amap-canvas"></div>
        <div v-if="mapError" class="map-error">
          <strong>地图 Provider 降级</strong>
          <span>{{ mapError }}</span>
        </div>
      </div>
      <aside class="telemetry-panel">
        <div class="telemetry-card accent">
          <span>当前路线</span>
          <strong>{{ activeFrame?.route_id || '-' }}</strong>
          <small>{{ activeFrame?.customer || '等待播放' }}</small>
        </div>
        <div class="telemetry-row">
          <div><span>进度</span><strong>{{ Math.round((activeFrame?.progress || 0) * 100) }}%</strong></div>
          <div><span>累计距离</span><strong>{{ activeFrame?.distance_km || 0 }} km</strong></div>
        </div>
        <div class="telemetry-row">
          <div><span>已用时</span><strong>{{ activeFrame?.elapsed_min || 0 }} min</strong></div>
          <div><span>鲜度</span><strong>{{ freshnessPercent }}%</strong></div>
        </div>
        <div class="freshness-meter">
          <span :style="{ width: freshnessPercent + '%' }"></span>
        </div>
        <div ref="freshnessRef" class="freshness-chart"></div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { loadMapEngine } from '@/utils/amapLoader'

const props = defineProps({
  result: { type: Object, default: null },
  network: { type: Object, default: null },
})

const mapRef = ref(null)
const freshnessRef = ref(null)
const engine = ref('pending')
const layerMode = ref('road')
const speed = ref(1)
const mapError = ref('')
const activeFrame = ref(null)
const frameCursor = ref(0)
const playing = ref(false)

let engineHandle = null
let amap = null
let leafletMap = null
let movingMarker = null
let freshnessChart = null
let replayTimer = null
let satelliteLayer = null
let trafficLayer = null
let routeOverlays = []
let staticMarkers = []

const truth = computed(() => ({
  distance_source: props.result?.animation?.distance_source || props.result?.distance_source,
  path_source: props.result?.animation?.path_source || props.result?.path_source,
  authenticity_level: props.result?.animation?.authenticity_level || props.result?.authenticity_level,
  fallback_reason: props.result?.animation?.fallback_reason || props.result?.fallback_reason,
}))

const replayRoutes = computed(() => props.result?.animation?.routes || [])
const frameCount = computed(() => flatFrames.value.length)
const canReplay = computed(() => frameCount.value > 1)
const engineLabel = computed(() => {
  if (engine.value === 'amap') return 'AMap JS API'
  if (engine.value === 'leaflet') return 'Leaflet fallback'
  if (engine.value === 'failed') return 'Map failed'
  return 'Map loading'
})
const freshnessPercent = computed(() => Math.round((activeFrame.value?.freshness_score ?? 0) * 100))

const flatFrames = computed(() => {
  const rows = []
  replayRoutes.value.forEach((route, routeIndex) => {
    ;(route.frames || []).forEach((frame) => {
      rows.push({
        ...frame,
        route_index: routeIndex,
        route_id: route.route_id,
        customer: route.customer,
        color: route.color,
      })
    })
  })
  return rows
})

function clearTimer() {
  if (replayTimer) {
    clearInterval(replayTimer)
    replayTimer = null
  }
}

function clearMapObjects() {
  routeOverlays.forEach((item) => {
    try {
      if (item?.setMap) item.setMap(null)
      else if (item?.remove) item.remove()
    } catch (e) {}
  })
  staticMarkers.forEach((item) => {
    try {
      if (item?.setMap) item.setMap(null)
      else if (item?.remove) item.remove()
    } catch (e) {}
  })
  routeOverlays = []
  staticMarkers = []
  movingMarker = null
}

function destroyMap() {
  clearTimer()
  clearMapObjects()
  if (freshnessChart) {
    freshnessChart.dispose()
    freshnessChart = null
  }
  if (leafletMap) {
    leafletMap.remove()
    leafletMap = null
  }
  if (amap) {
    amap.destroy()
    amap = null
  }
}

function pointArray(point) {
  return [Number(point.lon), Number(point.lat)]
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function markerHtml(color, label, size = 12) {
  return `<div style="width:${size}px;height:${size}px;border-radius:999px;background:${color};border:2px solid rgba(255,255,255,.9);box-shadow:0 0 18px ${color};"></div><span style="display:block;margin-top:2px;white-space:nowrap;color:#dff7ff;text-shadow:0 1px 4px #001;font-size:10px;">${escapeHtml(label)}</span>`
}

function vehicleHtml(color = '#5eead4') {
  return `<div style="width:20px;height:20px;border-radius:6px;background:linear-gradient(135deg,#fff,${color});border:2px solid #07111f;box-shadow:0 0 22px ${color};transform:rotate(45deg);"></div>`
}

async function render() {
  await nextTick()
  if (!mapRef.value || !props.result) return
  const shouldResume = playing.value
  destroyMap()
  mapError.value = ''
  activeFrame.value = flatFrames.value[0] || null
  frameCursor.value = 0

  try {
    engineHandle = await loadMapEngine()
    engine.value = engineHandle.engine
    if (engineHandle.engine === 'amap') renderAmap(engineHandle.AMap)
    else renderLeaflet(engineHandle.L, engineHandle.amapError)
    renderFreshnessChart()
    stepTo(0)
    if (shouldResume) play()
  } catch (e) {
    engine.value = 'failed'
    mapError.value = e.message || 'MAP_ENGINE_UNAVAILABLE'
    renderFreshnessChart()
  }
}

function addAmapNodeMarkers(AMap) {
  const nodes = props.network?.nodes || []
  const colorMap = { orchard: '#52c41a', facility: '#1890ff', b_store: '#faad14', origin_airport: '#722ed1', freight_airport: '#eb2f96' }
  nodes.filter((n) => n.lon && n.lat).slice(0, 120).forEach((node) => {
    const marker = new AMap.Marker({
      map: amap,
      position: [Number(node.lon), Number(node.lat)],
      title: node.name,
      offset: new AMap.Pixel(-8, -8),
      content: markerHtml(colorMap[node.node_type] || '#94a3b8', ['facility', 'orchard'].includes(node.node_type) ? node.name : '', node.node_type === 'facility' ? 16 : 10),
    })
    staticMarkers.push(marker)
  })
}

function renderAmap(AMap) {
  amap = new AMap.Map(mapRef.value, {
    center: [117.5, 32],
    zoom: 6,
    pitch: 46,
    rotation: -8,
    viewMode: '3D',
    mapStyle: 'amap://styles/darkblue',
  })
  try {
    amap.addControl(new AMap.Scale())
    amap.addControl(new AMap.ToolBar({ position: { top: '16px', right: '16px' } }))
    amap.addControl(new AMap.ControlBar({ position: { top: '72px', right: '16px' } }))
  } catch (e) {}
  satelliteLayer = new AMap.TileLayer.Satellite()
  trafficLayer = new AMap.TileLayer.Traffic({ autoRefresh: true, interval: 180 })
  syncLayers()
  addAmapNodeMarkers(AMap)

  const fitItems = []
  replayRoutes.value.forEach((route) => {
    const points = route.route_geometry?.polyline || []
    if (points.length < 2) return
    const path = points.map(pointArray)
    const line = new AMap.Polyline({
      path,
      strokeColor: route.color || '#5eead4',
      strokeOpacity: 0.92,
      strokeWeight: 6,
      strokeStyle: 'solid',
      lineJoin: 'round',
      lineCap: 'round',
      zIndex: 80,
    })
    line.setMap(amap)
    routeOverlays.push(line)
    fitItems.push(line)
  })
  const first = flatFrames.value[0]
  if (first) {
    movingMarker = new AMap.Marker({
      map: amap,
      position: [first.lon, first.lat],
      offset: new AMap.Pixel(-10, -10),
      content: vehicleHtml(first.color),
      zIndex: 120,
    })
    staticMarkers.push(movingMarker)
  }
  if (fitItems.length) amap.setFitView(fitItems, false, [70, 70, 70, 70], 8)
}

function renderLeaflet(L, amapError) {
  mapError.value = amapError ? `AMap 降级：${amapError}` : ''
  leafletMap = L.map(mapRef.value).setView([32, 117.5], 5)
  L.tileLayer('https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}', {
    subdomains: ['1', '2', '3', '4'],
    attribution: '© 高德瓦片 / Leaflet fallback',
    maxZoom: 18,
  }).addTo(leafletMap)

  const bounds = []
  replayRoutes.value.forEach((route) => {
    const latLngs = (route.route_geometry?.polyline || []).map((p) => [p.lat, p.lon])
    if (latLngs.length < 2) return
    const line = L.polyline(latLngs, { color: route.color || '#5eead4', weight: 4, opacity: 0.88 }).addTo(leafletMap)
    routeOverlays.push(line)
    latLngs.forEach((p) => bounds.push(p))
  })
  const first = flatFrames.value[0]
  if (first) {
    movingMarker = L.marker([first.lat, first.lon], {
      icon: L.divIcon({ className: 'vehicle-div-icon', html: vehicleHtml(first.color), iconSize: [22, 22], iconAnchor: [11, 11] }),
    }).addTo(leafletMap)
    staticMarkers.push(movingMarker)
  }
  if (bounds.length) leafletMap.fitBounds(bounds, { padding: [70, 70] })
}

function syncLayers() {
  if (!amap || engine.value !== 'amap') return
  if (satelliteLayer) satelliteLayer.setMap(layerMode.value === 'satellite' ? amap : null)
  if (trafficLayer) trafficLayer.setMap(layerMode.value === 'traffic' ? amap : null)
}

function renderFreshnessChart() {
  if (!freshnessRef.value) return
  if (freshnessChart) freshnessChart.dispose()
  freshnessChart = echarts.init(freshnessRef.value)
  const firstRoute = replayRoutes.value[0]
  const data = (firstRoute?.freshness_timeline || []).map((p) => [p.elapsed_min, Math.round((p.freshness_score || 0) * 100)])
  freshnessChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', formatter: (params) => `${params[0].axisValue} min<br/>鲜度 ${params[0].data[1]}%` },
    grid: { left: 34, right: 12, top: 18, bottom: 26 },
    xAxis: { type: 'value', axisLabel: { color: '#7a8fb0', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(120,200,255,.08)' } } },
    yAxis: { type: 'value', min: 0, max: 100, axisLabel: { color: '#7a8fb0', fontSize: 10, formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(120,200,255,.08)' } } },
    series: [{
      name: '鲜度',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 5,
      data,
      lineStyle: { color: '#5eead4', width: 3 },
      itemStyle: { color: '#5eead4' },
      areaStyle: { color: 'rgba(94,234,212,.14)' },
    }],
  })
}

function updateFreshnessCursor(frame) {
  if (!freshnessChart || !frame) return
  const route = replayRoutes.value[frame.route_index]
  const data = (route?.freshness_timeline || []).map((p) => [p.elapsed_min, Math.round((p.freshness_score || 0) * 100)])
  freshnessChart.setOption({
    series: [{
      data,
      markLine: {
        symbol: 'none',
        label: { color: '#cfe5ff', formatter: '当前' },
        lineStyle: { color: '#fbbf24', width: 2, type: 'dashed' },
        data: [{ xAxis: frame.elapsed_min }],
      },
    }],
  })
}

function stepTo(index) {
  const frames = flatFrames.value
  if (!frames.length) return
  const nextIndex = Math.max(0, Math.min(index, frames.length - 1))
  const frame = frames[nextIndex]
  frameCursor.value = nextIndex
  activeFrame.value = frame
  if (engine.value === 'amap' && movingMarker) {
    movingMarker.setPosition([frame.lon, frame.lat])
    if (movingMarker.setContent) movingMarker.setContent(vehicleHtml(frame.color))
  } else if (engine.value === 'leaflet' && movingMarker) {
    movingMarker.setLatLng([frame.lat, frame.lon])
  }
  updateFreshnessCursor(frame)
}

function play() {
  if (!canReplay.value) return
  if (frameCursor.value >= frameCount.value - 1) stepTo(0)
  clearTimer()
  playing.value = true
  const interval = Math.max(80, Math.round((props.result?.animation?.replay_interval_ms || 420) / Number(speed.value || 1)))
  stepTo(frameCursor.value + 1)
  replayTimer = setInterval(() => {
    if (frameCursor.value >= frameCount.value - 1) {
      pause()
      return
    }
    stepTo(frameCursor.value + 1)
  }, interval)
}

function pause() {
  playing.value = false
  clearTimer()
}

function reset() {
  pause()
  stepTo(0)
}

function playFromStart() {
  reset()
  play()
}

function restartIfPlaying() {
  if (playing.value) play()
}

watch(() => props.result, render, { immediate: true })

onBeforeUnmount(destroyMap)

defineExpose({ play, pause, reset, playFromStart })
</script>

<style scoped>
.replay-shell { display: flex; flex-direction: column; gap: 12px; }
.replay-toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.engine-badge { display: inline-flex; align-items: center; gap: 8px; min-width: 132px; padding: 6px 10px; border-radius: 8px; border: 1px solid rgba(120,200,255,.16); background: rgba(7,17,31,.72); color: #9bb3d4; font-size: 12px; }
.engine-badge strong { color: #5eead4; font-size: 14px; }
.engine-badge.leaflet strong,
.engine-badge.failed strong { color: #fbbf24; }
.speed-select { width: 86px; }
.fallback-text { color: #7a8fb0; font-size: 12px; max-width: 520px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.replay-grid { display: grid; grid-template-columns: minmax(0, 1fr) 310px; gap: 14px; align-items: stretch; }
.map-wrap { position: relative; min-height: 520px; border-radius: 10px; overflow: hidden; border: 1px solid rgba(120,200,255,.14); background: #07111f; }
.amap-canvas { height: 100%; min-height: 520px; width: 100%; }
.map-error { position: absolute; left: 16px; top: 16px; display: flex; flex-direction: column; gap: 3px; max-width: 360px; padding: 10px 12px; border: 1px solid rgba(251,191,36,.35); border-radius: 8px; background: rgba(33,24,7,.82); color: #fef3c7; font-size: 12px; z-index: 10; }
.telemetry-panel { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.telemetry-card,
.telemetry-row > div { border: 1px solid rgba(120,200,255,.14); border-radius: 10px; background: rgba(7,17,31,.72); padding: 12px; }
.telemetry-card { display: flex; flex-direction: column; gap: 4px; }
.telemetry-card.accent { box-shadow: inset 2px 0 0 #5eead4; }
.telemetry-card span,
.telemetry-row span { display: block; color: #7a8fb0; font-size: 11px; margin-bottom: 4px; }
.telemetry-card strong { color: #cfe5ff; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.telemetry-card small { color: #5eead4; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.telemetry-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.telemetry-row strong { color: #5eead4; font-size: 18px; }
.freshness-meter { height: 10px; border-radius: 999px; overflow: hidden; background: rgba(120,200,255,.08); border: 1px solid rgba(120,200,255,.12); }
.freshness-meter span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #f97316, #fbbf24, #5eead4); transition: width .24s ease; }
.freshness-chart { height: 230px; width: 100%; border: 1px solid rgba(120,200,255,.12); border-radius: 10px; background: rgba(7,17,31,.58); }
:deep(.amap-logo),
:deep(.amap-copyright) { opacity: .72; }

@media (max-width: 1180px) {
  .replay-grid { grid-template-columns: 1fr; }
  .telemetry-panel { grid-template-columns: repeat(2, minmax(0, 1fr)); display: grid; }
  .freshness-chart { grid-column: 1 / -1; }
}

@media (max-width: 720px) {
  .map-wrap,
  .amap-canvas { min-height: 420px; }
  .telemetry-panel,
  .telemetry-row { grid-template-columns: 1fr; }
  .fallback-text { white-space: normal; }
}
</style>
