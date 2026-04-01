<template>
  <div class="route-compare-chart">
    <!-- 雷达图对比 -->
    <div class="radar-section">
      <h3>📊 方案对比雷达图</h3>
      <div ref="radarChartRef" class="radar-chart"></div>
    </div>
    
    <!-- 柱状图对比 -->
    <div class="bar-section">
      <h3>📈 各指标详情</h3>
      <div ref="barChartRef" class="bar-chart"></div>
    </div>
    
    <!-- 方案详情表格 -->
    <div class="table-section">
      <h3>📋 方案详情</h3>
      <el-table :data="tableData" stripe style="width: 100%">
        <el-table-column prop="name" label="方案" width="120" />
        <el-table-column prop="distance" label="距离 (km)" width="100">
          <template #default="{ row }">
            <span :class="getScoreClass(row, 'distance')">
              {{ row.distance?.toFixed(1) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="time" label="时间 (min)" width="100">
          <template #default="{ row }">
            <span :class="getScoreClass(row, 'time')">
              {{ row.time?.toFixed(1) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="cost" label="成本 (元)" width="100">
          <template #default="{ row }">
            <span :class="getScoreClass(row, 'cost')">
              {{ row.cost?.toFixed(1) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="traffic" label="路况" width="80">
          <template #default="{ row }">
            <el-tag :type="getTrafficType(row.traffic)" size="small">
              {{ row.traffic?.toFixed(0) }}分
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="weather_risk" label="天气风险" width="100">
          <template #default="{ row }">
            <el-tag :type="getRiskType(row.weather_risk)" size="small">
              {{ row.weather_risk?.toFixed(0) }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="isPareto" label="Pareto最优" width="100">
          <template #default="{ row }">
            <el-icon v-if="row.isPareto" color="#67C23A"><Select /></el-icon>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <!-- 推荐说明 -->
    <div v-if="recommendation" class="recommendation-section">
      <el-alert
        :title="recommendation.title"
        type="success"
        :description="recommendation.description"
        show-icon
        :closable="false"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Select } from '@element-plus/icons-vue'

const props = defineProps({
  routes: {
    type: Array,
    default: () => []
  },
  selectedIndices: {
    type: Array,
    default: () => []
  }
})

const radarChartRef = ref(null)
const barChartRef = ref(null)
let radarChart = null
let barChart = null

// 表格数据
const tableData = computed(() => {
  return props.routes.map((route, index) => ({
    name: route.title || `方案 ${index + 1}`,
    distance: route.objectives?.distance,
    time: route.objectives?.time,
    cost: route.objectives?.cost,
    traffic: route.objectives?.traffic,
    weather_risk: route.objectives?.weather_risk,
    isPareto: route.type === 'pareto' || route.isPareto
  }))
})

// 推荐方案
const recommendation = computed(() => {
  const weighted = props.routes.find(r => r.type === 'weighted_best')
  if (weighted) {
    return {
      title: '💡 推荐方案',
      description: `${weighted.title}：${weighted.description}`
    }
  }
  return null
})

// 获取分数样式类
function getScoreClass(row, field) {
  const values = tableData.value.map(r => r[field]).filter(v => v != null)
  if (values.length === 0) return ''
  
  const min = Math.min(...values)
  const max = Math.max(...values)
  const value = row[field]
  
  if (value === min) return 'score-best'
  if (value === max) return 'score-worst'
  return ''
}

// 获取路况标签类型
function getTrafficType(score) {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

// 获取风险标签类型
function getRiskType(risk) {
  if (risk <= 20) return 'success'
  if (risk <= 50) return 'warning'
  return 'danger'
}

// 初始化雷达图
function initRadarChart() {
  if (!radarChartRef.value) return
  
  if (radarChart) {
    radarChart.dispose()
  }
  
  radarChart = echarts.init(radarChartRef.value)
  
  const indicators = [
    { name: '距离', max: 100 },
    { name: '时间', max: 100 },
    { name: '成本', max: 100 },
    { name: '路况', max: 100 },
    { name: '天气风险', max: 100 }
  ]
  
  // 归一化数据
  const seriesData = props.routes.slice(0, 5).map((route, index) => {
    const obj = route.objectives || {}
    return {
      name: route.title || `方案 ${index + 1}`,
      value: [
        normalizeValue(obj.distance, 0, 3000, true),  // 距离最大 3000km
        normalizeValue(obj.time, 0, 500, true),       // 时间最大 500min
        normalizeValue(obj.cost, 0, 10000, true),     // 成本最大 10000元
        normalizeValue(obj.traffic, 0, 100, false),
        normalizeValue(obj.weather_risk, 0, 100, true)
      ],
      itemStyle: {
        color: getColor(index)
      }
    }
  })
  
  const option = {
    tooltip: {
      trigger: 'item'
    },
    legend: {
      bottom: 0,
      data: seriesData.map(s => s.name)
    },
    radar: {
      shape: 'polygon',
      splitNumber: 5,
      axisName: {
        color: '#606266'
      },
      splitLine: {
        lineStyle: {
          color: '#e4e7ed'
        }
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['rgba(64, 158, 255, 0.05)', 'rgba(64, 158, 255, 0.1)']
        }
      },
      indicator: indicators
    },
    series: [{
      type: 'radar',
      data: seriesData,
      emphasis: {
        lineStyle: {
          width: 3
        }
      }
    }]
  }
  
  radarChart.setOption(option)
}

// 初始化柱状图
function initBarChart() {
  if (!barChartRef.value) return
  
  if (barChart) {
    barChart.dispose()
  }
  
  barChart = echarts.init(barChartRef.value)
  
  const routes = props.routes.slice(0, 5)
  const xData = routes.map((r, i) => r.title || `方案 ${i + 1}`)
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    legend: {
      bottom: 0,
      data: ['距离(km)', '时间(min)', '成本(×10元)']
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xData
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '距离(km)',
        type: 'bar',
        data: routes.map(r => r.objectives?.distance?.toFixed(1) || 0),
        itemStyle: { color: '#409EFF' }
      },
      {
        name: '时间(min)',
        type: 'bar',
        data: routes.map(r => r.objectives?.time?.toFixed(1) || 0),
        itemStyle: { color: '#67C23A' }
      },
      {
        name: '成本(×10元)',
        type: 'bar',
        data: routes.map(r => (r.objectives?.cost / 10)?.toFixed(1) || 0),
        itemStyle: { color: '#E6A23C' }
      }
    ]
  }
  
  barChart.setOption(option)
}

// 归一化数值
function normalizeValue(value, min, max, inverse = false) {
  if (value == null) return 50
  
  const normalized = ((value - min) / (max - min)) * 100
  const clamped = Math.max(0, Math.min(100, normalized))
  
  // 如果是逆向指标（越小越好），则取反
  return inverse ? (100 - clamped) : clamped
}

// 获取颜色
function getColor(index) {
  const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399']
  return colors[index % colors.length]
}

// 窗口大小变化时重绘
function handleResize() {
  radarChart?.resize()
  barChart?.resize()
}

// 监听数据变化
watch(() => props.routes, () => {
  nextTick(() => {
    initRadarChart()
    initBarChart()
  })
}, { deep: true })

onMounted(() => {
  nextTick(() => {
    initRadarChart()
    initBarChart()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  radarChart?.dispose()
  barChart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.route-compare-chart {
  padding: 16px;
}

.radar-section,
.bar-section,
.table-section {
  margin-bottom: 24px;
}

.radar-section h3,
.bar-section h3,
.table-section h3 {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

.radar-chart,
.bar-chart {
  width: 100%;
  height: 300px;
}

.score-best {
  color: #67C23A;
  font-weight: 600;
}

.score-worst {
  color: #F56C6C;
}

.recommendation-section {
  margin-top: 16px;
}
</style>
