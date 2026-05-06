<template>
  <div class="pareto-scatter-plot">
    <div class="card-header">
      <div class="title-wrap">
        <span class="emoji">📈</span>
        <div>
          <h3>Pareto 前沿散点图</h3>
          <p class="subtitle">用二维投影直观看不同目标之间的取舍关系</p>
        </div>
      </div>

      <div class="controls">
        <el-select v-model="xKey" size="small" style="width: 140px">
          <el-option
            v-for="item in objectiveOptions"
            :key="item.value"
            :label="`X轴：${item.label}`"
            :value="item.value"
          />
        </el-select>
        <el-select v-model="yKey" size="small" style="width: 140px">
          <el-option
            v-for="item in objectiveOptions"
            :key="item.value"
            :label="`Y轴：${item.label}`"
            :value="item.value"
          />
        </el-select>
      </div>
    </div>

    <div v-if="chartData.length > 0" ref="chartRef" class="chart"></div>
    <el-empty v-else description="暂无 Pareto 数据" :image-size="90" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  solutions: {
    type: Array,
    default: () => []
  },
  objectiveLabels: {
    type: Object,
    default: () => ({
      distance: '距离',
      time: '时间',
      cost: '成本',
      traffic: '路况',
      weather_risk: '天气风险'
    })
  }
})

const chartRef = ref(null)
let chart = null

const objectiveOptions = computed(() => {
  const first = props.solutions?.[0]?.objectives || {}
  return Object.keys(first).map(key => ({
    value: key,
    label: props.objectiveLabels[key] || key
  }))
})

const xKey = ref('distance')
const yKey = ref('time')

watch(objectiveOptions, (options) => {
  if (!options.length) return
  const keys = options.map(o => o.value)
  if (!keys.includes(xKey.value)) xKey.value = keys[0]
  if (!keys.includes(yKey.value)) yKey.value = keys[Math.min(1, keys.length - 1)]
})

const chartData = computed(() => {
  return (props.solutions || [])
    .filter(item => item?.objectives && item.objectives[xKey.value] != null && item.objectives[yKey.value] != null)
    .map((item, index) => ({
      name: item.title || item.name || `方案 ${index + 1}`,
      type: item.type || 'pareto',
      description: item.description || '',
      x: Number(item.objectives[xKey.value]),
      y: Number(item.objectives[yKey.value]),
      objectives: item.objectives,
      raw: item
    }))
})

function getPointColor(type) {
  if (type === 'weighted_best') return '#67C23A'
  if (type === 'single_objective') return '#E6A23C'
  return '#409EFF'
}

function buildOption() {
  return {
    tooltip: {
      trigger: 'item',
      formatter(params) {
        const d = params.data
        const lines = [
          `<strong>${d.name}</strong>`,
          d.description || '-',
          `${labelFor(xKey.value)}: ${formatValue(d.x)}`,
          `${labelFor(yKey.value)}: ${formatValue(d.y)}`
        ]
        return lines.join('<br/>')
      }
    },
    legend: {
      bottom: 0,
      data: ['Pareto方案', '综合最优', '单目标最优']
    },
    grid: {
      left: 50,
      right: 20,
      top: 20,
      bottom: 50
    },
    xAxis: {
      type: 'value',
      name: labelFor(xKey.value),
      nameLocation: 'middle',
      nameGap: 30,
      axisLabel: {
        color: '#606266'
      }
    },
    yAxis: {
      type: 'value',
      name: labelFor(yKey.value),
      nameLocation: 'middle',
      nameGap: 40,
      axisLabel: {
        color: '#606266'
      }
    },
    series: [
      {
        name: 'Pareto方案',
        type: 'scatter',
        data: chartData.value.filter(d => d.type === 'pareto').map(toPoint),
        symbolSize: 14,
        itemStyle: { color: '#409EFF' }
      },
      {
        name: '综合最优',
        type: 'scatter',
        data: chartData.value.filter(d => d.type === 'weighted_best').map(toPoint),
        symbolSize: 18,
        itemStyle: { color: '#67C23A' }
      },
      {
        name: '单目标最优',
        type: 'scatter',
        data: chartData.value.filter(d => d.type === 'single_objective').map(toPoint),
        symbolSize: 16,
        itemStyle: { color: '#E6A23C' }
      }
    ]
  }
}

function toPoint(item) {
  return {
    value: [item.x, item.y],
    ...item,
    itemStyle: {
      color: getPointColor(item.type)
    }
  }
}

function labelFor(key) {
  return props.objectiveLabels[key] || key || '-'
}

function formatValue(value) {
  if (value == null || Number.isNaN(Number(value))) return '-'
  return Number(value).toFixed(2)
}

function renderChart() {
  if (!chartRef.value || chartData.value.length === 0) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption(buildOption(), true)
}

function resizeChart() {
  chart?.resize()
}

watch([chartData, xKey, yKey], async () => {
  await nextTick()
  renderChart()
}, { deep: true })

onMounted(async () => {
  await nextTick()
  renderChart()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.pareto-scatter-plot {
  border: 1px solid #ebeef5;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  padding: 18px;
  box-shadow: 0 6px 18px rgba(31, 35, 41, 0.06);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.title-wrap {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.emoji {
  font-size: 24px;
  line-height: 1;
}

.title-wrap h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: #909399;
}

.controls {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chart {
  width: 100%;
  height: 360px;
}
</style>
