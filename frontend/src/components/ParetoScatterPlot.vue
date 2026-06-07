<template>
  <div class="pareto-scatter-plot">
    <div class="card-header">
      <div class="title-wrap">
        <span class="emoji">📈</span>
        <div>
          <h3>Pareto 前沿散点图</h3>
          <p class="subtitle">展示后端返回的方案点；是否构成真实 Pareto 前沿以 front-quality 为准</p>
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

    <el-alert
      v-if="frontQualityMeta.message"
      class="front-quality-alert"
      :type="frontQualityMeta.type"
      :closable="false"
      show-icon
      :title="frontQualityMeta.title"
      :description="frontQualityMeta.message"
    />

    <div v-if="chartData.length > 0" ref="chartRef" class="chart"></div>
    <el-empty v-else description="暂无可展示的方案点" :image-size="90" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { buildEmptyStateOption, buildScatterChartTheme, getChartPalette } from '@/utils/chartTheme'

const emit = defineEmits(['solution-click', 'solution-hover'])

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
  },
  frontQuality: {
    type: String,
    default: ''
  },
  reportedFrontCount: {
    type: Number,
    default: 0
  }
})

const chartRef = ref(null)
let chart = null
const palette = getChartPalette()

const objectiveOptions = computed(() => {
  const first = props.solutions?.[0]?.objectives || {}
  return Object.keys(first).map(key => ({
    value: key,
    label: props.objectiveLabels[key] || key
  }))
})

const xKey = ref('distance')
const yKey = ref('time')

const frontQualityMeta = computed(() => {
  const quality = props.frontQuality || inferFrontQuality()
  const count = props.reportedFrontCount || props.solutions.length
  const projectionQualities = ['single_solution_projection', 'single_solution_only', 'degenerate_front', 'low_diversity_front']

  if (!quality && props.solutions.length > 1) return { type: 'info', title: '', message: '' }

  if (projectionQualities.includes(quality)) {
    return {
      type: 'warning',
      title: frontQualityLabel(quality),
      message: quality === 'single_solution_projection'
        ? '当前是单个代表性方案点，不是真实多解 Pareto 前沿；散点图仅用于查看返回目标值。'
        : `当前返回 ${count} 个方案点，前沿多样性不足，不能宣称为完整 Pareto 解集。`
    }
  }

  if (quality) {
    return {
      type: 'info',
      title: frontQualityLabel(quality),
      message: `当前按后端返回的 ${count} 个方案点展示，是否为真实前沿以该质量标记为准。`
    }
  }

  return { type: 'info', title: '', message: '' }
})

watch(objectiveOptions, (options) => {
  if (!options.length) return
  const keys = options.map(o => o.value)
  if (!keys.includes(xKey.value)) xKey.value = keys[0]
  if (!keys.includes(yKey.value)) yKey.value = keys[Math.min(1, keys.length - 1)]
}, { immediate: true })

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
  if (type === 'weighted_best') return palette.teal
  if (type === 'single_objective') return palette.amber
  return palette.cyan
}

function inferFrontQuality() {
  if (props.solutions.length <= 1) return 'single_solution_only'
  const qualities = props.solutions.map(item => item?.front_quality).filter(Boolean)
  return qualities[0] || ''
}

function frontQualityLabel(quality) {
  const labels = {
    reported_front: '已返回前沿',
    multi_point_front: '多点前沿',
    approximate_front: '近似前沿',
    low_diversity_front: '低多样性前沿',
    degenerate_front: '退化前沿',
    single_solution_only: '单解结果',
    single_solution_projection: '单解投影'
  }
  return labels[quality] || quality || '前沿质量未标注'
}

function buildOption() {
  return buildScatterChartTheme({
    xName: labelFor(xKey.value),
    yName: labelFor(yKey.value),
    legendData: ['Pareto方案', '综合最优', '单目标最优'],
      title: '等待 Pareto 数据',
      subtitle: '当前尚未生成可展示的方案点。',
    series: [
      {
        name: 'Pareto方案',
        type: 'scatter',
        data: chartData.value.filter(d => d.type === 'pareto').map(toPoint),
        symbolSize: 18,
        emphasis: {
          scale: true,
          itemStyle: {
            shadowBlur: 22,
            shadowColor: palette.cyan
          }
        }
      },
      {
        name: '综合最优',
        type: 'scatter',
        data: chartData.value.filter(d => d.type === 'weighted_best').map(toPoint),
        symbolSize: 24,
        symbol: 'diamond',
        emphasis: {
          scale: true,
          itemStyle: {
            shadowBlur: 26,
            shadowColor: palette.teal
          }
        }
      },
      {
        name: '单目标最优',
        type: 'scatter',
        data: chartData.value.filter(d => d.type === 'single_objective').map(toPoint),
        symbolSize: 20,
        emphasis: {
          scale: true,
          itemStyle: {
            shadowBlur: 22,
            shadowColor: palette.amber
          }
        }
      }
    ]
  })
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
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
    chart.on('click', (params) => {
      if (params.data && params.data.raw) {
        emit('solution-click', params.data.raw, params.dataIndex)
      }
    })
    chart.on('mouseover', (params) => {
      if (params.data && params.data.raw) {
        emit('solution-hover', params.data.raw, params.dataIndex)
      }
    })
  }
  if (chartData.value.length === 0) {
    chart.setOption(buildEmptyStateOption('等待 Pareto 数据', '当前尚未生成可用解集。'), true)
    return
  }
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

.front-quality-alert {
  margin-bottom: 12px;
}

.chart {
  width: 100%;
  height: 360px;
}
</style>
