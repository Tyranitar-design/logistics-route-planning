<template>
  <div class="dashboard">
    <div class="bg-effects">
      <div class="grid-lines"></div>
      <div class="scan-line"></div>
      <div class="circuit-lines"></div>
      <div class="floating-particles">
        <span
          v-for="i in 30"
          :key="i"
          class="particle"
          :style="getParticleStyle(i)"
        ></span>
      </div>
      <div class="corner-deco top-left"></div>
      <div class="corner-deco top-right"></div>
      <div class="corner-deco bottom-left"></div>
      <div class="corner-deco bottom-right"></div>
    </div>

    <section class="dashboard-command-layer">
      <div class="dashboard-hero">
        <div class="hero-copy cc-panel cc-panel--strong">
          <div class="hero-copy__main">
            <span class="cc-kicker">Realtime Command</span>
            <h1>物流企业级战略指挥舱</h1>
            <p>
              首屏同时汇聚调度执行、优化决策、异常风险与平台能力边界，让系统从“一个功能集合”升级为“正在运行的物流中枢”。
            </p>
          </div>

          <div class="hero-clock">
            <div class="clock-display">
              <span class="clock-segment">{{ timeHours }}</span>
              <span class="clock-separator">:</span>
              <span class="clock-segment">{{ timeMinutes }}</span>
              <span class="clock-separator">:</span>
              <span class="clock-segment">{{ timeSeconds }}</span>
            </div>
            <div class="date-display">{{ currentDate }}</div>
          </div>

          <div class="hero-chips">
            <span class="cc-chip">
              <span class="cc-dot"></span>
              系统运行中
            </span>
            <span class="cc-chip">当前调度完成率 {{ deliveryRate }}%</span>
            <span class="cc-chip" v-if="currentWeather">
              {{ getWeatherIcon(currentWeather.weather) }} {{ currentWeather.weather }} {{ currentWeather.temperature }}°C
            </span>
          </div>
        </div>

        <div class="situation-grid">
          <article
            v-for="(metric, index) in metrics"
            :key="index"
            class="metric-card cc-panel"
            :class="metric.gradient"
          >
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
          </article>
        </div>
      </div>

      <div class="dashboard-primary-grid">
        <section class="map-stage cc-panel cc-panel--strong">
          <div class="section-header">
            <div>
              <span class="cc-kicker">Realtime Dispatch</span>
              <h3>全国节点与运输态势</h3>
            </div>
            <div class="section-actions">
              <el-tag size="small" effect="dark" type="success">实时</el-tag>
              <el-button size="small" text type="primary" @click="router.push('/earth3d')">
                进入 3D 视图
              </el-button>
            </div>
          </div>
          <div ref="chinaMapChart" class="map-stage__chart"></div>
          <div class="card-stats">
            <div class="stat-item" v-for="(item, i) in mapStats" :key="i">
              <span class="stat-dot" :style="{ background: item.color }"></span>
              <span class="stat-name">{{ item.name }}</span>
              <span class="stat-value">{{ item.value }}</span>
            </div>
          </div>
        </section>

        <CommandOverviewPanel
          :delivery-rate="deliveryRate"
          :solver-label="solverLabel"
          :alert-count="alertCount"
          :pending-orders="stats.pending_orders || 0"
          :vehicle-count="stats.total_vehicles || 0"
        />
      </div>

      <div class="dashboard-secondary-grid">
        <section class="event-stream cc-panel">
          <div class="section-header">
            <div>
              <span class="cc-kicker">Event Flow</span>
              <h3>实时订单与事件流</h3>
            </div>
            <el-badge :value="recentOrders.length" type="primary" />
          </div>

          <div class="order-stream">
            <TransitionGroup name="stream">
              <div
                v-for="order in recentOrders"
                :key="order.id"
                class="stream-item"
              >
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
        </section>

        <section class="signal-column">
          <div class="chart-card cc-panel">
            <div class="card-header">
              <span class="card-title">📈 订单趋势</span>
              <el-radio-group v-model="trendRange" size="small" @change="loadOrderTrend">
                <el-radio-button label="7">7天</el-radio-button>
                <el-radio-button label="14">14天</el-radio-button>
              </el-radio-group>
            </div>
            <div ref="orderTrendChart" class="chart-card__short"></div>
          </div>

          <div class="chart-card cc-panel">
            <div class="card-header">
              <span class="card-title">🎯 订单状态</span>
            </div>
            <div ref="orderStatusChart" class="chart-card__compact"></div>
          </div>
        </section>

        <section class="monitor-column">
          <div class="chart-card cc-panel">
            <div class="card-header">
              <span class="card-title">⚡ 运输效率雷达</span>
            </div>
            <div ref="efficiencyRadar" class="chart-card__compact"></div>
          </div>

          <div class="chart-card cc-panel">
            <div class="card-header">
              <span class="card-title">💰 成本分析</span>
            </div>
            <div ref="costAnalysisChart" class="chart-card__medium"></div>
          </div>

          <div class="chart-card chart-card--oil cc-panel">
            <OilPriceCard ref="oilPriceCard" />
          </div>
        </section>
      </div>
    </section>

    <section class="dashboard-capability-layer">
      <CapabilityMatrix :capabilities="capabilityDomains" />
    </section>

    <section class="dashboard-insight-layer">
      <div class="insight-support-grid">
        <section class="insight-panel cc-panel">
          <div class="section-header">
            <div>
              <span class="cc-kicker">Operations Health</span>
              <h3>车辆状态监控</h3>
            </div>
          </div>
          <div ref="vehicleStatusChart" class="chart-card__vehicle"></div>
          <div class="vehicle-summary">
            <div class="vehicle-item" v-for="v in vehicleSummary" :key="v.status">
              <span class="v-status" :style="{ color: v.color }">{{ v.status }}</span>
              <span class="v-count">{{ v.count }}辆</span>
              <el-progress
                :percentage="v.percent"
                :stroke-width="4"
                :color="v.color"
                :show-text="false"
              />
            </div>
          </div>
        </section>

        <section class="insight-panel cc-panel">
          <div class="section-header">
            <div>
              <span class="cc-kicker">Environment</span>
              <h3>天气运输影响</h3>
            </div>
          </div>
          <div ref="weatherImpactChart" class="chart-card__weather"></div>
        </section>

        <section class="insight-panel insight-panel--actions cc-panel">
          <div class="section-header">
            <div>
              <span class="cc-kicker">Quick Actions</span>
              <h3>平台快捷入口</h3>
            </div>
          </div>
          <div class="action-grid">
            <div class="action-btn" @click="router.push('/earth3d')">
              <div class="btn-icon">🌍</div>
              <span class="btn-text">3D地球</span>
              <div class="btn-glow"></div>
            </div>
            <div class="action-btn" @click="router.push('/dispatch')">
              <div class="btn-icon">🤖</div>
              <span class="btn-text">智能调度</span>
              <div class="btn-glow"></div>
            </div>
            <div class="action-btn" @click="router.push('/multi-objective')">
              <div class="btn-icon">🎯</div>
              <span class="btn-text">多目标优化</span>
              <div class="btn-glow"></div>
            </div>
            <div class="action-btn" @click="router.push('/network-design')">
              <div class="btn-icon">🧭</div>
              <span class="btn-text">网络设计</span>
              <div class="btn-glow"></div>
            </div>
            <div class="action-btn" @click="router.push('/alert')">
              <div class="btn-icon">🚨</div>
              <span class="btn-text">预警中心</span>
              <div class="btn-glow"></div>
            </div>
            <div class="action-btn" @click="showExportDialog = true">
              <div class="btn-icon">📤</div>
              <span class="btn-text">数据导出</span>
              <div class="btn-glow"></div>
            </div>
          </div>
        </section>
      </div>

      <InsightSummaryGrid :cards="insightCards" />
    </section>

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
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import 'echarts-gl'
import { getCostComponents } from '@/api/cost'
import { exportData } from '@/api/data'
import { getNodes } from '@/api/nodes'
import { getOrders } from '@/api/orders'
import { getOverview, getOrderDistribution, getOrderTrend, getVehicleUtilization } from '@/api/stats'
import { getWeatherNow } from '@/api/weather'
import CommandOverviewPanel from '@/components/dashboard/CommandOverviewPanel.vue'
import CapabilityMatrix from '@/components/dashboard/CapabilityMatrix.vue'
import InsightSummaryGrid from '@/components/dashboard/InsightSummaryGrid.vue'
import OilPriceCard from '@/components/OilPriceCard.vue'
import {
  buildBarChartTheme,
  buildEmptyStateOption,
  buildLineChartTheme,
  buildRadarChartTheme,
  getChartPalette
} from '@/utils/chartTheme'

const router = useRouter()

const currentDate = ref('')
const timeHours = ref('00')
const timeMinutes = ref('00')
const timeSeconds = ref('00')
const currentWeather = ref(null)

const stats = reactive({
  total_nodes: 0,
  total_routes: 0,
  total_vehicles: 0,
  total_orders: 0,
  new_nodes_today: 0,
  new_routes_today: 0,
  available_vehicles: 0,
  delivered_orders: 0,
  pending_orders: 0,
  total_cost: 0
})

const animatedStats = reactive({
  total_nodes: 0,
  total_routes: 0,
  total_vehicles: 0,
  total_orders: 0,
  delivered_orders: 0,
  pending_orders: 0,
  total_cost: 0
})

const trendRange = ref('7')
const recentOrders = ref([])
const nodeCount = ref(0)

const chinaMapChart = ref(null)
const orderTrendChart = ref(null)
const orderStatusChart = ref(null)
const efficiencyRadar = ref(null)
const costAnalysisChart = ref(null)
const vehicleStatusChart = ref(null)
const weatherImpactChart = ref(null)
const oilPriceCard = ref(null)

const showExportDialog = ref(false)
const exportLoading = ref(false)
const exportType = ref('nodes')
const exportFormat = ref('xlsx')

let charts = []
let timeInterval = null
const chartPalette = getChartPalette()

const initChart = (domRef) => {
  if (!domRef) return null

  const existingInstance = echarts.getInstanceByDom(domRef)
  if (existingInstance) {
    existingInstance.dispose()
  }

  const chart = echarts.init(domRef)
  charts.push(chart)
  return chart
}

const metrics = computed(() => [
  {
    icon: '📍',
    label: '节点总数',
    key: 'total_nodes',
    gradient: 'gradient-cyan',
    trendIcon: '↑',
    trendValue: stats.new_nodes_today || 0,
    trendClass: 'up'
  },
  {
    icon: '🛣️',
    label: '路线总数',
    key: 'total_routes',
    gradient: 'gradient-green',
    trendIcon: '↑',
    trendValue: stats.new_routes_today || 0,
    trendClass: 'up'
  },
  {
    icon: '🚛',
    label: '车辆总数',
    key: 'total_vehicles',
    gradient: 'gradient-purple',
    trendIcon: '●',
    trendValue: `${stats.available_vehicles || 0} 可用`,
    trendClass: 'neutral'
  },
  {
    icon: '📦',
    label: '订单总数',
    key: 'total_orders',
    gradient: 'gradient-orange',
    trendIcon: '⏳',
    trendValue: `${stats.pending_orders || 0} 待处理`,
    trendClass: 'warning'
  },
  {
    icon: '✅',
    label: '已完成',
    key: 'delivered_orders',
    gradient: 'gradient-blue',
    trendIcon: '↑',
    trendValue: `${deliveryRate.value}%`,
    trendClass: 'up'
  },
  {
    icon: '💰',
    label: '总成本',
    key: 'total_cost',
    gradient: 'gradient-pink',
    unit: '元',
    trendIcon: '—',
    trendValue: '本月',
    trendClass: 'neutral'
  }
])

const deliveryRate = computed(() => {
  if (!stats.total_orders) return 0
  return Math.round((stats.delivered_orders / stats.total_orders) * 100)
})

const alertCount = computed(() => {
  const pending = stats.pending_orders || 0
  const utilizationGap = Math.max(0, (stats.total_vehicles || 0) - (stats.available_vehicles || 0))
  return pending + utilizationGap
})

const solverLabel = computed(() => {
  if (deliveryRate.value >= 85) return '多目标平衡高履约策略'
  if ((stats.pending_orders || 0) > 20) return '高压订单优先调度策略'
  return '稳态成本效率协同策略'
})

const mapStats = computed(() => [
  { name: '仓库', value: stats.total_nodes || 0, color: '#00d4ff' },
  { name: '配送站', value: Math.floor((stats.total_nodes || 0) * 0.3), color: '#00ff88' },
  { name: '客户点', value: Math.floor((stats.total_nodes || 0) * 0.5), color: '#ff6b6b' }
])

const vehicleSummary = computed(() => {
  const total = stats.total_vehicles || 1
  return [
    {
      status: '可用',
      count: stats.available_vehicles || 0,
      percent: Math.round(((stats.available_vehicles || 0) / total) * 100),
      color: '#00ff88'
    },
    {
      status: '运输中',
      count: Math.floor(total * 0.3),
      percent: 30,
      color: '#00d4ff'
    },
    {
      status: '维护',
      count: Math.floor(total * 0.1),
      percent: 10,
      color: '#ff6b6b'
    }
  ]
})

const capabilityDomains = computed(() => [
  {
    key: 'dispatch',
    title: '调度执行',
    icon: '🚛',
    status: '在线',
    summary: '覆盖智能调度、订单执行、车辆编排与实时轨迹监控。',
    route: '/dispatch',
    metrics: [
      { label: '当前车辆', value: `${stats.total_vehicles || 0}` },
      { label: '待处理订单', value: `${stats.pending_orders || 0}` }
    ]
  },
  {
    key: 'optimization',
    title: '优化决策',
    icon: '🎯',
    status: '增强中',
    summary: '面向优化引擎、多目标求解、Pareto 决策与场景复盘。',
    route: '/optimization-engine',
    metrics: [
      { label: '履约率', value: `${deliveryRate.value}%` },
      { label: '策略', value: '平衡型' }
    ]
  },
  {
    key: 'tracking',
    title: '地图与轨迹',
    icon: '🗺️',
    status: '在线',
    summary: '支撑地图视图、轨迹回放、三维地球与节点空间态势。',
    route: '/tracking',
    metrics: [
      { label: '节点', value: `${nodeCount.value}` },
      { label: '地图页', value: '4+' }
    ]
  },
  {
    key: 'risk',
    title: '风险预警',
    icon: '🚨',
    status: '监测中',
    summary: '承载预警中心、风险管理与异常检测能力。',
    route: '/alert',
    metrics: [
      { label: '风险数', value: `${alertCount.value}` },
      { label: '模式', value: '实时' }
    ]
  },
  {
    key: 'ai',
    title: '数据分析与 AI',
    icon: '🧠',
    status: '规划中',
    summary: '面向分析总览、AI 预测、高级能力和数据洞察模块。',
    route: '/ml-prediction',
    metrics: [
      { label: '分析页', value: '4+' },
      { label: '状态', value: '待深化' }
    ]
  },
  {
    key: 'platform',
    title: '网络与平台',
    icon: '🏗️',
    status: '扩展中',
    summary: '覆盖网络设计、采集链路、大数据监控与平台治理。',
    route: '/network-design',
    metrics: [
      { label: '平台页', value: '5+' },
      { label: '采集', value: '已接入' }
    ]
  }
])

const insightCards = computed(() => [
  {
    key: 'ai',
    title: 'AI 预测',
    status: '规划中',
    route: '/ml-prediction',
    summary: '后续将承接需求预测、资源压力与未来异常风险趋势。',
    metrics: [
      { label: '预测覆盖', value: '准备中' },
      { label: '状态', value: '待升级' }
    ]
  },
  {
    key: 'network',
    title: '网络设计',
    status: '可演进',
    route: '/network-design',
    summary: '用于仓网布局、候选点决策和企业级网络规划视图。',
    metrics: [
      { label: '候选能力', value: '已具备' },
      { label: '数据库化', value: '下一阶段' }
    ]
  },
  {
    key: 'risk',
    title: '风险风控',
    status: '运行中',
    route: '/risk',
    summary: '异常与告警能力可继续强化，后续适合接入更细粒度评分。',
    metrics: [
      { label: '事件数', value: `${alertCount.value}` },
      { label: '模式', value: '实时' }
    ]
  },
  {
    key: 'platform',
    title: '平台运行',
    status: '在线',
    route: '/redis-monitor',
    summary: '缓存、数据采集、大数据监控与运行治理统一纳入平台层。',
    metrics: [
      { label: '组件面', value: '多入口' },
      { label: '运维视角', value: '已接入' }
    ]
  }
])

const getWeatherIcon = (weather) => {
  const icons = {
    晴: '☀️',
    多云: '⛅',
    阴: '☁️',
    小雨: '🌧️',
    中雨: '🌧️',
    大雨: '⛈️'
  }
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

const getStatusClass = (status) =>
  ({
    pending: 'status-pending',
    assigned: 'status-assigned',
    in_transit: 'status-transit',
    delivered: 'status-delivered'
  }[status] || 'status-pending')

const getStatusIcon = (status) =>
  ({
    pending: '📋',
    assigned: '🚛',
    in_transit: '🚚',
    delivered: '✅'
  }[status] || '📦')

const getParticleStyle = () => ({
  left: `${Math.random() * 100}%`,
  top: `${Math.random() * 100}%`,
  animationDelay: `${Math.random() * 5}s`,
  animationDuration: `${3 + Math.random() * 4}s`
})

const updateTime = () => {
  const now = new Date()
  currentDate.value = now.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  })
  timeHours.value = String(now.getHours()).padStart(2, '0')
  timeMinutes.value = String(now.getMinutes()).padStart(2, '0')
  timeSeconds.value = String(now.getSeconds()).padStart(2, '0')
}

const animateNumber = (key, target) => {
  const duration = 1200
  const start = animatedStats[key] || 0
  const increment = (target - start) / (duration / 16)
  let current = start
  const timer = window.setInterval(() => {
    current += increment
    if ((increment > 0 && current >= target) || (increment < 0 && current <= target) || increment === 0) {
      animatedStats[key] = target
      window.clearInterval(timer)
    } else {
      animatedStats[key] = Math.round(current)
    }
  }, 16)
}

const loadStats = async () => {
  try {
    const data = await getOverview()
    Object.assign(stats, data || {})
    Object.keys(animatedStats).forEach((key) => {
      if (data?.[key] !== undefined) {
        animateNumber(key, data[key])
      }
    })
  } catch (error) {
    console.error(error)
  }
}

const loadRecentOrders = async () => {
  try {
    const res = await getOrders({ per_page: 8 })
    recentOrders.value = res.orders || []
  } catch (error) {
    console.error(error)
  }
}

const loadWeather = async () => {
  try {
    const res = await getWeatherNow('北京')
    if (res.success) {
      currentWeather.value = res.data
    }
  } catch (error) {
    console.error(error)
  }
}

const loadNodeCount = async () => {
  try {
    const res = await getNodes({ per_page: 1 })
    nodeCount.value = res.total || res.nodes?.length || 0
  } catch (error) {
    console.error(error)
  }
}

const loadOrderTrend = async () => {
  await initOrderTrend()
}

const hasMeaningfulTrend = (trendData) => trendData.some((item) => Number(item.count || item.value || 0) > 0)

const initChinaMap = async () => {
  const chart = initChart(chinaMapChart.value)
  if (!chart) return

  try {
    const response = await fetch('/china.json')
    const chinaJson = await response.json()
    echarts.registerMap('china', chinaJson)
  } catch (error) {
    console.error('加载中国地图失败:', error)
  }

  const nodeData = [
    { name: '北京总部', value: [116.46, 39.92, 100] },
    { name: '上海仓库', value: [121.48, 31.22, 90] },
    { name: '广州分拨', value: [113.23, 23.16, 82] },
    { name: '成都节点', value: [104.06, 30.67, 72] },
    { name: '武汉节点', value: [114.31, 30.52, 68] }
  ]

  const linesData = [
    { coords: [[116.46, 39.92], [121.48, 31.22]] },
    { coords: [[116.46, 39.92], [113.23, 23.16]] },
    { coords: [[121.48, 31.22], [104.06, 30.67]] },
    { coords: [[113.23, 23.16], [114.31, 30.52]] }
  ]

  chart.setOption({
    backgroundColor: 'transparent',
    geo: {
      map: 'china',
      roam: true,
      zoom: 1.05,
      label: {
        show: false
      },
      itemStyle: {
        areaColor: '#0d1f34',
        borderColor: 'rgba(0, 212, 255, 0.25)',
        borderWidth: 1
      },
      emphasis: {
        itemStyle: {
          areaColor: '#12314e'
        }
      }
    },
    series: [
      {
        type: 'lines',
        coordinateSystem: 'geo',
        zlevel: 2,
        effect: {
          show: true,
          period: 5,
          trailLength: 0.2,
          color: '#00d4ff',
          symbolSize: 3
        },
        lineStyle: {
          color: '#00d4ff',
          width: 1,
          opacity: 0.5,
          curveness: 0.2
        },
        data: linesData
      },
      {
        type: 'effectScatter',
        coordinateSystem: 'geo',
        zlevel: 3,
        rippleEffect: {
          brushType: 'stroke'
        },
        symbolSize: (val) => Math.max(10, val[2] / 6),
        itemStyle: {
          color: '#11e0b7',
          shadowBlur: 20,
          shadowColor: 'rgba(17, 224, 183, 0.5)'
        },
        data: nodeData
      }
    ]
  })
}

const initOrderTrend = async () => {
  const chart = initChart(orderTrendChart.value)
  if (!chart) return

  const data = await getOrderTrend().catch(() => ({ trend: [] }))
  const trendData = (data.trend || []).slice(0, Number(trendRange.value) || 7)

  if (!trendData.length || !hasMeaningfulTrend(trendData)) {
    chart.setOption(buildEmptyStateOption(
      '等待真实订单趋势数据',
      '当前数据时间覆盖不足，暂不绘制趋势线。'
    ), true)
    return
  }

  const values = trendData.map((item) => Number(item.count || item.value || 0))
  const peakValue = Math.max(...values)
  const peakIndex = values.findIndex((value) => value === peakValue)

  chart.setOption(buildLineChartTheme({
    categories: trendData.map((item) => item.date || item.label || ''),
    series: [
      {
        name: '订单量',
        type: 'line',
        data: values,
        markPoint: {
          symbol: 'circle',
          symbolSize: 48,
          label: {
            formatter: '峰值',
            color: '#04121f',
            fontSize: 10,
            fontWeight: 700
          },
          data: peakValue > 0 ? [{ coord: [trendData[peakIndex]?.date || '', peakValue], value: peakValue }] : [],
          itemStyle: {
            color: chartPalette.amber
          }
        }
      }
    ]
  }), true)
}

const initOrderStatus = async () => {
  const chart = initChart(orderStatusChart.value)
  if (!chart) return

  const data = await getOrderDistribution().catch(() => ({ distribution: [] }))
  const distribution = data.distribution || []
  const colors = [chartPalette.cyan, chartPalette.teal, chartPalette.amber, chartPalette.danger, chartPalette.violet]

  if (!distribution.length || distribution.every((item) => Number(item.value || 0) === 0)) {
    chart.setOption(buildEmptyStateOption(
      '等待真实状态分布',
      '当前未获得可用订单状态结构。'
    ), true)
    return
  }

  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(6, 14, 28, 0.94)',
      borderColor: 'rgba(0, 212, 255, 0.22)',
      borderWidth: 1,
      formatter: '{b}<br/>{c} 单 · {d}%'
    },
    legend: {
      bottom: 0,
      textStyle: { color: chartPalette.textSecondary, fontSize: 10 },
      itemWidth: 10,
      itemHeight: 10
    },
    series: [
      {
        name: '订单状态',
        type: 'pie',
        roseType: 'radius',
        radius: ['34%', '70%'],
        center: ['50%', '42%'],
        minAngle: 8,
        itemStyle: {
          borderRadius: 8,
          borderColor: 'rgba(3, 10, 18, 0.9)',
          borderWidth: 2
        },
        label: {
          color: chartPalette.textSecondary,
          formatter: '{b|{b}}\n{c|{d}%}',
          rich: {
            b: {
              color: chartPalette.textPrimary,
              fontSize: 11,
              fontWeight: 600
            },
            c: {
              color: chartPalette.textMuted,
              fontSize: 10
            }
          }
        },
        labelLine: {
          lineStyle: {
            color: 'rgba(255,255,255,0.2)'
          }
        },
        emphasis: {
          scale: true,
          itemStyle: {
            shadowBlur: 18,
            shadowColor: 'rgba(0, 212, 255, 0.28)'
          }
        },
        data: distribution.map((item, index) => ({
          ...item,
          itemStyle: { color: colors[index % colors.length] }
        }))
      }
    ]
  }, true)
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
    series: [
      {
        type: 'radar',
        data: [
          {
            value: [85, 72, 88, 76, 90],
            areaStyle: { color: 'rgba(0, 212, 255, 0.28)' },
            lineStyle: { color: '#00d4ff', width: 2 },
            itemStyle: { color: '#00d4ff' }
          }
        ]
      }
    ]
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

  if (!components.length) {
    chart.setOption(buildEmptyStateOption(
      '等待真实成本结构数据',
      '当前未获得可用成本构成数据。'
    ), true)
    return
  }

  chart.setOption(buildBarChartTheme({
    categories: components.map((item) => item.name),
    series: [
      {
        name: '成本',
        data: components.map((item) => item.value),
        label: {
          show: true,
          position: 'top',
          formatter: '¥{c}',
          fontSize: 10,
          color: chartPalette.textSecondary
        }
      }
    ]
  }), true)
}

const initVehicleStatus = async () => {
  const chart = initChart(vehicleStatusChart.value)
  if (!chart) return

  const data = await getVehicleUtilization().catch(() => ({ utilization: [] }))
  const colors = ['#00ff88', '#00d4ff', '#ff6b6b']
  const seriesData = data.utilization || [
    { name: '可用', value: 5 },
    { name: '运输中', value: 3 },
    { name: '维护', value: 1 }
  ]

  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['46%', '70%'],
        center: ['50%', '48%'],
        data: seriesData.map((item, index) => ({
          ...item,
          itemStyle: { color: colors[index % colors.length] }
        })),
        label: {
          show: true,
          formatter: '{b}\n{c}辆',
          color: '#fff',
          fontSize: 10
        },
        itemStyle: {
          borderRadius: 4,
          borderColor: 'rgba(0,0,0,0.2)',
          borderWidth: 2
        }
      }
    ]
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
      data: weatherData.map((item) => item.name),
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.2)' } },
      axisLabel: { color: 'rgba(255,255,255,0.7)', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: '影响%',
      nameTextStyle: { color: 'rgba(255,255,255,0.5)', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.08)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
    },
    series: [
      {
        type: 'bar',
        barWidth: '42%',
        data: weatherData.map((item) => ({
          value: item.value,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: item.color },
              { offset: 1, color: 'rgba(255,255,255,0.08)' }
            ]),
            borderRadius: [8, 8, 0, 0]
          }
        })),
        label: {
          show: true,
          position: 'top',
          formatter: '{c}%',
          fontSize: 9,
          color: 'rgba(255,255,255,0.7)'
        }
      }
    ]
  })
}

const handleExport = async () => {
  exportLoading.value = true
  try {
    const blob = await exportData({
      type: exportType.value,
      format: exportFormat.value
    })
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
  } catch (error) {
    ElMessage.error('导出失败')
  } finally {
    exportLoading.value = false
  }
}

const handleResize = () => charts.forEach((chart) => chart.resize())

onMounted(async () => {
  updateTime()
  timeInterval = window.setInterval(updateTime, 1000)

  await Promise.all([loadStats(), loadRecentOrders(), loadWeather(), loadNodeCount()])

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
  if (timeInterval) {
    window.clearInterval(timeInterval)
  }
  window.removeEventListener('resize', handleResize)
  charts.forEach((chart) => chart.dispose())
})
</script>

<style scoped>
.dashboard {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: calc(100vh - 88px);
  padding: 4px 0 8px;
  color: #fff;
  overflow: hidden;
}

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

.circuit-lines {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, transparent 49.5%, rgba(0, 212, 255, 0.03) 49.5%, rgba(0, 212, 255, 0.03) 50.5%, transparent 50.5%);
  background-size: 200px 200px;
  animation: circuit-pulse 3s ease-in-out infinite;
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

.dashboard-command-layer,
.dashboard-capability-layer,
.dashboard-insight-layer {
  position: relative;
  z-index: 1;
}

.dashboard-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 18px;
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
}

.hero-copy__main h1 {
  margin: 12px 0 10px;
  font-size: 40px;
  line-height: 1.1;
  color: var(--cc-text-primary);
}

.hero-copy__main p {
  max-width: 820px;
  color: var(--cc-text-secondary);
  line-height: 1.8;
}

.hero-clock {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}

.clock-display {
  display: flex;
  align-items: center;
  gap: 6px;
}

.clock-segment {
  font-size: 38px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
  color: #00d4ff;
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.5), 0 0 40px rgba(0, 212, 255, 0.3);
  background: rgba(0, 212, 255, 0.1);
  padding: 4px 10px;
  border-radius: 8px;
}

.clock-separator {
  font-size: 28px;
  color: #00d4ff;
  animation: blink 1s infinite;
}

.date-display {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
  letter-spacing: 1px;
}

.hero-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.situation-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  align-content: stretch;
}

.metric-card {
  position: relative;
  min-height: 128px;
  padding: 16px;
  overflow: hidden;
  transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}

.metric-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 212, 255, 0.5);
  box-shadow: 0 8px 32px rgba(0, 212, 255, 0.16);
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
  transition: opacity 0.3s ease;
}

.metric-card:hover .card-glow {
  opacity: 1;
}

.card-content {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.metric-icon-wrapper {
  position: relative;
  width: 42px;
  height: 42px;
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

.metric-value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.value-number {
  font-size: 30px;
  font-weight: 700;
  color: #fff;
}

.value-unit {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.metric-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.65);
}

.metric-trend {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.metric-trend.up { color: #00ff88; }
.metric-trend.warning { color: #ff9500; }
.metric-trend.neutral { color: rgba(255, 255, 255, 0.5); }

.dashboard-primary-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(340px, 0.9fr);
  gap: 18px;
  margin-top: 18px;
}

.map-stage {
  padding: 18px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}

.section-header h3 {
  margin: 8px 0 0;
  font-size: 22px;
  color: var(--cc-text-primary);
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.map-stage__chart {
  height: 420px;
}

.card-stats {
  display: flex;
  justify-content: space-around;
  margin-top: 14px;
  padding-top: 14px;
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

.stat-name {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.dashboard-secondary-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.9fr) minmax(0, 0.95fr);
  gap: 18px;
  margin-top: 18px;
}

.event-stream,
.chart-card,
.insight-panel {
  padding: 16px;
}

.order-stream {
  max-height: 320px;
  overflow-y: auto;
}

.stream-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 10px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 10px;
  border-left: 2px solid rgba(0, 212, 255, 0.3);
  transition: all 0.3s ease;
}

.stream-item:hover {
  background: rgba(0, 212, 255, 0.1);
  border-left-color: #00d4ff;
}

.item-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
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

.item-info {
  flex: 1;
  min-width: 0;
}

.item-id {
  display: block;
  font-size: 12px;
  font-weight: 500;
}

.item-customer {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.45);
}

.item-time {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
}

.signal-column,
.monitor-column {
  display: grid;
  gap: 16px;
}

.chart-card__short {
  height: 220px;
}

.chart-card__compact {
  height: 188px;
}

.chart-card__medium {
  height: 210px;
}

.chart-card__vehicle {
  height: 220px;
}

.chart-card__weather {
  height: 260px;
}

.chart-card--oil {
  padding: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.dashboard-capability-layer {
  margin-top: 4px;
}

.dashboard-insight-layer {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.insight-support-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.vehicle-summary {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.vehicle-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.v-status {
  width: 50px;
  font-size: 11px;
}

.v-count {
  width: 40px;
  font-size: 12px;
  font-weight: 500;
}

.insight-panel--actions {
  min-height: 100%;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.action-btn {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 18px 8px;
  border-radius: 12px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.18);
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.action-btn:hover {
  transform: translateY(-3px);
  background: rgba(0, 212, 255, 0.1);
  border-color: #00d4ff;
}

.btn-icon {
  font-size: 22px;
  margin-bottom: 8px;
}

.btn-text {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
}

.btn-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at center, rgba(0, 212, 255, 0.2) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.action-btn:hover .btn-glow {
  opacity: 1;
}

.stream-enter-active,
.stream-leave-active {
  transition: all 0.5s ease;
}

.stream-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}

.stream-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

:deep(.el-tag) {
  background: rgba(0, 212, 255, 0.16);
  border-color: rgba(0, 212, 255, 0.24);
  color: #8be9ff;
}

:deep(.el-radio-button__inner) {
  background: rgba(0, 212, 255, 0.08);
  border-color: rgba(0, 212, 255, 0.2);
  color: rgba(255, 255, 255, 0.68);
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #00d4ff;
  border-color: #00d4ff;
  color: #04121f;
}

:deep(.el-badge__content) {
  background: #00d4ff;
  border-color: #00d4ff;
}

@keyframes grid-move {
  0% { transform: translate(0, 0); }
  100% { transform: translate(50px, 50px); }
}

@keyframes scan {
  0% { top: -10px; opacity: 0; }
  10% { opacity: 0.6; }
  90% { opacity: 0.6; }
  100% { top: 100%; opacity: 0; }
}

@keyframes circuit-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.6; }
}

@keyframes float {
  0%, 100% { transform: translateY(0) translateX(0); opacity: 0.3; }
  50% { transform: translateY(-20px) translateX(10px); opacity: 0.8; }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.2; }
}

@keyframes ring-pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0; }
}

@media (max-width: 1440px) {
  .dashboard-hero,
  .dashboard-primary-grid,
  .dashboard-secondary-grid,
  .insight-support-grid {
    grid-template-columns: 1fr;
  }

  .situation-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1024px) {
  .situation-grid,
  .action-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hero-copy__main h1 {
    font-size: 32px;
  }
}

@media (max-width: 768px) {
  .dashboard {
    gap: 16px;
  }

  .hero-copy,
  .event-stream,
  .chart-card,
  .insight-panel {
    padding: 14px;
  }

  .clock-segment {
    font-size: 28px;
  }

  .hero-copy__main h1 {
    font-size: 28px;
  }

  .situation-grid,
  .action-grid {
    grid-template-columns: 1fr;
  }

  .card-stats {
    flex-wrap: wrap;
    gap: 10px;
  }
}
</style>
