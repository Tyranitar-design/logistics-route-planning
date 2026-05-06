<template>
  <div class="parallel-coordinates-chart">
    <div class="card-header">
      <div class="title-wrap">
        <span class="emoji">🪢</span>
        <div>
          <h3>平行坐标图</h3>
          <p class="subtitle">直观看不同方案在多个目标维度上的取舍关系</p>
        </div>
      </div>
    </div>

    <div v-if="seriesData.length > 0" ref="chartRef" class="chart"></div>
    <el-empty v-else description="暂无多目标方案数据" :image-size="90" />
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

const objectiveKeys = computed(() => {
  const first = props.solutions?.find(item => item?.objectives)?.objectives || {}
  return Object.keys(first)
})

const dimensions = computed(() => {
  return objectiveKeys.value.map((key) => {
    const values = props.solutions
      .map(item => item?.objectives?.[key])
      .filter(v => v != null)
      .map(v => Number(v))

    const min = values.length ? Math.min(...values) : 0
    const max = values.length ? Math.max(...values) : 100

    return {
      dim: key,
      name: props.objectiveLabels[key] || key,
      min,
      max: max === min ? max + 1 : max
    }
  })
})

const seriesData = computed(() => {
  return (props.solutions || [])
    .filter(item => item?.objectives)
    .map((item, index) => {
      const row = {}
      objectiveKeys.value.forEach((key) => {
        row[key] = Number(item.objectives[key] ?? 0)
      })
      row.__name = item.title || item.name || `方案 ${index + 1}`
      row.__type = item.type || 'pareto'
      row.__raw = item
      return row
    })
})

function getColor(type) {
  if (type === 'weighted_best') return '#67C23A'
  if (type === 'single_objective') return '#E6A23C'
  return '#409EFF'
}

function buildOption() {
  return {
    tooltip: {
      trigger: 'item',
      formatter(params) {
        const raw = params.data || {}
        const lines = [`<strong>${raw.__name || '方案'}</strong>`]
        objectiveKeys.value.forEach((key) => {
          lines.push(`${props.objectiveLabels[key] || key}: ${formatValue(raw[key])}`)
        })
        return lines.join('<br/>')
      }
    },
    parallelAxis: dimensions.value.map((item, index) => ({
      dim: index,
      name: item.name,
      min: item.min,
      max: item.max,
      nameLocation: 'end',
      nameGap: 8,
      axisLabel: {
        color: '#606266'
      }
    })),
    parallel: {
      left: 40,
      right: 40,
      top: 40,
      bottom: 30,
      parallelAxisDefault: {
        type: 'value',
        nameTextStyle: {
          color: '#303133',
          fontWeight: 600,
          fontSize: 12
        },
        axisLine: {
          lineStyle: {
            color: '#dcdfe6'
          }
        },
        axisTick: {
          show: false
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: '#f0f2f5'
          }
        }
      }
    },
    series: seriesData.value.map((item) => ({
      type: 'parallel',
      name: item.__name,
      lineStyle: {
        width: item.__type === 'weighted_best' ? 3 : 2,
        color: getColor(item.__type),
        opacity: item.__type === 'weighted_best' ? 0.95 : 0.75
      },
      emphasis: {
        lineStyle: {
          width: 4,
          opacity: 1
        }
      },
      data: [objectiveKeys.value.map(key => item[key])]
    }))
  }
}

function formatValue(value) {
  if (value == null || Number.isNaN(Number(value))) return '-'
  return Number(value).toFixed(2)
}

function renderChart() {
  if (!chartRef.value || !seriesData.value.length || !objectiveKeys.value.length) return
  if (!chart) chart = echarts.init(chartRef.value)
  chart.setOption(buildOption(), true)
}

function resizeChart() {
  chart?.resize()
}

watch([seriesData, dimensions], async () => {
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
.parallel-coordinates-chart {
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

.chart {
  width: 100%;
  height: 380px;
}
</style>
