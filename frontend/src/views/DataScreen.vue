<template>
  <div class="data-screen">
    <!-- 背景粒子效果 -->
    <div class="particles-bg"></div>
    
    <!-- 顶部标题栏 -->
    <header class="screen-header">
      <div class="header-left">
        <div class="logo-wrap">
          <span class="logo-icon">🚚</span>
          <span class="logo-text">智慧物流数据大屏</span>
        </div>
      </div>
      <div class="header-center">
        <h1 class="main-title">
          <span class="title-decorator">◆</span>
          物流路径规划系统实时监控中心
          <span class="title-decorator">◆</span>
        </h1>
        <div class="sub-title">Smart Logistics Route Planning System - Real-time Monitoring Center</div>
      </div>
      <div class="header-right">
        <div class="datetime">
          <div class="date">{{ currentDate }}</div>
          <div class="time">{{ currentTime }}</div>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="screen-main">
      <!-- 左侧面板 -->
      <aside class="left-panel">
        <!-- 订单统计 -->
        <section class="panel-box order-panel">
          <div class="panel-header">
            <span class="panel-icon">📦</span>
            <span class="panel-title">订单统计</span>
          </div>
          <div class="panel-content">
            <div class="order-stats">
              <div class="stat-item">
                <div class="stat-value">{{ animatedData.totalOrders }}</div>
                <div class="stat-label">总订单数</div>
                <div class="stat-trend up">↑ 12%</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ animatedData.todayOrders }}</div>
                <div class="stat-label">今日订单</div>
                <div class="stat-trend up">↑ 8%</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ animatedData.transitOrders }}</div>
                <div class="stat-label">运输中</div>
                <div class="stat-trend stable">→ 正常</div>
              </div>
              <div class="stat-item">
                <div class="stat-value">{{ animatedData.completedOrders }}</div>
                <div class="stat-label">已完成</div>
                <div class="stat-trend up">↑ 15%</div>
              </div>
            </div>
            <!-- 订单趋势图 -->
            <div ref="orderChartRef" class="chart-container"></div>
          </div>
        </section>

        <!-- 车辆状态 -->
        <section class="panel-box vehicle-panel">
          <div class="panel-header">
            <span class="panel-icon">🚛</span>
            <span class="panel-title">车辆状态</span>
          </div>
          <div class="panel-content">
            <div class="vehicle-stats">
              <div class="vehicle-total">
                <div class="total-number">{{ animatedData.totalVehicles }}</div>
                <div class="total-label">车辆总数</div>
              </div>
              <div class="vehicle-status-list">
                <div class="status-item running">
                  <span class="status-dot"></span>
                  <span class="status-name">运输中</span>
                  <span class="status-count">{{ vehicleStatus.running }}</span>
                </div>
                <div class="status-item idle">
                  <span class="status-dot"></span>
                  <span class="status-name">空闲</span>
                  <span class="status-count">{{ vehicleStatus.idle }}</span>
                </div>
                <div class="status-item maintenance">
                  <span class="status-dot"></span>
                  <span class="status-name">维护中</span>
                  <span class="status-count">{{ vehicleStatus.maintenance }}</span>
                </div>
              </div>
            </div>
            <!-- 车辆环形图 -->
            <div ref="vehicleChartRef" class="chart-container"></div>
          </div>
        </section>
      </aside>

      <!-- 中央区域 - 3D地球 -->
      <section class="center-panel">
        <div class="earth-container">
          <div ref="earthChartRef" class="earth-chart"></div>
          <!-- 中央数据悬浮卡片 -->
          <div class="floating-cards">
            <div class="float-card">
              <div class="card-icon">📍</div>
              <div class="card-value">{{ animatedData.nodes }}</div>
              <div class="card-label">物流节点</div>
            </div>
            <div class="float-card">
              <div class="card-icon">🛣️</div>
              <div class="card-value">{{ animatedData.routes }}</div>
              <div class="card-label">运输路线</div>
            </div>
            <div class="float-card">
              <div class="card-icon">🚚</div>
              <div class="card-value">{{ animatedData.activeVehicles }}</div>
              <div class="card-label">在线车辆</div>
            </div>
          </div>
        </div>
      </section>

      <!-- 右侧面板 -->
      <aside class="right-panel">
        <!-- 成本分析 -->
        <section class="panel-box cost-panel">
          <div class="panel-header">
            <span class="panel-icon">💰</span>
            <span class="panel-title">成本分析</span>
          </div>
          <div class="panel-content">
            <div class="cost-overview">
              <div class="cost-total">
                <span class="cost-value">¥ {{ animatedData.totalCost }}</span>
                <span class="cost-label">本月总成本</span>
              </div>
              <div class="cost-saving">
                <span class="saving-value">↓ ¥ {{ animatedData.savedCost }}</span>
                <span class="saving-label">优化节省</span>
              </div>
            </div>
            <!-- 成本趋势图 -->
            <div ref="costChartRef" class="chart-container"></div>
          </div>
        </section>

        <!-- 预警信息 -->
        <section class="panel-box alert-panel">
          <div class="panel-header">
            <span class="panel-icon">🔔</span>
            <span class="panel-title">实时预警</span>
            <span class="alert-badge">{{ alerts.length }}</span>
          </div>
          <div class="panel-content">
            <div class="alert-list">
              <div 
                v-for="(alert, index) in alerts" 
                :key="index" 
                class="alert-item"
                :class="alert.level"
              >
                <span class="alert-icon">{{ getAlertIcon(alert.level) }}</span>
                <span class="alert-text">{{ alert.message }}</span>
                <span class="alert-time">{{ alert.time }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 供应链状态 -->
        <section class="panel-box supply-panel">
          <div class="panel-header">
            <span class="panel-icon">🔗</span>
            <span class="panel-title">供应链状态</span>
          </div>
          <div class="panel-content">
            <div class="supply-chain">
              <div class="chain-node" v-for="(node, index) in supplyNodes" :key="index">
                <div class="node-icon">{{ node.icon }}</div>
                <div class="node-name">{{ node.name }}</div>
                <div class="node-status" :class="node.status">{{ node.statusText }}</div>
                <div class="chain-line" v-if="index < supplyNodes.length - 1"></div>
              </div>
            </div>
          </div>
        </section>
      </aside>
    </main>

    <!-- 底部滚动信息 -->
    <footer class="screen-footer">
      <div class="scroll-bar">
        <div class="scroll-content">
          <span v-for="(item, index) in scrollMessages" :key="index" class="scroll-item">
            {{ item }}
          </span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import 'echarts-gl'

// 图表引用
const orderChartRef = ref(null)
const vehicleChartRef = ref(null)
const earthChartRef = ref(null)
const costChartRef = ref(null)

// 图表实例
let orderChart = null
let vehicleChart = null
let earthChart = null
let costChart = null

// 时间
const currentDate = ref('')
const currentTime = ref('')

// 动画数据
const animatedData = reactive({
  totalOrders: 0,
  todayOrders: 0,
  transitOrders: 0,
  completedOrders: 0,
  totalVehicles: 0,
  nodes: 0,
  routes: 0,
  activeVehicles: 0,
  totalCost: 0,
  savedCost: 0
})

// 目标数据
const targetData = {
  totalOrders: 12580,
  todayOrders: 326,
  transitOrders: 45,
  completedOrders: 281,
  totalVehicles: 86,
  nodes: 42,
  routes: 128,
  activeVehicles: 52,
  totalCost: 892600,
  savedCost: 45800
}

// 车辆状态
const vehicleStatus = reactive({
  running: 52,
  idle: 28,
  maintenance: 6
})

// 预警信息
const alerts = ref([
  { level: 'warning', message: '北京→上海路线预计延误30分钟', time: '2分钟前' },
  { level: 'info', message: '广州配送站新增5个紧急订单', time: '5分钟前' },
  { level: 'success', message: '成都→武汉配送任务已完成', time: '8分钟前' },
  { level: 'warning', message: '车辆豫A12345即将到达目的地', time: '12分钟前' },
  { level: 'info', message: '深圳仓库库存预警：商品A低于安全库存', time: '15分钟前' }
])

// 供应链节点
const supplyNodes = ref([
  { icon: '🏭', name: '供应商', status: 'normal', statusText: '正常' },
  { icon: '📦', name: '仓库', status: 'normal', statusText: '正常' },
  { icon: '🚛', name: '运输', status: 'running', statusText: '运输中' },
  { icon: '🏪', name: '配送站', status: 'normal', statusText: '正常' },
  { icon: '👤', name: '客户', status: 'success', statusText: '已送达' }
])

// 滚动消息
const scrollMessages = ref([
  '🚚 订单 #2026032701 已从北京发往上海，预计明日送达',
  '📦 广州仓库新增入库单 #IN2026032701，共150件商品',
  '💰 本月成本优化节省 ¥45,800，优化率达12.3%',
  '🔔 深圳配送站完成今日配送任务，准时率98.5%',
  '📍 新增物流节点：武汉配送中心，覆盖中部地区',
  '🏆 本周运输准时率达96.8%，环比提升2.3%',
  '🌱 绿色路线推荐已启用，本月碳排放降低8.5%'
])

// 更新时间
const updateTime = () => {
  const now = new Date()
  currentDate.value = now.toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit',
    weekday: 'long'
  })
  currentTime.value = now.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  })
}

// 数字动画
const animateNumber = (key, target, duration = 2000) => {
  const start = animatedData[key]
  const increment = (target - start) / (duration / 16)
  let current = start
  
  const timer = setInterval(() => {
    current += increment
    if ((increment > 0 && current >= target) || (increment < 0 && current <= target)) {
      animatedData[key] = target
      clearInterval(timer)
    } else {
      animatedData[key] = Math.round(current)
    }
  }, 16)
}

// 启动所有数字动画
const startNumberAnimations = () => {
  Object.keys(targetData).forEach(key => {
    animateNumber(key, targetData[key])
  })
}

// 获取预警图标
const getAlertIcon = (level) => {
  const icons = {
    'warning': '⚠️',
    'info': 'ℹ️',
    'success': '✅',
    'error': '❌'
  }
  return icons[level] || '📢'
}

// 初始化订单趋势图
const initOrderChart = () => {
  if (!orderChartRef.value) return
  
  orderChart = echarts.init(orderChartRef.value)
  
  const hours = ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00']
  const orderData = [12, 8, 5, 18, 35, 48, 42, 38, 45, 52, 38, 25]
  
  const option = {
    backgroundColor: 'transparent',
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: hours,
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255, 255, 255, 0.6)', fontSize: 10 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: 'rgba(255, 255, 255, 0.6)', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } }
    },
    series: [{
      data: orderData,
      type: 'bar',
      barWidth: '60%',
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#00d4ff' },
          { offset: 1, color: 'rgba(0, 212, 255, 0.2)' }
        ]),
        borderRadius: [4, 4, 0, 0]
      },
      emphasis: {
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#00ff88' },
            { offset: 1, color: 'rgba(0, 255, 136, 0.3)' }
          ])
        }
      }
    }]
  }
  
  orderChart.setOption(option)
}

// 初始化车辆状态图
const initVehicleChart = () => {
  if (!vehicleChartRef.value) return
  
  vehicleChart = echarts.init(vehicleChartRef.value)
  
  const option = {
    backgroundColor: 'transparent',
    series: [{
      type: 'pie',
      radius: ['50%', '70%'],
      center: ['50%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 6,
        borderColor: 'rgba(10, 14, 39, 0.8)',
        borderWidth: 2
      },
      label: {
        show: true,
        position: 'outside',
        color: 'rgba(255, 255, 255, 0.8)',
        fontSize: 11,
        formatter: '{b}\n{c}辆'
      },
      labelLine: {
        show: true,
        lineStyle: { color: 'rgba(0, 212, 255, 0.5)' }
      },
      data: [
        { value: vehicleStatus.running, name: '运输中', itemStyle: { color: '#00ff88' } },
        { value: vehicleStatus.idle, name: '空闲', itemStyle: { color: '#00d4ff' } },
        { value: vehicleStatus.maintenance, name: '维护中', itemStyle: { color: '#ff6b6b' } }
      ]
    }]
  }
  
  vehicleChart.setOption(option)
}

// 初始化3D地球
const initEarthChart = () => {
  if (!earthChartRef.value) return
  
  earthChart = echarts.init(earthChartRef.value)
  
  // 模拟节点数据
  const nodes = [
    { name: '北京', lng: 116.46, lat: 39.92, value: 156 },
    { name: '上海', lng: 121.48, lat: 31.22, value: 189 },
    { name: '广州', lng: 113.23, lat: 23.16, value: 98 },
    { name: '深圳', lng: 114.07, lat: 22.62, value: 67 },
    { name: '杭州', lng: 120.19, lat: 30.26, value: 112 },
    { name: '南京', lng: 118.78, lat: 32.04, value: 134 },
    { name: '成都', lng: 104.06, lat: 30.67, value: 78 },
    { name: '武汉', lng: 114.31, lat: 30.52, value: 89 },
    { name: '西安', lng: 108.95, lat: 34.27, value: 56 },
    { name: '重庆', lng: 106.55, lat: 29.56, value: 71 }
  ]
  
  // 模拟路线数据
  const routes = [
    { from: [116.46, 39.92], to: [121.48, 31.22] },
    { from: [121.48, 31.22], to: [113.23, 23.16] },
    { from: [113.23, 23.16], to: [114.07, 22.62] },
    { from: [118.78, 32.04], to: [116.46, 39.92] },
    { from: [104.06, 30.67], to: [106.55, 29.56] },
    { from: [114.31, 30.52], to: [118.78, 32.04] },
    { from: [108.95, 34.27], to: [116.46, 39.92] },
    { from: [120.19, 30.26], to: [121.48, 31.22] }
  ]
  
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
        autoRotate: true,
        autoRotateSpeed: 2,
        distance: 150,
        alpha: 20,
        beta: 0,
        targetCoord: [108, 32]
      },
      atmosphere: {
        show: true,
        offset: 5,
        color: '#00d4ff'
      },
      globeRadius: 80
    },
    series: [
      // 节点
      {
        type: 'scatter3D',
        coordinateSystem: 'globe',
        blendMode: 'lighter',
        symbolSize: (val) => Math.max(val[2] / 5, 10),
        itemStyle: {
          color: '#00d4ff',
          opacity: 0.9
        },
        data: nodes.map(n => [n.lng, n.lat, n.value])
      },
      // 节点发光
      {
        type: 'scatter3D',
        coordinateSystem: 'globe',
        blendMode: 'lighter',
        symbolSize: (val) => Math.max(val[2] / 3, 15),
        itemStyle: {
          color: 'rgba(0, 212, 255, 0.3)',
          opacity: 0.4
        },
        data: nodes.map(n => [n.lng, n.lat, n.value])
      },
      // 路线
      {
        type: 'lines3D',
        coordinateSystem: 'globe',
        blendMode: 'lighter',
        effect: {
          show: true,
          period: 4,
          trailLength: 0.2,
          trailWidth: 2,
          trailColor: '#00ff88'
        },
        lineStyle: {
          width: 2,
          color: '#00d4ff',
          opacity: 0.5
        },
        data: routes.map(r => ({ coords: [r.from, r.to] }))
      }
    ]
  }
  
  earthChart.setOption(option)
}

// 初始化成本趋势图
const initCostChart = () => {
  if (!costChartRef.value) return
  
  costChart = echarts.init(costChartRef.value)
  
  const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
  const costData = [28500, 32100, 29800, 35600, 31200, 27800, 25400]
  const savedData = [3200, 4100, 2800, 5200, 3800, 3100, 2900]
  
  const option = {
    backgroundColor: 'transparent',
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    legend: {
      data: ['运输成本', '优化节省'],
      textStyle: { color: 'rgba(255, 255, 255, 0.7)', fontSize: 11 },
      top: 0
    },
    xAxis: {
      type: 'category',
      data: days,
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255, 255, 255, 0.6)', fontSize: 10 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: 'rgba(255, 255, 255, 0.6)', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } }
    },
    series: [
      {
        name: '运输成本',
        type: 'line',
        smooth: true,
        data: costData,
        lineStyle: { color: '#00d4ff', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 212, 255, 0.3)' },
            { offset: 1, color: 'rgba(0, 212, 255, 0)' }
          ])
        },
        itemStyle: { color: '#00d4ff' }
      },
      {
        name: '优化节省',
        type: 'line',
        smooth: true,
        data: savedData,
        lineStyle: { color: '#00ff88', width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 255, 136, 0.3)' },
            { offset: 1, color: 'rgba(0, 255, 136, 0)' }
          ])
        },
        itemStyle: { color: '#00ff88' }
      }
    ]
  }
  
  costChart.setOption(option)
}

// 窗口大小变化
const handleResize = () => {
  orderChart?.resize()
  vehicleChart?.resize()
  earthChart?.resize()
  costChart?.resize()
}

// 定时器
let timeTimer = null
let alertTimer = null

// 模拟预警更新
const updateAlerts = () => {
  const newAlerts = [
    { level: 'warning', message: '上海→广州路线因天气延误15分钟', time: '刚刚' },
    { level: 'info', message: '北京仓库新入库单 #IN2026032702', time: '刚刚' },
    { level: 'success', message: '订单 #2026032702 已完成配送', time: '刚刚' }
  ]
  
  const randomAlert = newAlerts[Math.floor(Math.random() * newAlerts.length)]
  alerts.value.unshift(randomAlert)
  if (alerts.value.length > 6) {
    alerts.value.pop()
  }
}

onMounted(async () => {
  // 更新时间
  updateTime()
  timeTimer = setInterval(updateTime, 1000)
  
  // 启动数字动画
  startNumberAnimations()
  
  // 初始化图表
  await nextTick()
  setTimeout(() => {
    initOrderChart()
    initVehicleChart()
    initEarthChart()
    initCostChart()
  }, 100)
  
  // 定时更新预警
  alertTimer = setInterval(updateAlerts, 30000)
  
  // 窗口大小变化
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (timeTimer) clearInterval(timeTimer)
  if (alertTimer) clearInterval(alertTimer)
  window.removeEventListener('resize', handleResize)
  
  orderChart?.dispose()
  vehicleChart?.dispose()
  earthChart?.dispose()
  costChart?.dispose()
})
</script>

<style scoped>
/* 基础布局 */
.data-screen {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #0d1033 100%);
  overflow: hidden;
  position: relative;
  color: #fff;
  font-family: 'Microsoft YaHei', sans-serif;
}

/* 粒子背景 */
.particles-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: 
    radial-gradient(circle at 20% 30%, rgba(0, 212, 255, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 80% 70%, rgba(0, 255, 136, 0.1) 0%, transparent 50%);
  pointer-events: none;
}

/* 顶部标题栏 */
.screen-header {
  height: 80px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 30px;
  background: linear-gradient(180deg, rgba(0, 212, 255, 0.1) 0%, transparent 100%);
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  position: relative;
  z-index: 10;
}

.header-left .logo-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 32px;
}

.logo-text {
  font-size: 20px;
  font-weight: 600;
  background: linear-gradient(90deg, #00d4ff, #00ff88);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-center {
  text-align: center;
}

.main-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0;
  letter-spacing: 4px;
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
}

.title-decorator {
  color: #00d4ff;
  margin: 0 15px;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.sub-title {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 2px;
  margin-top: 5px;
}

.header-right .datetime {
  text-align: right;
}

.date {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
}

.time {
  font-size: 24px;
  font-weight: 600;
  color: #00d4ff;
  font-family: 'Consolas', monospace;
}

/* 主内容区 */
.screen-main {
  display: flex;
  height: calc(100vh - 120px);
  padding: 15px;
  gap: 15px;
}

/* 左侧面板 */
.left-panel {
  width: 300px;
  min-width: 280px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.right-panel {
  width: 300px;
  min-width: 280px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

/* 中央面板 */
.center-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 面板盒子 */
.panel-box {
  background: rgba(10, 14, 39, 0.8);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 8px;
  overflow: hidden;
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
}

.order-panel {
  flex: 1.2;
}

.vehicle-panel {
  flex: 1;
}

.cost-panel {
  flex: 1;
}

.alert-panel {
  flex: 0.8;
}

.supply-panel {
  flex: 0.6;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 15px;
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.15), transparent);
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
}

.panel-icon {
  font-size: 18px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #00d4ff;
}

.alert-badge {
  margin-left: auto;
  background: #ff6b6b;
  color: #fff;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}

.panel-content {
  padding: 12px 15px;
  flex: 1;
  overflow: auto;
}

/* 订单统计 */
.order-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 15px;
}

.stat-item {
  text-align: center;
  padding: 10px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 6px;
  border: 1px solid rgba(0, 212, 255, 0.1);
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #00d4ff;
}

.stat-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 4px;
}

.stat-trend {
  font-size: 10px;
  margin-top: 4px;
}

.stat-trend.up { color: #00ff88; }
.stat-trend.down { color: #ff6b6b; }
.stat-trend.stable { color: #ffc107; }

/* 车辆状态 */
.vehicle-stats {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
}

.vehicle-total {
  text-align: center;
  padding: 10px;
  background: rgba(0, 212, 255, 0.1);
  border-radius: 8px;
  min-width: 80px;
}

.total-number {
  font-size: 28px;
  font-weight: 700;
  color: #00ff88;
}

.total-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.vehicle-status-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-item.running .status-dot { background: #00ff88; }
.status-item.idle .status-dot { background: #00d4ff; }
.status-item.maintenance .status-dot { background: #ff6b6b; }

.status-name {
  flex: 1;
  color: rgba(255, 255, 255, 0.7);
}

.status-count {
  font-weight: 600;
  color: #fff;
}

/* 图表容器 */
.chart-container {
  height: 120px;
  min-height: 100px;
}

/* 地球容器 */
.earth-container {
  flex: 1;
  position: relative;
  background: rgba(10, 14, 39, 0.5);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 8px;
  overflow: hidden;
  min-height: 400px;
}

.earth-chart {
  width: 100%;
  height: 100%;
}

/* 悬浮卡片 */
.floating-cards {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 20px;
}

.float-card {
  background: rgba(10, 14, 39, 0.9);
  border: 1px solid rgba(0, 212, 255, 0.4);
  border-radius: 8px;
  padding: 12px 20px;
  text-align: center;
  backdrop-filter: blur(10px);
}

.float-card .card-icon {
  font-size: 20px;
  margin-bottom: 5px;
}

.float-card .card-value {
  font-size: 22px;
  font-weight: 700;
  color: #00d4ff;
}

.float-card .card-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

/* 成本分析 */
.cost-overview {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
}

.cost-total,
.cost-saving {
  text-align: center;
}

.cost-value {
  font-size: 22px;
  font-weight: 700;
  color: #00d4ff;
}

.cost-label,
.saving-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.saving-value {
  font-size: 18px;
  font-weight: 600;
  color: #00ff88;
}

/* 预警列表 */
.alert-list {
  max-height: 140px;
  overflow-y: auto;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  margin-bottom: 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  font-size: 12px;
  border-left: 3px solid;
}

.alert-item.warning { border-color: #ffc107; }
.alert-item.info { border-color: #00d4ff; }
.alert-item.success { border-color: #00ff88; }
.alert-item.error { border-color: #ff6b6b; }

.alert-icon {
  font-size: 14px;
}

.alert-text {
  flex: 1;
  color: rgba(255, 255, 255, 0.8);
}

.alert-time {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}

/* 供应链 */
.supply-chain {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chain-node {
  text-align: center;
  position: relative;
}

.node-icon {
  font-size: 24px;
  margin-bottom: 5px;
}

.node-name {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
}

.node-status {
  font-size: 10px;
  margin-top: 4px;
  padding: 2px 6px;
  border-radius: 4px;
}

.node-status.normal { background: rgba(0, 212, 255, 0.2); color: #00d4ff; }
.node-status.running { background: rgba(0, 255, 136, 0.2); color: #00ff88; }
.node-status.success { background: rgba(0, 255, 136, 0.2); color: #00ff88; }

.chain-line {
  position: absolute;
  top: 12px;
  right: -30px;
  width: 25px;
  height: 2px;
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.5), rgba(0, 255, 136, 0.5));
}

.chain-line::after {
  content: '→';
  position: absolute;
  right: -5px;
  top: -8px;
  color: #00ff88;
  font-size: 12px;
}

/* 底部滚动 */
.screen-footer {
  height: 40px;
  background: rgba(0, 212, 255, 0.05);
  border-top: 1px solid rgba(0, 212, 255, 0.2);
  overflow: hidden;
}

.scroll-bar {
  height: 100%;
  display: flex;
  align-items: center;
}

.scroll-content {
  display: flex;
  gap: 50px;
  animation: scroll 30s linear infinite;
  white-space: nowrap;
}

@keyframes scroll {
  0% { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

.scroll-item {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

/* 滚动条美化 */
::-webkit-scrollbar {
  width: 4px;
}

::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 212, 255, 0.3);
  border-radius: 2px;
}
</style>