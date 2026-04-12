<template>
  <div class="logistics-bigdata-screen">
    <!-- 头部 -->
    <div class="header">
      <div class="bg_header">
        <div class="header_nav fl t_title">
          物流路径规划系统 - 大数据可视化平台
        </div>
      </div>
    </div>

    <!-- 主体 -->
    <div class="data_content">
      <div class="data_time">
        当前时间：{{ currentTime }}
        <el-button type="primary" size="small" style="float: right; margin-right: 20px;" @click="goBack">返回系统</el-button>
      </div>

      <div class="data_main">
        <!-- 左侧 -->
        <div class="main_left fl">
          <!-- 订单统计 -->
          <div class="left_1">
            <div class="t_line_box"><i class="t_l_line"></i><i class="l_t_line"></i></div>
            <div class="t_line_box"><i class="t_r_line"></i><i class="r_t_line"></i></div>
            <div class="t_line_box"><i class="l_b_line"></i><i class="b_l_line"></i></div>
            <div class="t_line_box"><i class="r_b_line"></i><i class="b_r_line"></i></div>
            <div class="main_title">
              <img src="/templates/logistics-bigdata/img/t_1.png" alt="">
              各仓库订单量
            </div>
            <div ref="chart1" class="chart" style="width:100%;height: 280px;"></div>
          </div>
          
          <!-- 成本分析 -->
          <div class="left_2">
            <div class="t_line_box"><i class="t_l_line"></i><i class="l_t_line"></i></div>
            <div class="t_line_box"><i class="t_r_line"></i><i class="r_t_line"></i></div>
            <div class="t_line_box"><i class="l_b_line"></i><i class="b_l_line"></i></div>
            <div class="t_line_box"><i class="r_b_line"></i><i class="b_r_line"></i></div>
            <div class="main_title">
              <img src="/templates/logistics-bigdata/img/t_2.png" alt="">
              成本分布图
            </div>
            <div ref="chart2" class="chart" style="width:100%;height: 280px;"></div>
          </div>
        </div>

        <!-- 中间地图 -->
        <div class="main_center fl">
          <div class="center_text">
            <div class="t_line_box"><i class="t_l_line"></i><i class="l_t_line"></i></div>
            <div class="t_line_box"><i class="t_r_line"></i><i class="r_t_line"></i></div>
            <div class="t_line_box"><i class="l_b_line"></i><i class="b_l_line"></i></div>
            <div class="t_line_box"><i class="r_b_line"></i><i class="b_r_line"></i></div>
            <div class="main_title">
              <img src="/templates/logistics-bigdata/img/t_3.png" alt="">
              全国运输地图
            </div>
            <div ref="chartMap" style="width:100%;height:610px;"></div>
          </div>
        </div>

        <!-- 右侧 -->
        <div class="main_right fr">
          <!-- 车辆状态 -->
          <div class="right_1">
            <div class="t_line_box"><i class="t_l_line"></i><i class="l_t_line"></i></div>
            <div class="t_line_box"><i class="t_r_line"></i><i class="r_t_line"></i></div>
            <div class="t_line_box"><i class="l_b_line"></i><i class="b_l_line"></i></div>
            <div class="t_line_box"><i class="r_b_line"></i><i class="b_r_line"></i></div>
            <div class="main_title">
              <img src="/templates/logistics-bigdata/img/t_4.png" alt="">
              车辆状态统计
            </div>
            <div ref="chart3" class="chart" style="width:100%;height: 280px;"></div>
          </div>

          <!-- 路线排行 -->
          <div class="right_2">
            <div class="t_line_box"><i class="t_l_line"></i><i class="l_t_line"></i></div>
            <div class="t_line_box"><i class="t_r_line"></i><i class="r_t_line"></i></div>
            <div class="t_line_box"><i class="l_b_line"></i><i class="b_l_line"></i></div>
            <div class="t_line_box"><i class="r_b_line"></i><i class="b_r_line"></i></div>
            <div class="main_title">
              <img src="/templates/logistics-bigdata/img/t_5.png" alt="">
              热门路线排行
            </div>
            <div ref="chart4" class="chart" style="width:100%;height: 280px;"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'

const router = useRouter()

// 时间
const currentTime = ref('')

// 图表引用
const chart1 = ref(null)
const chart2 = ref(null)
const chartMap = ref(null)
const chart3 = ref(null)
const chart4 = ref(null)

let charts = []
let timer = null

// 返回
const goBack = () => {
  router.push('/bigdata')
}

// 更新时间
const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN')
}

// 从后端获取数据
const fetchRealData = async () => {
  try {
    const [ordersRes, vehiclesRes, routesRes] = await Promise.all([
      fetch('/api/orders/stats').then(r => r.json()),
      fetch('/api/vehicles/stats').then(r => r.json()),
      fetch('/api/routes/popular').then(r => r.json())
    ])
    
    return { orders: ordersRes, vehicles: vehiclesRes, routes: routesRes }
  } catch (e) {
    // 返回模拟数据
    return getMockData()
  }
}

// 模拟数据
const getMockData = () => ({
  orders: {
    warehouses: [
      { name: '北京仓', value: 1200 },
      { name: '上海仓', value: 980 },
      { name: '广州仓', value: 856 },
      { name: '深圳仓', value: 756 },
      { name: '成都仓', value: 623 },
      { name: '武汉仓', value: 545 }
    ]
  },
  vehicles: {
    status: [
      { name: '运输中', value: 45 },
      { name: '待命', value: 23 },
      { name: '维修', value: 5 },
      { name: '装载', value: 16 }
    ]
  },
  routes: {
    popular: [
      { name: '北京→上海', value: 89 },
      { name: '广州→深圳', value: 78 },
      { name: '上海→杭州', value: 65 },
      { name: '成都→重庆', value: 52 },
      { name: '武汉→长沙', value: 41 }
    ]
  },
  costs: [
    { name: '运输成本', value: 45 },
    { name: '仓储成本', value: 25 },
    { name: '人力成本', value: 18 },
    { name: '其他', value: 12 }
  ]
})

// 图表1：仓库订单量（玫瑰图）
const initChart1 = (data) => {
  const chart = echarts.init(chart1.value)
  charts.push(chart)
  
  const colors = ['#f845f1', '#ad46f3', '#5045f6', '#4777f5', '#44aff0', '#45dbf7']
  
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}单' },
    legend: {
      x: 'center',
      y: '15%',
      data: data.orders.warehouses.map(w => w.name),
      icon: 'circle',
      textStyle: { color: '#fff' }
    },
    series: [{
      type: 'pie',
      startAngle: 0,
      radius: [41, 100],
      center: ['50%', '55%'],
      roseType: 'area',
      avoidLabelOverlap: false,
      label: { normal: { show: true, formatter: '{c}单' } },
      data: data.orders.warehouses.map((w, i) => ({
        value: w.value,
        name: w.name,
        itemStyle: { color: colors[i % colors.length] }
      }))
    }]
  })
}

// 图表2：成本分布（柱状图）
const initChart2 = (data) => {
  const chart = echarts.init(chart2.value)
  charts.push(chart)
  
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 40, right: 20, bottom: 30, left: 50 },
    xAxis: {
      type: 'category',
      data: data.costs.map(c => c.name),
      axisLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#fff' }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#1e3a5f' } },
      axisLabel: { color: '#fff', formatter: '{value}%' }
    },
    series: [{
      type: 'bar',
      data: data.costs.map(c => c.value),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#00d4ff' },
          { offset: 1, color: '#0066cc' }
        ])
      },
      barWidth: 30
    }]
  })
}

// 图表3：车辆状态（饼图）
const initChart3 = (data) => {
  const chart = echarts.init(chart3.value)
  charts.push(chart)
  
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}辆' },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: { color: '#fff' }
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['40%', '50%'],
      avoidLabelOverlap: false,
      label: { show: true, formatter: '{b}: {c}' },
      labelLine: { show: true },
      data: data.vehicles.status.map((s, i) => ({
        value: s.value,
        name: s.name,
        itemStyle: { color: ['#00ff88', '#00d4ff', '#ffcc00', '#ff4757'][i] }
      }))
    }]
  })
}

// 图表4：热门路线（横向柱状图）
const initChart4 = (data) => {
  const chart = echarts.init(chart4.value)
  charts.push(chart)
  
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 10, right: 30, bottom: 10, left: 80 },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { show: false },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'category',
      data: data.routes.popular.map(r => r.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#fff' }
    },
    series: [{
      type: 'bar',
      data: data.routes.popular.map(r => r.value),
      barWidth: 15,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#00d4ff' },
          { offset: 1, color: '#00ff88' }
        ])
      },
      label: {
        show: true,
        position: 'right',
        color: '#00d4ff'
      }
    }]
  })
}

// 地图
const initMapChart = async (data) => {
  const chart = echarts.init(chartMap.value)
  charts.push(chart)
  
  try {
    // 加载中国地图
    const response = await fetch('/china.json')
    const chinaJson = await response.json()
    echarts.registerMap('china', chinaJson)
    
    // 飞线数据
    const lines = [
      { coords: [[116.46, 39.92], [121.48, 31.22]] },
      { coords: [[113.23, 23.16], [114.07, 22.62]] },
      { coords: [[104.06, 30.67], [106.55, 29.56]] },
      { coords: [[114.31, 30.52], [113.00, 28.21]] },
      { coords: [[120.19, 30.26], [118.78, 32.07]] }
    ]
    
    chart.setOption({
      backgroundColor: 'transparent',
      geo: {
        map: 'china',
        roam: true,
        zoom: 1.2,
        center: [105, 36],
        label: { show: false },
        itemStyle: {
          areaColor: '#0a2a4a',
          borderColor: '#00d4ff',
          borderWidth: 1
        },
        emphasis: {
          itemStyle: { areaColor: '#1a4a7a' }
        }
      },
      series: [
        // 飞线
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
          data: lines
        },
        // 城市点
        {
          type: 'effectScatter',
          coordinateSystem: 'geo',
          zlevel: 3,
          rippleEffect: { brushType: 'stroke', scale: 4 },
          symbol: 'circle',
          symbolSize: 10,
          itemStyle: {
            color: '#00d4ff',
            shadowColor: 'rgba(0, 212, 255, 0.8)',
            shadowBlur: 10
          },
          data: [
            { name: '北京', value: [116.46, 39.92, 100] },
            { name: '上海', value: [121.48, 31.22, 90] },
            { name: '广州', value: [113.23, 23.16, 80] },
            { name: '深圳', value: [114.07, 22.62, 75] },
            { name: '成都', value: [104.06, 30.67, 70] },
            { name: '武汉', value: [114.31, 30.52, 65] },
            { name: '杭州', value: [120.19, 30.26, 60] }
          ]
        }
      ]
    })
  } catch (e) {
    console.error('地图加载失败:', e)
  }
}

// 初始化所有图表
const initAllCharts = async () => {
  const data = await fetchRealData()
  
  initChart1(data)
  initChart2(data)
  initChart3(data)
  initChart4(data)
  await initMapChart(data)
  
  // 响应式
  window.addEventListener('resize', () => {
    charts.forEach(c => c.resize())
  })
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
  
  setTimeout(initAllCharts, 100)
})

onUnmounted(() => {
  clearInterval(timer)
  charts.forEach(c => c.dispose())
})
</script>

<style scoped>
/* 引入模板样式 */
@import url('/templates/logistics-bigdata/css/bootstrap.css');
@import url('/templates/logistics-bigdata/css/base.css');
@import url('/templates/logistics-bigdata/css/index.css');

.logistics-bigdata-screen {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: url('/templates/logistics-bigdata/img/true.png') no-repeat center center;
  background-size: 100% 100%;
}

.t_title {
  width: 100%;
  height: 100%;
  text-align: center;
  font-size: 2.5em;
  line-height: 80px;
  color: #fff;
}

.chart {
  width: 100%;
}
</style>
