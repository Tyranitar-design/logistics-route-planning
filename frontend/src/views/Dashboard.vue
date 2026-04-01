<template>
  <div class="dashboard">
    <!-- 背景动效 -->
    <div class="bg-effects">
      <div class="grid-lines"></div>
      <div class="scan-line"></div>
      <div class="circuit-lines"></div>
      <div class="floating-particles">
        <span v-for="i in 30" :key="i" class="particle" :style="getParticleStyle(i)"></span>
      </div>
      <div class="corner-deco top-left"></div>
      <div class="corner-deco top-right"></div>
      <div class="corner-deco bottom-left"></div>
      <div class="corner-deco bottom-right"></div>
    </div>

    <!-- 顶部标题栏 -->
    <div class="dashboard-header">
      <div class="header-left">
        <div class="logo-glow">
          <h1>🚚 智慧物流调度中心</h1>
        </div>
        <span class="subtitle">SMART LOGISTICS DISPATCH CENTER</span>
      </div>
      <div class="header-center">
        <div class="digital-clock">
          <div class="clock-display">
            <span class="clock-segment">{{ timeHours }}</span>
            <span class="clock-separator">:</span>
            <span class="clock-segment">{{ timeMinutes }}</span>
            <span class="clock-separator">:</span>
            <span class="clock-segment">{{ timeSeconds }}</span>
          </div>
          <div class="date-display">{{ currentDate }}</div>
        </div>
      </div>
      <div class="header-right">
        <div class="status-indicator">
          <span class="pulse-dot"></span>
          <span class="status-text">系统运行中</span>
        </div>
        <div class="weather-widget" v-if="currentWeather">
          <span class="weather-icon">{{ getWeatherIcon(currentWeather.weather) }}</span>
          <span class="weather-temp">{{ currentWeather.temperature }}°C</span>
          <span class="weather-desc">{{ currentWeather.weather }}</span>
        </div>
      </div>
    </div>

    <!-- 核心指标卡片 -->
    <el-row :gutter="12" class="metric-row">
      <el-col :span="4" v-for="(metric, index) in metrics" :key="index">
        <div class="metric-card" :class="metric.gradient">
          <div class="card-glow"></div>
          <div class="card-content">
            <div class="metric-icon-wrapper">
              <span class="metric-icon">{{ metric.icon }}</span>
              <div class="icon-ring"></div>
            </div>
            <div class="metric-info">
              <div class="metric-value">
                <span class="value-number">{{ animatedStats[metric.key] }}</span>
                <span class="value-unit" v-if="metric.unit">{{ metric.unit }}</span>
              </div>
              <div class="metric-label">{{ metric.label }}</div>
            </div>
            <div class="metric-trend" :class="metric.trendClass">
              <span class="trend-icon">{{ metric.trendIcon }}</span>
              <span class="trend-value">{{ metric.trendValue }}</span>
            </div>
          </div>
          <div class="card-footer">
            <span class="footer-line"></span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 主要图表区域 -->
    <el-row :gutter="12" style="margin-top: 12px">
      <!-- 3D 地球/地图 -->
      <el-col :span="10">
        <div class="chart-card large-card">
          <div class="card-header">
            <div class="header-decoration">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">🌐 全国节点分布</span>
            <div class="header-tags">
              <el-tag size="small" effect="dark" type="success">实时</el-tag>
              <el-button size="small" type="primary" link @click="$router.push('/earth3d')">
                🌍 3D
              </el-button>
            </div>
          </div>
          <div ref="chinaMapChart" style="height: 380px"></div>
          <div class="card-stats">
            <div class="stat-item" v-for="(item, i) in mapStats" :key="i">
              <span class="stat-dot" :style="{background: item.color}"></span>
              <span class="stat-name">{{ item.name }}</span>
              <span class="stat-value">{{ item.value }}</span>
            </div>
          </div>
        </div>
      </el-col>
      
      <!-- 订单趋势 + 状态 -->
      <el-col :span="7">
        <div class="chart-card">
          <div class="card-header">
            <div class="header-decoration">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">📈 订单趋势</span>
            <el-radio-group v-model="trendRange" size="small" @change="loadOrderTrend">
              <el-radio-button label="7">7天</el-radio-button>
              <el-radio-button label="14">14天</el-radio-button>
            </el-radio-group>
          </div>
          <div ref="orderTrendChart" style="height: 200px"></div>
        </div>
        
        <div class="chart-card" style="margin-top: 12px">
          <div class="card-header">
            <div class="header-decoration">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">🎯 订单状态</span>
          </div>
          <div ref="orderStatusChart" style="height: 168px"></div>
        </div>
      </el-col>
      
      <!-- 右侧数据面板 -->
      <el-col :span="7">
        <div class="chart-card">
          <div class="card-header">
            <div class="header-decoration">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">⚡ 运输效率雷达</span>
          </div>
          <div ref="efficiencyRadar" style="height: 180px"></div>
        </div>
        
        <div class="chart-card" style="margin-top: 12px">
          <div class="card-header">
            <div class="header-decoration">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">💰 成本分析</span>
          </div>
          <div ref="costAnalysisChart" style="height: 188px"></div>
        </div>
        
        <!-- 油价卡片 -->
        <div class="chart-card" style="margin-top: 12px; padding: 12px;">
          <OilPriceCard ref="oilPriceCard" />
        </div>
      </el-col>
    </el-row>

    <!-- 底部区域 -->
    <el-row :gutter="12" style="margin-top: 12px">
      <!-- 实时订单流 -->
      <el-col :span="6">
        <div class="chart-card stream-card">
          <div class="card-header">
            <div class="header-decoration">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">🔔 实时订单流</span>
            <el-badge :value="recentOrders.length" type="primary" />
          </div>
          <div class="order-stream">
            <TransitionGroup name="stream">
              <div v-for="order in recentOrders" :key="order.id" class="stream-item">
                <div class="item-avatar" :class="getStatusClass(order.status)">
                  {{ getStatusIcon(order.status) }}
                </div>
                <div class="item-info">
                  <span class="item-id">{{ order.order_number }}</span>
                  <span class="item-customer">{{ order.customer_name }}</span>
                </div>
                <div class="item-meta">
                  <span class="item-time">{{ formatTime(order.created_at) }}</span>
                </div>
              </div>
            </TransitionGroup>
          </div>
        </div>
      </el-col>
      
      <!-- 车辆状态 -->
      <el-col :span="6">
        <div class="chart-card">
          <div class="card-header">
            <div class="header-decoration">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">🚛 车辆状态监控</span>
          </div>
          <div ref="vehicleStatusChart" style="height: 200px"></div>
          <div class="vehicle-summary">
            <div class="vehicle-item" v-for="v in vehicleSummary" :key="v.status">
              <span class="v-status" :style="{color: v.color}">{{ v.status }}</span>
              <span class="v-count">{{ v.count }}辆</span>
              <el-progress :percentage="v.percent" :stroke-width="4" :color="v.color" :show-text="false" />
            </div>
          </div>
        </div>
      </el-col>
      
      <!-- 天气影响 -->
      <el-col :span="6">
        <div class="chart-card">
          <div class="card-header">
            <div class="header-decoration">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">🌤️ 天气运输影响</span>
          </div>
          <div ref="weatherImpactChart" style="height: 240px"></div>
        </div>
      </el-col>
      
      <!-- 快捷操作 -->
      <el-col :span="6">
        <div class="chart-card action-card">
          <div class="card-header">
            <div class="header-decoration">
              <span class="deco-line"></span>
              <span class="deco-dot"></span>
            </div>
            <span class="card-title">🚀 快捷操作</span>
          </div>
          <div class="action-grid">
            <div class="action-btn" @click="$router.push('/earth3d')">
              <div class="btn-icon">🌍</div>
              <span class="btn-text">3D地球</span>
              <div class="btn-glow"></div>
            </div>
            <div class="action-btn" @click="$router.push('/dispatch')">
              <div class="btn-icon">🤖</div>
              <span class="btn-text">智能调度</span>
              <div class="btn-glow"></div>
            </div>
            <div class="action-btn" @click="$router.push('/map')">
              <div class="btn-icon">🗺️</div>
              <span class="btn-text">地图视图</span>
              <div class="btn-glow"></div>
            </div>
            <div class="action-btn" @click="$router.push('/orders')">
              <div class="btn-icon">📦</div>
              <span class="btn-text">订单管理</span>
              <div class="btn-glow"></div>
            </div>
            <div class="action-btn" @click="$router.push('/cost')">
              <div class="btn-icon">📊</div>
              <span class="btn-text">成本分析</span>
              <div class="btn-glow"></div>
            </div>
            <div class="action-btn" @click="$router.push('/vehicles')">
              <div class="btn-icon">🚛</div>
              <span class="btn-text">车辆管理</span>
              <div class="btn-glow"></div>
            </div>
            <div class="action-btn" @click="showExportDialog = true">
              <div class="btn-icon">📤</div>
              <span class="btn-text">数据导出</span>
              <div class="btn-glow"></div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 导出对话框 -->
    <el-dialog v-model="showExportDialog" title="📤 数据导出" width="450px" class="tech-dialog">
      <el-form label-width="90px">
        <el-form-item label="导出类型">
          <el-select v-model="exportType" placeholder="请选择">
            <el-option label="节点数据" value="nodes" />
            <el-option label="订单数据" value="orders" />
            <el-option label="运输报表" value="transport_report" />
          </el-select>
        </el-form-item>
        <el-form-item label="导出格式">
          <el-radio-group v-model="exportFormat">
            <el-radio label="xlsx" value="xlsx">Excel</el-radio>
            <el-radio label="csv" value="csv">CSV</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExportDialog = false">取消</el-button>
        <el-button type="primary" :loading="exportLoading" @click="handleExport">导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { Connection } from '@element-plus/icons-vue'
import { getOverview, getOrderTrend, getOrderDistribution, getVehicleUtilization } from '@/api/stats'
import { exportData } from '@/api/data'
import { getCostComponents } from '@/api/cost'
import { getOrders } from '@/api/orders'
import { getWeatherNow } from '@/api/weather'
import { getNodes, getRoutes } from '@/api/nodes'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import 'echarts-gl'
import OilPriceCard from '@/components/OilPriceCard.vue'

// 时间
const currentDate = ref('')
const timeHours = ref('00')
const timeMinutes = ref('00')
const timeSeconds = ref('00')
const currentWeather = ref(null)

// 统计数据
const stats = ref({
  total_nodes: 0, total_routes: 0, total_vehicles: 0, total_orders: 0,
  new_nodes_today: 0, new_routes_today: 0, available_vehicles: 0,
  delivered_orders: 0, pending_orders: 0, total_cost: 0
})

const animatedStats = reactive({
  total_nodes: 0, total_routes: 0, total_vehicles: 0, total_orders: 0,
  delivered_orders: 0, pending_orders: 0
})

const trendRange = ref('7')
const recentOrders = ref([])

// 图表引用
const chinaMapChart = ref(null)
const orderTrendChart = ref(null)
const orderStatusChart = ref(null)
const efficiencyRadar = ref(null)
const costAnalysisChart = ref(null)
const vehicleStatusChart = ref(null)
const weatherImpactChart = ref(null)
const oilPriceCard = ref(null)

let charts = []
let timeInterval = null

// 安全初始化图表（防止重复初始化）
const initChart = (domRef) => {
  if (!domRef) return null
  
  // 检查是否已存在实例
  const existingInstance = echarts.getInstanceByDom(domRef)
  if (existingInstance) {
    existingInstance.dispose()
  }
  
  const chart = echarts.init(domRef)
  charts.push(chart)
  return chart
}

// 导出
const showExportDialog = ref(false)
const exportLoading = ref(false)
const exportType = ref('nodes')
const exportFormat = ref('xlsx')

// 指标配置
const metrics = computed(() => [
  {
    icon: '📍', label: '节点总数', key: 'total_nodes', gradient: 'gradient-cyan',
    trendIcon: '↑', trendValue: stats.value.new_nodes_today || 0, trendClass: 'up'
  },
  {
    icon: '🛣️', label: '路线总数', key: 'total_routes', gradient: 'gradient-green',
    trendIcon: '↑', trendValue: stats.value.new_routes_today || 0, trendClass: 'up'
  },
  {
    icon: '🚛', label: '车辆总数', key: 'total_vehicles', gradient: 'gradient-purple',
    trendIcon: '●', trendValue: `${stats.value.available_vehicles || 0} 可用`, trendClass: 'neutral'
  },
  {
    icon: '📦', label: '订单总数', key: 'total_orders', gradient: 'gradient-orange',
    trendIcon: '⏳', trendValue: `${stats.value.pending_orders || 0} 待处理`, trendClass: 'warning'
  },
  {
    icon: '✅', label: '已完成', key: 'delivered_orders', gradient: 'gradient-blue',
    trendIcon: '↑', trendValue: `${deliveryRate.value}%`, trendClass: 'up'
  },
  {
    icon: '💰', label: '总成本', key: 'total_cost', gradient: 'gradient-pink', unit: '元',
    trendIcon: '—', trendValue: '本月', trendClass: 'neutral'
  }
])

const deliveryRate = computed(() => {
  if (stats.value.total_orders === 0) return 0
  return Math.round((stats.value.delivered_orders / stats.value.total_orders) * 100)
})

const mapStats = computed(() => [
  { name: '仓库', value: stats.value.total_nodes || 0, color: '#00d4ff' },
  { name: '配送站', value: Math.floor((stats.value.total_nodes || 0) * 0.3), color: '#00ff88' },
  { name: '客户点', value: Math.floor((stats.value.total_nodes || 0) * 0.5), color: '#ff6b6b' }
])

const vehicleSummary = computed(() => {
  const total = stats.value.total_vehicles || 1
  return [
    { status: '可用', count: stats.value.available_vehicles || 0, percent: Math.round(((stats.value.available_vehicles || 0) / total) * 100), color: '#00ff88' },
    { status: '运输中', count: Math.floor(total * 0.3), percent: 30, color: '#00d4ff' },
    { status: '维护', count: Math.floor(total * 0.1), percent: 10, color: '#ff6b6b' }
  ]
})

// 格式化方法
const getWeatherIcon = (weather) => {
  const icons = { '晴': '☀️', '多云': '⛅', '阴': '☁️', '小雨': '🌧️', '中雨': '🌧️', '大雨': '⛈️' }
  return icons[weather] || '🌤️'
}

const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now - date
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  return `${Math.floor(diff / 3600000)}小时前`
}

const getStatusClass = (status) => ({
  pending: 'status-pending', assigned: 'status-assigned',
  in_transit: 'status-transit', delivered: 'status-delivered'
}[status] || 'status-pending')

const getStatusIcon = (status) => ({
  pending: '📋', assigned: '🚛', in_transit: '🚚', delivered: '✅'
}[status] || '📦')

const getParticleStyle = (i) => ({
  left: `${Math.random() * 100}%`,
  top: `${Math.random() * 100}%`,
  animationDelay: `${Math.random() * 5}s`,
  animationDuration: `${3 + Math.random() * 4}s`
})

// 更新时间
const updateTime = () => {
  const now = new Date()
  currentDate.value = now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
  timeHours.value = String(now.getHours()).padStart(2, '0')
  timeMinutes.value = String(now.getMinutes()).padStart(2, '0')
  timeSeconds.value = String(now.getSeconds()).padStart(2, '0')
}

// 数字动画
const animateNumber = (key, target) => {
  const duration = 2000
  const start = animatedStats[key] || 0
  const increment = (target - start) / (duration / 16)
  let current = start
  const timer = setInterval(() => {
    current += increment
    if ((increment > 0 && current >= target) || (increment < 0 && current <= target) || increment === 0) {
      animatedStats[key] = target
      clearInterval(timer)
    } else {
      animatedStats[key] = Math.round(current)
    }
  }, 16)
}

// 加载数据
const loadStats = async () => {
  try {
    const data = await getOverview()
    stats.value = data
    Object.keys(animatedStats).forEach(key => {
      if (data[key] !== undefined) animateNumber(key, data[key])
    })
  } catch (e) { console.error(e) }
}

const loadRecentOrders = async () => {
  try {
    const res = await getOrders({ per_page: 8 })
    recentOrders.value = res.orders || []
  } catch (e) { console.error(e) }
}

const loadWeather = async () => {
  try {
    const res = await getWeatherNow('北京')
    if (res.success) currentWeather.value = res.data
  } catch (e) { console.error(e) }
}

const loadOrderTrend = async () => {
  // 已在 initOrderTrend 中处理
}

// 初始化图表
const initChinaMap = async () => {
  const chart = initChart(chinaMapChart.value)
  if (!chart) return
  
  // 加载中国地图数据
  try {
    const chinaMapUrl = 'https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json'
    const response = await fetch(chinaMapUrl)
    const chinaJson = await response.json()
    echarts.registerMap('china', chinaJson)
  } catch (e) {
    console.log('地图加载失败，使用简化版')
  }
  
  // 节点数据
  const nodeData = [
    { name: '北京总部', value: [116.46, 39.92, 100] },
    { name: '上海仓库', value: [121.48, 31.22, 90] },
    { name: '广州配送', value: [113.23, 23.16, 80] },
    { name: '深圳站点', value: [114.07, 22.62, 70] },
    { name: '杭州中心', value: [120.19, 30.26, 60] },
    { name: '南京仓库', value: [118.78, 32.04, 85] },
    { name: '成都站点', value: [104.06, 30.67, 50] },
    { name: '武汉中心', value: [114.31, 30.52, 55] },
    { name: '西安仓库', value: [108.95, 34.27, 45] },
    { name: '重庆配送', value: [106.55, 29.56, 65] },
    { name: '天津站点', value: [117.20, 39.13, 75] },
    { name: '苏州中心', value: [120.62, 31.32, 40] },
    { name: '青岛仓库', value: [120.38, 36.07, 55] },
    { name: '厦门站点', value: [118.10, 24.46, 35] },
    { name: '长沙中心', value: [112.94, 28.23, 45] },
    { name: '郑州仓库', value: [113.65, 34.76, 50] },
    { name: '沈阳站点', value: [123.38, 41.80, 40] },
    { name: '哈尔滨仓库', value: [126.63, 45.75, 35] },
    { name: '昆明中心', value: [102.73, 25.04, 30] },
    { name: '乌鲁木齐', value: [87.62, 43.83, 20] }
  ]
  
  const linesData = [
    { coords: [[116.46, 39.92], [121.48, 31.22]] },
    { coords: [[116.46, 39.92], [113.23, 23.16]] },
    { coords: [[121.48, 31.22], [120.19, 30.26]] },
    { coords: [[113.23, 23.16], [114.07, 22.62]] },
    { coords: [[104.06, 30.67], [106.55, 29.56]] },
    { coords: [[114.31, 30.52], [118.78, 32.04]] },
    { coords: [[108.95, 34.27], [116.46, 39.92]] },
    { coords: [[121.48, 31.22], [120.62, 31.32]] },
    { coords: [[120.38, 36.07], [121.48, 31.22]] },
    { coords: [[113.65, 34.76], [114.31, 30.52]] },
    { coords: [[123.38, 41.80], [116.46, 39.92]] },
    { coords: [[126.63, 45.75], [123.38, 41.80]] }
  ]
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}' },
    geo: {
      map: 'china',
      roam: true,
      zoom: 1.2,
      center: [104, 35],
      itemStyle: {
        areaColor: 'rgba(0, 212, 255, 0.08)',
        borderColor: 'rgba(0, 212, 255, 0.3)',
        borderWidth: 1
      },
      emphasis: {
        itemStyle: { areaColor: 'rgba(0, 212, 255, 0.25)' }
      },
      label: { show: false }
    },
    series: [
      // 热力点
      {
        type: 'effectScatter',
        coordinateSystem: 'geo',
        data: nodeData.map((item, i) => ({
          name: item.name,
          value: item.value,
          itemStyle: { color: ['#00d4ff', '#00ff88', '#ff6b6b', '#ffd93d'][i % 4] }
        })),
        symbolSize: (val) => Math.max(val[2] / 8, 12),
        showEffectOn: 'render',
        rippleEffect: { brushType: 'stroke', scale: 3, period: 3 },
        label: { show: true, formatter: '{b}', position: 'right', color: '#fff', fontSize: 10 },
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 212, 255, 0.5)' }
      },
      // 连接线
      {
        type: 'lines',
        coordinateSystem: 'geo',
        data: linesData,
        symbol: ['none', 'arrow'],
        symbolSize: 6,
        lineStyle: { color: '#00d4ff', width: 1.5, opacity: 0.6, curveness: 0.2 },
        effect: {
          show: true, period: 4, trailLength: 0.5,
          symbol: 'arrow', symbolSize: 4, color: '#00ff88'
        }
      }
    ]
  })
  
  // 注册点击跳转事件
  chart.on('click', () => {
    window.$router?.push('/earth3d')
  })
}

const initOrderTrend = async () => {
  const chart = initChart(orderTrendChart.value)
  if (!chart) return
  
  const data = await getOrderTrend().catch(() => ({ trend: [] }))
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(0,0,0,0.8)', borderColor: '#00d4ff', textStyle: { color: '#fff' } },
    grid: { left: '5%', right: '5%', bottom: '10%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.trend?.map(i => i.date?.slice(5) || '') || [],
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
    },
    series: [{
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      data: data.trend?.map(i => i.count) || [],
      lineStyle: { color: '#00d4ff', width: 2, shadowBlur: 10, shadowColor: 'rgba(0, 212, 255, 0.5)' },
      itemStyle: { color: '#00d4ff', borderColor: '#fff', borderWidth: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(0, 212, 255, 0.4)' },
          { offset: 1, color: 'rgba(0, 212, 255, 0.02)' }
        ])
      }
    }]
  })
}

const initOrderStatus = async () => {
  const chart = initChart(orderStatusChart.value)
  if (!chart) return
  
  const data = await getOrderDistribution().catch(() => ({ distribution: [] }))
  const colors = ['#00d4ff', '#00ff88', '#ffd93d', '#ff6b6b']
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { color: 'rgba(255,255,255,0.7)', fontSize: 10 }, itemWidth: 10, itemHeight: 10 },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 4, borderColor: 'rgba(0,0,0,0.3)', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 12, fontWeight: 'bold', color: '#fff' } },
      data: (data.distribution || []).map((item, i) => ({ ...item, itemStyle: { color: colors[i % 4] } }))
    }]
  })
}

const initEfficiencyRadar = () => {
  const chart = initChart(efficiencyRadar.value)
  if (!chart) return
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: {},
    radar: {
      indicator: [
        { name: '配送及时率', max: 100 },
        { name: '车辆利用率', max: 100 },
        { name: '路线优化率', max: 100 },
        { name: '成本控制', max: 100 },
        { name: '客户满意度', max: 100 }
      ],
      radius: '65%',
      axisName: { color: 'rgba(255,255,255,0.7)', fontSize: 10 },
      splitArea: { areaStyle: { color: ['rgba(0, 212, 255, 0.05)', 'rgba(0, 212, 255, 0.1)'] } },
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.2)' } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: [85, 72, 88, 76, 90],
        name: '效率指标',
        areaStyle: { color: 'rgba(0, 212, 255, 0.3)' },
        lineStyle: { color: '#00d4ff', width: 2 },
        itemStyle: { color: '#00d4ff' }
      }]
    }]
  })
}

const initCostAnalysis = async () => {
  const chart = initChart(costAnalysisChart.value)
  if (!chart) return
  
  const data = await getCostComponents().catch(() => ({ components: [] }))
  const components = data.components || [
    { name: '燃油费', value: 12500 },
    { name: '过路费', value: 8200 },
    { name: '人工费', value: 15600 },
    { name: '折旧费', value: 4800 }
  ]
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '5%', right: '5%', bottom: '10%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: components.map(c => c.name),
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.7)', fontSize: 10, interval: 0 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10, formatter: '¥{value}' }
    },
    series: [{
      type: 'bar',
      barWidth: '50%',
      data: components.map((c, i) => ({
        value: c.value,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: ['#00d4ff', '#00ff88', '#ffd93d', '#ff6b6b'][i % 4] },
            { offset: 1, color: ['rgba(0,212,255,0.3)', 'rgba(0,255,136,0.3)', 'rgba(255,217,61,0.3)', 'rgba(255,107,107,0.3)'][i % 4] }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      })),
      label: { show: true, position: 'top', formatter: '¥{c}', fontSize: 9, color: 'rgba(255,255,255,0.7)' }
    }]
  })
}

const initVehicleStatus = async () => {
  const chart = initChart(vehicleStatusChart.value)
  if (!chart) return
  
  const data = await getVehicleUtilization().catch(() => ({ utilization: [] }))
  const colors = ['#00ff88', '#00d4ff', '#ff6b6b']
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '50%'],
      data: (data.utilization || [{ name: '可用', value: 5 }, { name: '运输中', value: 3 }, { name: '维护', value: 1 }]).map((item, i) => ({
        ...item,
        itemStyle: { color: colors[i % 3] }
      })),
      label: { show: true, formatter: '{b}\n{c}辆', color: '#fff', fontSize: 10 },
      itemStyle: { borderRadius: 4, borderColor: 'rgba(0,0,0,0.3)', borderWidth: 2 }
    }]
  })
}

const initWeatherImpact = () => {
  const chart = initChart(weatherImpactChart.value)
  if (!chart) return
  
  const weatherData = [
    { name: '晴天', value: 5, color: '#ffd93d' },
    { name: '多云', value: 10, color: '#00d4ff' },
    { name: '小雨', value: 25, color: '#00ff88' },
    { name: '中雨', value: 45, color: '#ff6b6b' },
    { name: '大风', value: 35, color: '#a855f7' }
  ]
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '5%', right: '5%', bottom: '10%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: weatherData.map(d => d.name),
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.7)', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: '影响%',
      nameTextStyle: { color: 'rgba(255,255,255,0.5)', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
    },
    series: [{
      type: 'bar',
      barWidth: '40%',
      data: weatherData.map(d => ({
        value: d.value,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: d.color },
            { offset: 1, color: d.color.replace(')', ', 0.3)').replace('rgb', 'rgba') }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      })),
      label: { show: true, position: 'top', formatter: '{c}%', fontSize: 9, color: 'rgba(255,255,255,0.7)' }
    }]
  })
}

// 导出
const handleExport = async () => {
  exportLoading.value = true
  try {
    const blob = await exportData({ type: exportType.value, format: exportFormat.value })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${exportType.value}_${new Date().toISOString().split('T')[0]}.${exportFormat.value}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
    showExportDialog.value = false
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exportLoading.value = false
  }
}

// 窗口大小变化
const handleResize = () => charts.forEach(c => c.resize())

// 中国地图坐标（简化）
const chinaGeoCoord = {
  type: 'FeatureCollection',
  features: [
    { type: 'Feature', properties: { name: '中国' }, geometry: { type: 'Polygon', coordinates: [[[73, 18], [73, 54], [135, 54], [135, 18], [73, 18]]] } }
  ]
}

onMounted(async () => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
  
  await Promise.all([loadStats(), loadRecentOrders(), loadWeather()])
  
  initChinaMap()
  initOrderTrend()
  initOrderStatus()
  initEfficiencyRadar()
  initCostAnalysis()
  initVehicleStatus()
  initWeatherImpact()
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (timeInterval) clearInterval(timeInterval)
  window.removeEventListener('resize', handleResize)
  charts.forEach(c => c.dispose())
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #0d1033 100%);
  padding: 12px;
  color: #fff;
  position: relative;
  overflow: hidden;
}

/* 背景效果 */
.bg-effects {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.grid-lines {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(0, 212, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.04) 1px, transparent 1px);
  background-size: 50px 50px;
  animation: grid-move 20s linear infinite;
}

@keyframes grid-move {
  0% { transform: translate(0, 0); }
  100% { transform: translate(50px, 50px); }
}

.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, transparent 0%, #00d4ff 50%, transparent 100%);
  animation: scan 4s linear infinite;
  opacity: 0.6;
}

@keyframes scan {
  0% { top: -10px; opacity: 0; }
  10% { opacity: 0.6; }
  90% { opacity: 0.6; }
  100% { top: 100%; opacity: 0; }
}

.circuit-lines {
  position: absolute;
  inset: 0;
  background: 
    linear-gradient(90deg, transparent 49.5%, rgba(0, 212, 255, 0.03) 49.5%, rgba(0, 212, 255, 0.03) 50.5%, transparent 50.5%);
  background-size: 200px 200px;
  animation: circuit-pulse 3s ease-in-out infinite;
}

@keyframes circuit-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}

.corner-deco {
  position: absolute;
  width: 100px;
  height: 100px;
  border: 2px solid transparent;
  opacity: 0.3;
}

.corner-deco.top-left {
  top: 20px;
  left: 20px;
  border-top-color: #00d4ff;
  border-left-color: #00d4ff;
}

.corner-deco.top-right {
  top: 20px;
  right: 20px;
  border-top-color: #00ff88;
  border-right-color: #00ff88;
}

.corner-deco.bottom-left {
  bottom: 20px;
  left: 20px;
  border-bottom-color: #ffd93d;
  border-left-color: #ffd93d;
}

.corner-deco.bottom-right {
  bottom: 20px;
  right: 20px;
  border-bottom-color: #ff6b6b;
  border-right-color: #ff6b6b;
}

.floating-particles .particle {
  position: absolute;
  width: 3px;
  height: 3px;
  background: #00d4ff;
  border-radius: 50%;
  animation: float 5s infinite ease-in-out;
  opacity: 0.5;
}

@keyframes float {
  0%, 100% { transform: translateY(0) translateX(0); opacity: 0.3; }
  50% { transform: translateY(-20px) translateX(10px); opacity: 0.8; }
}

/* 顶部 */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  margin-bottom: 12px;
  backdrop-filter: blur(10px);
}

.logo-glow h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  background: linear-gradient(90deg, #00d4ff, #00ff88, #ffd93d, #00d4ff);
  background-size: 300% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: glow 4s linear infinite;
  text-shadow: 0 0 30px rgba(0, 212, 255, 0.3);
  letter-spacing: 2px;
}

@keyframes glow {
  0% { background-position: 0% center; }
  100% { background-position: 300% center; }
}

.subtitle {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
  letter-spacing: 2px;
  text-transform: uppercase;
}

.digital-clock {
  text-align: center;
  padding: 8px 24px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 12px;
  border: 1px solid rgba(0, 212, 255, 0.2);
}

.clock-display {
  display: flex;
  align-items: center;
  gap: 4px;
}

.clock-segment {
  font-size: 38px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
  color: #00d4ff;
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.5), 0 0 40px rgba(0, 212, 255, 0.3);
  background: rgba(0, 212, 255, 0.1);
  padding: 4px 8px;
  border-radius: 6px;
}

.clock-separator {
  font-size: 32px;
  color: #00d4ff;
  animation: blink 1s infinite;
  text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.2; }
}

.date-display {
  font-size: 12px;
  color: rgba(255,255,255,0.6);
  margin-top: 6px;
  letter-spacing: 1px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pulse-dot {
  width: 10px;
  height: 10px;
  background: #00ff88;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.5); }
  50% { box-shadow: 0 0 0 10px rgba(0, 255, 136, 0); }
}

.status-text {
  font-size: 12px;
  color: #00ff88;
}

.weather-widget {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255,255,255,0.05);
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.1);
}

.weather-icon { font-size: 20px; }
.weather-temp { font-size: 18px; font-weight: 600; color: #00d4ff; }
.weather-desc { font-size: 12px; color: rgba(255,255,255,0.5); }

/* 指标卡片 */
.metric-row { margin-bottom: 0; }

.metric-card {
  position: relative;
  padding: 16px;
  border-radius: 12px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  overflow: hidden;
  transition: all 0.3s;
}

.metric-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 212, 255, 0.5);
  box-shadow: 0 8px 32px rgba(0, 212, 255, 0.2);
}

.metric-card.gradient-cyan { border-left: 3px solid #00d4ff; }
.metric-card.gradient-green { border-left: 3px solid #00ff88; }
.metric-card.gradient-purple { border-left: 3px solid #a855f7; }
.metric-card.gradient-orange { border-left: 3px solid #ff9500; }
.metric-card.gradient-blue { border-left: 3px solid #3b82f6; }
.metric-card.gradient-pink { border-left: 3px solid #ff6b6b; }

.card-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(0, 212, 255, 0.1) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.3s;
}

.metric-card:hover .card-glow { opacity: 1; }

.card-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-icon-wrapper {
  position: relative;
  width: 40px;
  height: 40px;
}

.metric-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 24px;
}

.icon-ring {
  position: absolute;
  inset: 0;
  border: 2px solid rgba(0, 212, 255, 0.3);
  border-radius: 50%;
  animation: ring-pulse 2s infinite;
}

@keyframes ring-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0; }
}

.metric-value { display: flex; align-items: baseline; gap: 4px; }
.value-number { font-size: 28px; font-weight: 700; color: #fff; }
.value-unit { font-size: 12px; color: rgba(255,255,255,0.5); }
.metric-label { font-size: 13px; color: rgba(255,255,255,0.6); }

.metric-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}
.metric-trend.up { color: #00ff88; }
.metric-trend.warning { color: #ff9500; }
.metric-trend.neutral { color: rgba(255,255,255,0.5); }

.card-footer {
  margin-top: 8px;
  padding-top: 8px;
}

.footer-line {
  display: block;
  height: 2px;
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.5), transparent);
}

/* 图表卡片 */
.chart-card {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
  padding: 12px;
  backdrop-filter: blur(5px);
}

.large-card {
  min-height: 450px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.header-decoration {
  display: flex;
  align-items: center;
  gap: 4px;
}

.deco-line {
  width: 20px;
  height: 2px;
  background: linear-gradient(90deg, #00d4ff, transparent);
}

.deco-dot {
  width: 6px;
  height: 6px;
  background: #00d4ff;
  border-radius: 50%;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  flex: 1;
}

.card-stats {
  display: flex;
  justify-content: space-around;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.stat-name { font-size: 11px; color: rgba(255,255,255,0.5); }
.stat-value { font-size: 14px; font-weight: 600; color: #fff; }

/* 订单流 */
.stream-card { height: 300px; }

.order-stream {
  max-height: 220px;
  overflow-y: auto;
}

.stream-item {
  display: flex;
  align-items: center;
  padding: 10px;
  margin-bottom: 8px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
  border-left: 2px solid rgba(0, 212, 255, 0.3);
  transition: all 0.3s;
}

.stream-item:hover {
  background: rgba(0, 212, 255, 0.1);
  border-left-color: #00d4ff;
}

.item-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  margin-right: 10px;
}

.item-avatar.status-pending { background: rgba(0, 212, 255, 0.2); }
.item-avatar.status-assigned { background: rgba(0, 255, 136, 0.2); }
.item-avatar.status-transit { background: rgba(255, 149, 0, 0.2); }
.item-avatar.status-delivered { background: rgba(59, 130, 246, 0.2); }

.item-info { flex: 1; }
.item-id { font-size: 12px; font-weight: 500; display: block; }
.item-customer { font-size: 10px; color: rgba(255,255,255,0.4); }

.item-time { font-size: 10px; color: rgba(255,255,255,0.3); }

/* 车辆摘要 */
.vehicle-summary {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.vehicle-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.v-status { font-size: 11px; width: 50px; }
.v-count { font-size: 12px; font-weight: 500; width: 40px; }

/* 快捷操作 */
.action-card { height: 300px; }

.action-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  padding: 8px;
}

.action-btn {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16px 8px;
  border-radius: 10px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.2);
  cursor: pointer;
  transition: all 0.3s;
  overflow: hidden;
}

.action-btn:hover {
  background: rgba(0, 212, 255, 0.1);
  border-color: #00d4ff;
  transform: translateY(-2px);
}

.btn-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.btn-text {
  font-size: 11px;
  color: rgba(255,255,255,0.7);
}

.btn-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, rgba(0, 212, 255, 0.2) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.3s;
}

.action-btn:hover .btn-glow { opacity: 1; }

/* 动画 */
.stream-enter-active, .stream-leave-active {
  transition: all 0.5s ease;
}
.stream-enter-from { opacity: 0; transform: translateX(-30px); }
.stream-leave-to { opacity: 0; transform: translateX(30px); }

/* Element Plus 覆盖 */
:deep(.el-tag) {
  background: rgba(0, 212, 255, 0.2);
  border-color: rgba(0, 212, 255, 0.3);
  color: #00d4ff;
}

:deep(.el-radio-button__inner) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  color: rgba(255,255,255,0.6);
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #00d4ff;
  border-color: #00d4ff;
  color: #000;
}

:deep(.el-badge__content) {
  background: #00d4ff;
  border-color: #00d4ff;
}
</style>
