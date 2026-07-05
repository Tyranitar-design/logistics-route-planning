<template>
  <div class="case-page">
    <header class="page-hero">
      <h1>✈️ 空运多式联运</h1>
      <p>纯陆运 vs 空+陆 vs 空+无人机 · B747-8F(135t/426km/h) · 27 货运机场</p>
      <div class="hero-actions">
        <el-button size="small" :loading="loading" @click="load">刷新对比</el-button>
      </div>
    </header>
    <div class="kpi-grid">
      <div class="kpi-card"><span>聚类数</span><strong>{{ result?.summary?.cluster_count || 0 }}</strong></div>
      <div class="kpi-card"><span>空运可行</span><strong>{{ result?.summary?.air_feasible_clusters || 0 }}</strong></div>
      <div class="kpi-card"><span>货运机场已编码</span><strong>{{ result?.constraint_validation?.freight_airports_geocoded || 0 }}</strong></div>
      <div class="kpi-card"><span>飞机载重</span><strong>{{ Math.round(result?.constraint_validation?.aircraft_payload_kg || 0) }} kg</strong></div>
      <div class="kpi-card"><span>真实性</span><strong>{{ result?.authenticity_level || '-' }}</strong></div>
    </div>
    <section class="panel">
      <h2>📊 三模式成本/时效/碳排对比（归一化%）</h2>
      <div ref="chartRef" class="mm-chart"></div>
    </section>
    <section class="panel">
      <h2>三模式对比明细</h2>
      <el-table :data="result?.clusters || []" height="420">
        <el-table-column prop="cluster" label="区域" min-width="100" />
        <el-table-column prop="weight_kg" label="重量(kg)" width="90" />
        <el-table-column prop="nearest_freight_airport" label="最近货运机场" min-width="150" show-overflow-tooltip />
        <el-table-column label="纯陆运" min-width="180"><template #default="{ row }">{{ fmt(row, 'pure_road') }}</template></el-table-column>
        <el-table-column label="空+陆" min-width="180"><template #default="{ row }">{{ fmt(row, 'air_plus_road') }}</template></el-table-column>
        <el-table-column label="空+无人机" min-width="180"><template #default="{ row }">{{ fmt(row, 'air_plus_drone') }}</template></el-table-column>
        <el-table-column prop="recommended_mode" label="推荐" width="110" />
      </el-table>
    </section>
    <section class="panel">
      <h2>📐 CFLP 仓网选址数学模型</h2>
      <pre class="math-model">{{ cflpModel }}</pre>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { optimizeFoodSupplyMultimodal } from '@/api/foodSupplyCase'

const result = ref(null)
const loading = ref(false)
const chartRef = ref(null)

const cflpModel = `CFLP（Capacitated Facility Location Problem）仓网选址-分配模型

目标 Objective:
  min  Σ_j f_j · y_j + Σ_i Σ_j c_ij · x_ij          // 设施开放固定成本 + 顾客-设施分配运输成本

约束 Constraints:
  (1) Σ_j x_ij = 1            ∀ i ∈ Customers        // 每顾客恰分配到一个设施
  (2) x_ij ≤ y_j              ∀ i, j                 // 只能分配到已开放设施
  (3) Σ_j y_j ≤ P                                   // 最多开放 P 个候选设施（案例 = 2）
  (4) Σ_i q_i · x_ij ≤ Q_j    ∀ j                    // 设施容量（吞吐量上限）
  (5) y_j ∈ {0,1}, x_ij ∈ {0,1}                      // 0-1 决策变量

多式联运扩展（案例）:
  • 果园 → 始发机场（车辆）：c = d × cost_per_km
  • 始发机场 → 货运机场（B747-8F）：c = weight × 1.17 元/kg
  • 货运机场 → C 端聚类（车辆/无人机）：含续航约束
  • 决策：设施选址 y_j + 运输模式 z_mode

求解器: greedy CFLP baseline（默认） / Gurobi MILP 精确解（已有 _try_milp_network_design hook）`

function fmt(row, mode) {
  const m = (row.modes || []).find(x => x.mode === mode)
  if (!m) return '-'
  const tag = m.feasible ? '' : ' (不可行)'
  return `${m.cost} 元 / ${m.duration_min} min${tag}`
}

function renderChart() {
  if (!chartRef.value || !result.value) return
  const chart = echarts.init(chartRef.value)
  const cls = result.value.clusters || []
  const modes = ['pure_road', 'air_plus_road', 'air_plus_drone']
  const labels = ['纯陆运', '空+陆', '空+无人机']
  const agg = modes.map(m => {
    const cost = cls.reduce((s, c) => s + ((c.modes || []).find(x => x.mode === m && x.feasible)?.cost || 0), 0)
    const dur = cls.reduce((s, c) => s + ((c.modes || []).find(x => x.mode === m && x.feasible)?.duration_min || 0), 0)
    const carbon = cls.reduce((s, c) => s + ((c.modes || []).find(x => x.mode === m && x.feasible)?.carbon_kg || 0), 0)
    return { cost: Math.round(cost), dur: Math.round(dur), carbon: Math.round(carbon) }
  })
  const maxCost = Math.max(...agg.map(a => a.cost)) || 1
  const maxDur = Math.max(...agg.map(a => a.dur)) || 1
  const maxCarbon = Math.max(...agg.map(a => a.carbon)) || 1
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: '#aac' }, top: 0 },
    grid: { left: 50, right: 30, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: labels, axisLabel: { color: '#9bb3d4' } },
    yAxis: { type: 'value', max: 100, axisLabel: { color: '#7a8fb0', formatter: '{value}%' } },
    series: [
      { name: '成本(归一)', type: 'bar', data: agg.map(a => Math.round(a.cost / maxCost * 100)), itemStyle: { color: '#1890ff', borderRadius: [4, 4, 0, 0] } },
      { name: '时效(归一)', type: 'bar', data: agg.map(a => Math.round(a.dur / maxDur * 100)), itemStyle: { color: '#5eead4', borderRadius: [4, 4, 0, 0] } },
      { name: '碳排(归一)', type: 'bar', data: agg.map(a => Math.round(a.carbon / maxCarbon * 100)), itemStyle: { color: '#52c41a', borderRadius: [4, 4, 0, 0] } },
    ],
  })
}

async function load() {
  loading.value = true
  try {
    const res = await optimizeFoodSupplyMultimodal({ cluster_limit: 10, persist: false })
    result.value = res
    await nextTick()
    renderChart()
  } catch (e) { ElMessage.error('多式联运加载失败：' + (e.message || '后端未启动')) }
  finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.case-page { color: #e6f0ff; }
.page-hero { margin-bottom: 18px; }
.page-hero h1 { margin: 0 0 4px; font-size: 22px; color: #a8d8ff; }
.page-hero p { margin: 0 0 10px; color: #7a8fb0; font-size: 13px; }
.hero-actions { display: flex; gap: 12px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; margin-bottom: 18px; }
.kpi-card { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 4px; }
.kpi-card span { font-size: 11px; color: #7a8fb0; }
.kpi-card strong { font-size: 18px; color: #5eead4; }
.panel { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.panel h2 { margin: 0 0 12px; font-size: 15px; color: #a8d8ff; }
.math-model { background: rgba(7,17,31,0.8); border: 1px solid rgba(120,200,255,0.1); border-radius: 8px; padding: 14px; color: #b8d4f0; font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; line-height: 1.7; white-space: pre-wrap; margin: 0; }
.mm-chart { height: 320px; width: 100%; }
</style>
