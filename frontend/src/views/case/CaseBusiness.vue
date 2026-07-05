<template>
  <div class="case-page">
    <header class="page-hero">
      <h1>📊 核心业务范畴</h1>
      <p>SLA 准时率 · 覆盖率 · 产能 · 履约率 — 案例端到端业务指标</p>
    </header>
    <div class="kpi-grid">
      <div class="kpi-card big"><span>SLA（48h 准时率）</span><strong>{{ pct(kpi.sla) }}%</strong><small>{{ kpi.sla }}</small></div>
      <div class="kpi-card big"><span>区域覆盖率</span><strong>{{ pct(kpi.coverage) }}%</strong><small>{{ kpi.c2c_clusters }}/{{ kpi.total_regions }} 区域</small></div>
      <div class="kpi-card big"><span>果园产能</span><strong>{{ summary.capacity_label || '-' }}</strong><small>{{ kpi.capacity_boxes }} 箱</small></div>
      <div class="kpi-card big"><span>履约率</span><strong>{{ pct(kpi.fulfillment) }}%</strong><small>车容 {{ kpi.vehicle_capacity_kg }}kg / 需求 {{ kpi.b2b_demand_kg }}kg</small></div>
    </div>
    <section class="panel">
      <h2>SLA 仪表盘（48h 可达率）</h2>
      <div ref="gaugeRef" class="biz-chart"></div>
    </section>
    <section class="panel">
      <h2>覆盖率 & 履约率对比</h2>
      <div ref="barRef" class="biz-chart"></div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getFoodSupplyBusinessKpi } from '@/api/foodSupplyCase'

const kpi = ref({})
const summary = ref({})
const gaugeRef = ref(null)
const barRef = ref(null)
const pct = (v) => Math.round((v || 0) * 100)

function renderCharts() {
  if (gaugeRef.value) {
    echarts.init(gaugeRef.value).setOption({
      series: [{ type: 'gauge', startAngle: 200, endAngle: -20, min: 0, max: 100,
        progress: { show: true, width: 18, itemStyle: { color: '#5eead4' } },
        axisLine: { lineStyle: { width: 18, color: [[0.3, '#ff6b6b'], [0.7, '#faad14'], [1, '#52c41a']] } },
        detail: { valueAnimation: true, formatter: '{value}%', color: '#a8d8ff', fontSize: 28, offsetCenter: [0, '70%'] },
        data: [{ value: pct(kpi.value.sla), name: 'SLA' }],
        title: { color: '#7a8fb0', fontSize: 12, offsetCenter: [0, '-30%'] } }],
    })
  }
  if (barRef.value) {
    echarts.init(barRef.value).setOption({
      tooltip: {}, grid: { left: 60, right: 30, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: ['覆盖率', '履约率'], axisLabel: { color: '#9bb3d4' } },
      yAxis: { type: 'value', max: 100, axisLabel: { color: '#7a8fb0', formatter: '{value}%' } },
      series: [{ type: 'bar', data: [pct(kpi.value.coverage), pct(kpi.value.fulfillment)], itemStyle: { color: '#5eead4', borderRadius: [4, 4, 0, 0] }, barWidth: 50, label: { show: true, position: 'top', color: '#a8d8ff', formatter: '{c}%' } }],
    })
  }
}

async function load() {
  try {
    const res = await getFoodSupplyBusinessKpi()
    kpi.value = res.kpi || {}; summary.value = res.summary || {}
    await nextTick(); renderCharts()
  } catch (e) { ElMessage.error('业务 KPI 加载失败：' + (e.message || '后端未启动')) }
}
onMounted(load)
</script>

<style scoped>
.case-page { color: #e6f0ff; }
.page-hero { margin-bottom: 18px; }
.page-hero h1 { margin: 0 0 4px; font-size: 22px; color: #a8d8ff; }
.page-hero p { margin: 0; color: #7a8fb0; font-size: 13px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; margin-bottom: 18px; }
.kpi-card { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 16px; display: flex; flex-direction: column; gap: 4px; }
.kpi-card.big strong { font-size: 26px; color: #5eead4; }
.kpi-card span { font-size: 11px; color: #7a8fb0; }
.kpi-card small { font-size: 11px; color: #5a7090; }
.panel { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.panel h2 { margin: 0 0 12px; font-size: 15px; color: #a8d8ff; }
.biz-chart { height: 320px; width: 100%; }
</style>
