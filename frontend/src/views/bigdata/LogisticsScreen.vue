<template>
  <div class="logistics-screen-pro">
    <!-- 背景粒子 -->
    <canvas ref="particleCanvas" class="particle-bg"></canvas>
    
    <!-- 顶部标题 -->
    <div class="screen-header">
      <div class="header-decoration left"></div>
      <h1 class="main-title">
        <span class="title-icon">🚚</span>
        物流路径规划系统 - 大数据可视化平台
        <span class="title-icon">📦</span>
      </h1>
      <div class="header-decoration right"></div>
      <div class="header-info">
        <span class="time">{{ currentTime }}</span>
        <el-button type="primary" size="small" @click="goBack">返回系统</el-button>
      </div>
    </div>

    <!-- 主体内容 -->
    <div class="screen-body">
      <!-- 左侧面板 -->
      <div class="panel-left">
        <!-- 核心指标 -->
        <div class="panel-item core-metrics">
          <div class="panel-title">
            <span class="title-deco"></span>
            核心指标
          </div>
          <div class="metrics-grid">
            <div class="metric-card pulse" v-for="(m, i) in coreMetrics" :key="i" :style="{ animationDelay: i * 0.1 + 's' }">
              <div class="metric-icon">{{ m.icon }}</div>
              <div class="metric-info">
                <div class="metric-value">
                  <span class="number" :data-value="m.value">{{ animatedValues[i] || 0 }}</span>
                  <span class="unit">{{ m.unit }}</span>
                </div>
                <div class="metric-label">{{ m.label }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 订单趋势 -->
        <div class="panel-item">
          <div class="panel-title">
            <span class="title-deco"></span>
            订单趋势分析
          </div>
          <div ref="orderTrendChart" class="chart-container"></div>
        </div>

        <!-- 车辆监控 -->
        <div class="panel-item">
          <div class="panel-title">
            <span class="title-deco"></span>
            车辆实时监控
          </div>
          <div class="vehicle-grid">
            <div class="vehicle-card" v-for="v in vehicleList" :key="v.id" :class="v.status">
              <div class="vehicle-header">
                <span class="vehicle-plate">{{ v.plate }}</span>
                <span class="vehicle-status-dot"></span>
              </div>
              <div class="vehicle-info">
                <div class="info-row">
                  <span class="label">状态</span>
                  <span class="value">{{ v.statusText }}</span>
                </div>
                <div class="info-row">
                  <span class="label">路线</span>
                  <span class="value route">{{ v.route }}</span>
                </div>
                <div class="info-row">
                  <span class="label">速度</span>
                  <span class="value">{{ v.speed }} km/h</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 中间地图 -->
      <div class="panel-center">
        <div class="map-wrapper">
          <div class="map-header">
            <span class="map-title">🌐 全国物流运输实时监控</span>
            <div class="map-legend">
              <span class="legend-item"><i class="dot red"></i> 仓库</span>
              <span class="legend-item"><i class="dot blue"></i> 运输中</span>
              <span class="legend-item"><i class="dot green"></i> 已送达</span>
            </div>
          </div>
          <div ref="mapChart" class="map-chart"></div>
          <!-- 实时数据浮窗 -->
          <div class="realtime-overlay">
            <div class="overlay-item">
              <span class="overlay-label">今日订单</span>
              <span class="overlay-value">{{ realtimeOrders }}</span>
            </div>
            <div class="overlay-item">
              <span class="overlay-label">运输中</span>
              <span class="overlay-value">{{ transporting }}</span>
            </div>
            <div class="overlay-item">
              <span class="overlay-label">已完成</span>
              <span class="overlay-value">{{ completed }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧面板 -->
      <div class="panel-right">
        <!-- 成本分析 -->
        <div class="panel-item">
          <div class="panel-title">
            <span class="title-deco"></span>
            成本构成分析
          </div>
          <div ref="costChart" class="chart-container"></div>
        </div>

        <!-- 热门路线 -->
        <div class="panel-item">
          <div class="panel-title">
            <span class="title-deco"></span>
            热门运输路线 TOP5
          </div>
          <div ref="routeChart" class="chart-container"></div>
        </div>

        <!-- 实时告警 -->
        <div class="panel-item alerts-panel">
          <div class="panel-title">
            <span class="title-deco"></span>
            实时告警
            <span class="alert-count">{{ alerts.length }}</span>
          </div>
          <div class="alerts-list">
            <div class="alert-item" v-for="a in alerts" :key="a.id" :class="'level-' + a.level">
              <div class="alert-icon">{{ a.level === 'high' ? '🔴' : a.level === 'medium' ? '🟡' : '🔵' }}</div>
              <div class="alert-content">
                <div class="alert-title">{{ a.title }}</div>
                <div class="alert-time">{{ a.time }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部滚动 -->
    <div class="screen-footer">
      <div class="footer-content">
        <div class="scroll-wrapper">
          <div class="scroll-text" :style="{ transform: `translateX(${scrollOffset}px)` }">
            <span v-for="(item, i) in scrollItems" :key="i" class="scroll-item">
              {{ item }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'

const router = useRouter()

// 时间
const currentTime = ref('')

// 核心指标
const coreMetrics = ref([
  { icon: '📦', label: '今日订单', value: 1234, unit: '单' },
  { icon: '🚛', label: '运输车辆', value: 89, unit: '辆' },
  { icon: '✅', label: '完成率', value: 98.5, unit: '%' },
  { icon: '💰', label: '今日营收', value: 125.6, unit: '万' }
])

const animatedValues = ref([])

// 实时数据
const realtimeOrders = ref(1234)
const transporting = ref(89)
const completed = ref(1145)

// 车辆列表
const vehicleList = ref([
  { id: 1, plate: '京A12345', status: 'running', statusText: '运输中', route: '北京→上海', speed: 85 },
  { id: 2, plate: '沪B67890', status: 'running', statusText: '运输中', route: '上海→广州', speed: 72 },
  { id: 3, plate: '粤C11223', status: 'idle', statusText: '待命', route: '广州仓库', speed: 0 },
  { id: 4, plate: '川D44556', status: 'running', statusText: '运输中', route: '成都→武汉', speed: 68 }
])

// 告警
const alerts = ref([
  { id: 1, level: 'high', title: '京A12345 车辆偏离预计路线', time: '14:32:15' },
  { id: 2, level: 'medium', title: '订单 #8890 预计延迟 30 分钟', time: '14:28:45' },
  { id: 3, level: 'low', title: '广州仓库库存预警', time: '14:15:22' }
])

// 滚动
const scrollItems = ref([
  '🚚 订单 #8891 已从北京仓库发货',
  '📦 订单 #8892 已送达上海客户',
  '⚡ 车辆 京A12345 预计 2 小时后到达目的地',
  '📊 今日运输效率达到 98.5%',
  '💰 本月成本节省 ¥125,000'
])
const scrollOffset = ref(0)

// 图表引用
const particleCanvas = ref(null)
const mapChart = ref(null)
const orderTrendChart = ref(null)
const costChart = ref(null)
const routeChart = ref(null)

let charts = []
let particleCtx = null
let particles = []
let animationId = null
let timer = null
let scrollTimer = null

// 返回
const goBack = () => {
  router.push('/dashboard')
}

// 更新时间
const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

// 数字动画
const animateNumbers = () => {
  coreMetrics.value.forEach((m, i) => {
    const target = m.value
    let current = 0
    const step = target / 50
    const interval = setInterval(() => {
      current += step
      if (current >= target) {
        current = target
        clearInterval(interval)
      }
      animatedValues.value[i] = m.unit === '%' ? current.toFixed(1) : Math.floor(current)
    }, 30)
  })
}

// 粒子背景
const initParticles = () => {
  if (!particleCanvas.value) return
  
  const canvas = particleCanvas.value
  particleCtx = canvas.getContext('2d')
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
  
  particles = []
  for (let i = 0; i < 80; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      size: Math.random() * 2 + 1,
      alpha: Math.random() * 0.5 + 0.2
    })
  }
  
  animateParticles()
}

const animateParticles = () => {
  if (!particleCtx) return
  
  const canvas = particleCanvas.value
  particleCtx.clearRect(0, 0, canvas.width, canvas.height)
  
  particles.forEach(p => {
    p.x += p.vx
    p.y += p.vy
    
    if (p.x < 0 || p.x > canvas.width) p.vx *= -1
    if (p.y < 0 || p.y > canvas.height) p.vy *= -1
    
    particleCtx.beginPath()
    particleCtx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
    particleCtx.fillStyle = `rgba(0, 212, 255, ${p.alpha})`
    particleCtx.fill()
  })
  
  // 连线
  particles.forEach((p1, i) => {
    particles.slice(i + 1).forEach(p2 => {
      const dx = p1.x - p2.x
      const dy = p1.y - p2.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      
      if (dist < 150) {
        particleCtx.beginPath()
        particleCtx.moveTo(p1.x, p1.y)
        particleCtx.lineTo(p2.x, p2.y)
        particleCtx.strokeStyle = `rgba(0, 212, 255, ${0.2 * (1 - dist / 150)})`
        particleCtx.stroke()
      }
    })
  })
  
  animationId = requestAnimationFrame(animateParticles)
}

// 初始化地图
const initMapChart = async () => {
  if (!mapChart.value) return
  
  const chart = echarts.init(mapChart.value)
  charts.push(chart)
  
  // 加载中国地图
  try {
    const response = await fetch('/china.json')
    const chinaJson = await response.json()
    echarts.registerMap('china', chinaJson)
    
    const option = {
      backgroundColor: 'transparent',
      geo: {
        map: 'china',
        roam: true,
        zoom: 1.2,
        center: [105, 36],
        label: { show: false },
        itemStyle: {
          areaColor: '#0d1b2a',
          borderColor: '#00d4ff',
          borderWidth: 1,
          shadowColor: 'rgba(0, 212, 255, 0.3)',
          shadowBlur: 10
        },
        emphasis: {
          itemStyle: { 
            areaColor: '#1b3a5f',
            borderColor: '#00ff88'
          },
          label: { show: true, color: '#fff' }
        }
      },
      series: [
        // 飞线效果
        {
          type: 'lines',
          coordinateSystem: 'geo',
          zlevel: 2,
          effect: {
            show: true,
            period: 4,
            trailLength: 0.4,
            symbol: 'arrow',
            symbolSize: 6,
            color: '#00ff88'
          },
          lineStyle: {
            color: '#00d4ff',
            width: 1.5,
            curveness: 0.3
          },
          data: [
            { coords: [[116.46, 39.92], [121.48, 31.22]] },
            { coords: [[113.23, 23.16], [120.19, 30.26]] },
            { coords: [[104.06, 30.67], [114.31, 30.52]] },
            { coords: [[118.78, 32.07], [113.23, 23.16]] },
            { coords: [[106.55, 29.56], [108.95, 34.27]] },
            { coords: [[114.07, 22.62], [120.16, 30.24]] }
          ]
        },
        // 城市节点
        {
          type: 'effectScatter',
          coordinateSystem: 'geo',
          zlevel: 3,
          rippleEffect: {
            brushType: 'stroke',
            scale: 4,
            period: 6
          },
          symbol: 'circle',
          symbolSize: 12,
          itemStyle: {
            color: '#00d4ff',
            shadowColor: 'rgba(0, 212, 255, 0.8)',
            shadowBlur: 15
          },
          data: [
            { name: '北京', value: [116.46, 39.92, 100], itemStyle: { color: '#ff4757' } },
            { name: '上海', value: [121.48, 31.22, 90], itemStyle: { color: '#00d4ff' } },
            { name: '广州', value: [113.23, 23.16, 80], itemStyle: { color: '#00ff88' } },
            { name: '深圳', value: [114.07, 22.62, 75], itemStyle: { color: '#ffcc00' } },
            { name: '成都', value: [104.06, 30.67, 70], itemStyle: { color: '#ff6b35' } },
            { name: '武汉', value: [114.31, 30.52, 65], itemStyle: { color: '#a855f7' } },
            { name: '杭州', value: [120.19, 30.26, 60], itemStyle: { color: '#22d3ee' } }
          ]
        }
      ]
    }
    
    chart.setOption(option)
  } catch (e) {
    console.error('Map load error:', e)
    // 备用图表
    chart.setOption({
      backgroundColor: 'transparent',
      grid: { top: 20, right: 20, bottom: 40, left: 50 },
      xAxis: { type: 'category', data: ['北京', '上海', '广州', '深圳', '成都', '杭州'], axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#888' } },
      yAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#222' } }, axisLabel: { color: '#888' } },
      series: [{ type: 'bar', data: [120, 200, 150, 80, 70, 110], itemStyle: { color: '#00d4ff' } }]
    })
  }
}

// 订单趋势图
const initOrderTrendChart = () => {
  if (!orderTrendChart.value) return
  
  const chart = echarts.init(orderTrendChart.value)
  charts.push(chart)
  
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`)
  const data = hours.map(() => Math.floor(Math.random() * 100 + 50))
  
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { top: 30, right: 20, bottom: 30, left: 50 },
    xAxis: {
      type: 'category',
      data: hours,
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#6b7280', fontSize: 10, interval: 3 },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: '#6b7280' },
      splitLine: { lineStyle: { color: '#1e3a5f', type: 'dashed' } }
    },
    series: [{
      type: 'line',
      data: data,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 3, color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
        { offset: 0, color: '#00d4ff' },
        { offset: 1, color: '#00ff88' }
      ])},
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(0, 212, 255, 0.4)' },
          { offset: 1, color: 'rgba(0, 212, 255, 0.02)' }
        ])
      }
    }]
  })
}

// 成本分析图
const initCostChart = () => {
  if (!costChart.value) return
  
  const chart = echarts.init(costChart.value)
  charts.push(chart)
  
  chart.setOption({
    backgroundColor: 'transparent',
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 8,
        borderColor: '#0d1b2a',
        borderWidth: 2
      },
      label: {
        show: true,
        position: 'outside',
        color: '#fff',
        fontSize: 11,
        formatter: '{b}\n{d}%'
      },
      labelLine: { lineStyle: { color: '#4b5563' } },
      data: [
        { value: 45, name: '运输成本', itemStyle: { color: '#00d4ff' } },
        { value: 25, name: '仓储成本', itemStyle: { color: '#00ff88' } },
        { value: 18, name: '人力成本', itemStyle: { color: '#ffcc00' } },
        { value: 12, name: '其他', itemStyle: { color: '#a855f7' } }
      ]
    }]
  })
}

// 路线排行图
const initRouteChart = () => {
  if (!routeChart.value) return
  
  const chart = echarts.init(routeChart.value)
  charts.push(chart)
  
  chart.setOption({
    backgroundColor: 'transparent',
    grid: { top: 15, right: 20, bottom: 15, left: 90 },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { show: false },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'category',
      data: ['武汉→长沙', '成都→重庆', '上海→杭州', '北京→天津', '广州→深圳'],
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#9ca3af', fontSize: 11 }
    },
    series: [{
      type: 'bar',
      data: [41, 52, 65, 78, 89],
      barWidth: 12,
      itemStyle: {
        borderRadius: [0, 6, 6, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#1e3a5f' },
          { offset: 1, color: '#00d4ff' }
        ])
      },
      label: {
        show: true,
        position: 'right',
        color: '#00d4ff',
        fontSize: 11
      }
    }]
  })
}

// 滚动动画
const startScroll = () => {
  scrollTimer = setInterval(() => {
    scrollOffset.value -= 2
    if (scrollOffset.value < -800) {
      scrollOffset.value = 400
    }
  }, 40)
}

// 定期更新实时数据
const updateRealtimeData = () => {
  setInterval(() => {
    realtimeOrders.value += Math.floor(Math.random() * 3)
    transporting.value = Math.min(150, transporting.value + Math.floor(Math.random() * 3 - 1))
    completed.value += Math.floor(Math.random() * 2)
  }, 5000)
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
  
  initParticles()
  animateNumbers()
  updateRealtimeData()
  
  setTimeout(() => {
    initMapChart()
    initOrderTrendChart()
    initCostChart()
    initRouteChart()
    startScroll()
  }, 200)
  
  window.addEventListener('resize', () => {
    if (particleCanvas.value) {
      particleCanvas.value.width = window.innerWidth
      particleCanvas.value.height = window.innerHeight
    }
    charts.forEach(c => c.resize())
  })
})

onUnmounted(() => {
  clearInterval(timer)
  clearInterval(scrollTimer)
  cancelAnimationFrame(animationId)
  charts.forEach(c => c.dispose())
})
</script>

<style scoped>
.logistics-screen-pro {
  width: 100vw;
  height: 100vh;
  background: radial-gradient(ellipse at center, #0d1b2a 0%, #050a14 100%);
  color: #fff;
  overflow: hidden;
  position: relative;
  font-family: 'Microsoft YaHei', sans-serif;
}

/* 粒子背景 */
.particle-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
}

/* 头部 */
.screen-header {
  position: relative;
  z-index: 10;
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, rgba(13, 27, 42, 0.9) 0%, transparent 100%);
  border-bottom: 1px solid rgba(0, 212, 255, 0.3);
}

.header-decoration {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 300px;
  height: 2px;
  background: linear-gradient(90deg, transparent, #00d4ff);
}

.header-decoration.left { left: 20px; }
.header-decoration.right { right: 20px; background: linear-gradient(90deg, #00d4ff, transparent); }

.main-title {
  font-size: 28px;
  font-weight: bold;
  background: linear-gradient(90deg, #00d4ff, #00ff88, #00d4ff);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: gradientFlow 3s ease infinite;
  display: flex;
  align-items: center;
  gap: 15px;
  margin: 0;
}

@keyframes gradientFlow {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.title-icon { font-size: 24px; }

.header-info {
  position: absolute;
  right: 30px;
  display: flex;
  align-items: center;
  gap: 15px;
}

.time {
  font-size: 14px;
  color: #00d4ff;
  font-family: 'Consolas', monospace;
}

/* 主体 */
.screen-body {
  position: relative;
  z-index: 5;
  display: flex;
  height: calc(100vh - 110px);
  padding: 10px 15px;
  gap: 15px;
}

/* 面板 */
.panel-left, .panel-right {
  width: 340px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.panel-center {
  flex: 1;
}

.panel-item {
  flex: 1;
  background: rgba(13, 27, 42, 0.8);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  overflow: hidden;
  backdrop-filter: blur(10px);
}

.panel-title {
  padding: 12px 15px;
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.15), transparent);
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-deco {
  width: 4px;
  height: 14px;
  background: linear-gradient(180deg, #00d4ff, #00ff88);
  border-radius: 2px;
}

/* 核心指标 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  padding: 10px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px;
  background: rgba(30, 58, 95, 0.3);
  border-radius: 8px;
  border: 1px solid rgba(0, 212, 255, 0.1);
  transition: all 0.3s ease;
}

.metric-card:hover {
  background: rgba(30, 58, 95, 0.5);
  border-color: rgba(0, 212, 255, 0.3);
  transform: translateY(-2px);
}

.metric-card.pulse {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0, 212, 255, 0.2); }
  50% { box-shadow: 0 0 15px 5px rgba(0, 212, 255, 0.1); }
}

.metric-icon { font-size: 28px; }

.metric-value {
  font-size: 22px;
  font-weight: bold;
  color: #00d4ff;
}

.metric-value .unit {
  font-size: 12px;
  color: #6b7280;
  margin-left: 4px;
}

.metric-label {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
}

/* 图表 */
.chart-container {
  height: calc(100% - 45px);
  padding: 10px;
}

/* 车辆卡片 */
.vehicle-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  padding: 10px;
}

.vehicle-card {
  padding: 12px;
  background: rgba(30, 58, 95, 0.2);
  border-radius: 8px;
  border-left: 3px solid;
}

.vehicle-card.running { border-color: #00ff88; }
.vehicle-card.idle { border-color: #6b7280; }

.vehicle-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.vehicle-plate {
  font-weight: bold;
  color: #00d4ff;
  font-size: 13px;
}

.vehicle-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00ff88;
  animation: blink 1.5s ease-in-out infinite;
}

.vehicle-card.idle .vehicle-status-dot {
  background: #6b7280;
  animation: none;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.vehicle-info .info-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  padding: 3px 0;
}

.info-row .label { color: #6b7280; }
.info-row .value { color: #d1d5db; }
.info-row .value.route { color: #00d4ff; font-size: 10px; }

/* 地图 */
.map-wrapper {
  height: 100%;
  position: relative;
  background: rgba(13, 27, 42, 0.6);
  border-radius: 8px;
  border: 1px solid rgba(0, 212, 255, 0.2);
  overflow: hidden;
}

.map-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  padding: 15px 20px;
  background: linear-gradient(180deg, rgba(13, 27, 42, 0.9), transparent);
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 10;
}

.map-title {
  font-size: 16px;
  color: #00d4ff;
  font-weight: 500;
}

.map-legend {
  display: flex;
  gap: 20px;
}

.legend-item {
  font-size: 12px;
  color: #9ca3af;
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot.red { background: #ff4757; }
.dot.blue { background: #00d4ff; }
.dot.green { background: #00ff88; }

.map-chart {
  width: 100%;
  height: 100%;
}

.realtime-overlay {
  position: absolute;
  bottom: 20px;
  left: 20px;
  display: flex;
  gap: 15px;
  z-index: 10;
}

.overlay-item {
  background: rgba(13, 27, 42, 0.9);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 8px;
  padding: 12px 18px;
  text-align: center;
}

.overlay-label {
  font-size: 11px;
  color: #9ca3af;
  display: block;
  margin-bottom: 4px;
}

.overlay-value {
  font-size: 22px;
  font-weight: bold;
  color: #00d4ff;
}

/* 告警 */
.alerts-panel .panel-title {
  justify-content: space-between;
}

.alert-count {
  background: #ff4757;
  color: #fff;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}

.alerts-list {
  padding: 10px;
  max-height: calc(100% - 45px);
  overflow-y: auto;
}

.alert-item {
  display: flex;
  gap: 10px;
  padding: 10px;
  background: rgba(30, 58, 95, 0.2);
  border-radius: 6px;
  margin-bottom: 8px;
  border-left: 3px solid;
}

.alert-item.level-high { border-color: #ff4757; }
.alert-item.level-medium { border-color: #ffcc00; }
.alert-item.level-low { border-color: #00d4ff; }

.alert-icon { font-size: 16px; }

.alert-title {
  font-size: 12px;
  color: #d1d5db;
}

.alert-time {
  font-size: 11px;
  color: #6b7280;
  margin-top: 4px;
}

/* 底部 */
.screen-footer {
  position: relative;
  z-index: 10;
  height: 40px;
  background: linear-gradient(0deg, rgba(13, 27, 42, 0.9), transparent);
}

.footer-content {
  height: 100%;
  display: flex;
  align-items: center;
}

.scroll-wrapper {
  overflow: hidden;
  width: 100%;
}

.scroll-text {
  display: flex;
  gap: 60px;
  white-space: nowrap;
}

.scroll-item {
  color: #00d4ff;
  font-size: 14px;
}
</style>
