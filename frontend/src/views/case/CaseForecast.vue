<template>
  <div class="case-page">
    <header class="page-hero">
      <h1>📈 时序 & 需求预测</h1>
      <p>果园 92 天逐日箱数 · deterministic / lightgbm / optuna 三级预测 · 保鲜采摘波次</p>
      <div class="hero-actions">
        <el-radio-group v-model="mode" size="small" @change="load">
          <el-radio-button label="deterministic">确定性基线</el-radio-button>
          <el-radio-button label="lightgbm">lightgbm</el-radio-button>
          <el-radio-button label="optuna">optuna 调参</el-radio-button>
        </el-radio-group>
        <el-button size="small" :loading="loading" @click="load">刷新</el-button>
      </div>
    </header>
    <div class="kpi-grid">
      <div class="kpi-card"><span>果园数</span><strong>{{ forecast?.forecast?.length || 0 }}</strong></div>
      <div class="kpi-card"><span>预测模型</span><strong>{{ forecast?.model_stage || '-' }}</strong></div>
      <div class="kpi-card"><span>预测天数</span><strong>{{ forecast?.summary?.horizon || 0 }}</strong></div>
      <div class="kpi-card"><span>保鲜窗口</span><strong>{{ forecast?.summary?.freshness_days || 0 }} 天</strong></div>
      <div class="kpi-card"><span>季总箱数</span><strong>{{ timeseries?.summary?.season_total_boxes || 0 }}</strong></div>
    </div>
    <section class="panel">
      <div class="panel-title">
        <h2>📈 预测曲线（历史 92 天 + 预测 14 天）</h2>
        <el-select v-model="selectedOrchard" size="small" style="width:200px" @change="renderChart">
          <el-option v-for="o in orchardOptions" :key="o.code" :label="o.name" :value="o.code" />
        </el-select>
      </div>
      <div ref="chartRef" class="forecast-chart"></div>
      <small style="color:#5a7090">蓝实线=历史 · 青虚线=预测 · 青色背景=采摘波次窗口</small>
    </section>
    <section class="panel">
      <h2>92 天时序摘要</h2>
      <el-table :data="timeseries?.series || []" height="260">
        <el-table-column prop="orchard_code" label="果园" width="110" />
        <el-table-column prop="name" label="名称" min-width="100" />
        <el-table-column prop="total_boxes" label="92天总箱数" width="130" />
        <el-table-column prop="peak_day_boxes" label="峰值" width="100" />
        <el-table-column prop="mean_boxes" label="日均" width="100" />
      </el-table>
    </section>
    <section class="panel">
      <h2>需求预测 + 采摘波次（{{ mode }}）</h2>
      <el-table :data="forecast?.forecast || []" height="320">
        <el-table-column prop="orchard_code" label="果园" width="110" />
        <el-table-column prop="name" label="名称" min-width="100" />
        <el-table-column prop="moving_avg_7" label="7日均" width="90" />
        <el-table-column prop="trend" label="趋势" width="80" />
        <el-table-column v-if="forecast?.forecast?.[0]?.best_params" prop="best_params" label="最优参数" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ JSON.stringify(row.best_params) }}</template>
        </el-table-column>
        <el-table-column v-if="forecast?.forecast?.[0]?.validation_mae !== undefined" prop="validation_mae" label="验证MAE" width="100" />
        <el-table-column label="预测14天合计" width="120">
          <template #default="{ row }">{{ (row.forecast_daily || []).reduce((s, d) => s + d.predicted_boxes, 0) }}</template>
        </el-table-column>
        <el-table-column label="采摘波次" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">{{ (row.harvest_waves || []).map(w => `${w.wave_date}(${w.boxes}箱/${w.days}天)`).join('，') }}</template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getFoodSupplyOrchardTimeseries, getFoodSupplyOrchardForecast } from '@/api/foodSupplyCase'

const timeseries = ref(null)
const forecast = ref(null)
const loading = ref(false)
const mode = ref('deterministic')
const chartRef = ref(null)
const selectedOrchard = ref('')
const orchardOptions = computed(() => (timeseries.value?.series || []).map(o => ({ code: o.orchard_code, name: o.name })))

function renderChart() {
  if (!chartRef.value || !timeseries.value) return
  const orchard = (timeseries.value.series || []).find(o => o.orchard_code === selectedOrchard.value) || timeseries.value.series?.[0]
  if (!orchard) return
  const chart = echarts.init(chartRef.value)
  const daily = orchard.daily || []
  const fcOrchard = (forecast.value?.forecast || []).find(o => o.orchard_code === orchard.orchard_code)
  const fdaily = fcOrchard?.forecast_daily || []
  const waves = fcOrchard?.harvest_waves || []
  const lastDate = fdaily.length ? fdaily[fdaily.length - 1].date : '09-14'
  const markAreas = waves.map(w => [{ xAxis: w.wave_date }, { xAxis: lastDate }])
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: '#aac' }, top: 0, data: ['历史 92 天', '预测 14 天'] },
    grid: { left: 70, right: 30, top: 40, bottom: 40 },
    xAxis: { type: 'category', axisLabel: { color: '#7a8fb0', fontSize: 10, interval: 6 } },
    yAxis: { type: 'value', name: '箱数', nameTextStyle: { color: '#7a8fb0' }, axisLabel: { color: '#7a8fb0' }, splitLine: { lineStyle: { color: 'rgba(120,200,255,0.08)' } } },
    series: [
      { name: '历史 92 天', type: 'line', data: daily.map(d => d.boxes), showSymbol: false, smooth: true, lineStyle: { color: '#1890ff', width: 2 }, itemStyle: { color: '#1890ff' } },
      { name: '预测 14 天', type: 'line', data: [...new Array(daily.length - 1).fill(null), daily[daily.length - 1]?.boxes, ...fdaily.map(d => d.predicted_boxes)], showSymbol: true, smooth: true, lineStyle: { color: '#5eead4', width: 2, type: 'dashed' }, itemStyle: { color: '#5eead4' }, symbolSize: 6,
        markArea: { itemStyle: { color: 'rgba(94,234,212,0.10)' }, data: markAreas, label: { show: true, color: '#5eead4', fontSize: 10, formatter: () => '采摘波次' } } },
    ],
  })
}

async function load() {
  loading.value = true
  try {
    const [ts, fc] = await Promise.all([
      getFoodSupplyOrchardTimeseries(),
      getFoodSupplyOrchardForecast({ horizon: 14, freshness_days: 4, use_ml: mode.value === 'lightgbm' ? 1 : 0, use_optuna: mode.value === 'optuna' ? 1 : 0 }),
    ])
    timeseries.value = ts
    forecast.value = fc
    if (!selectedOrchard.value && ts.series?.length) selectedOrchard.value = ts.series[0].orchard_code
    await nextTick()
    renderChart()
  } catch (e) { ElMessage.error('预测加载失败：' + (e.message || '后端未启动')) }
  finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.case-page { color: #e6f0ff; }
.page-hero { margin-bottom: 18px; }
.page-hero h1 { margin: 0 0 4px; font-size: 22px; color: #a8d8ff; }
.page-hero p { margin: 0 0 10px; color: #7a8fb0; font-size: 13px; }
.hero-actions { display: flex; gap: 12px; align-items: center; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; margin-bottom: 18px; }
.kpi-card { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 4px; }
.kpi-card span { font-size: 11px; color: #7a8fb0; }
.kpi-card strong { font-size: 20px; color: #5eead4; }
.panel { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.panel h2 { margin: 0 0 12px; font-size: 15px; color: #a8d8ff; }
.forecast-chart { height: 360px; width: 100%; }
.panel-title { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
</style>
