<template>
  <div class="case-page">
    <header class="page-hero">
      <h1>🚚 智能调度（鲜度 VRPTW）</h1>
      <p>OR-Tools 精确求解 · 48h 时间窗硬约束 · 鲜度衰减 · 求解动画</p>
      <div class="hero-actions">
        <el-radio-group v-model="solver" size="small" @change="load">
          <el-radio-button value="greedy">greedy</el-radio-button>
          <el-radio-button value="ortools">OR-Tools VRPTW</el-radio-button>
          <el-radio-button value="pso">粒子群 PSO</el-radio-button>
        </el-radio-group>
        <el-radio-group v-model="routeProvider" size="small" @change="load">
          <el-radio-button value="amap">高德真实路线</el-radio-button>
          <el-radio-button value="none">估算回放</el-radio-button>
        </el-radio-group>
        <el-button size="small" :loading="loading" @click="load">刷新</el-button>
        <el-button size="small" type="primary" @click="playAnim" :disabled="!canPlayReplay">▶ 播放求解动画</el-button>
        <el-button size="small" type="success" :loading="compareLoading" @click="compareAll">📊 对比所有算法</el-button>
      </div>
    </header>
    <div class="kpi-grid">
      <div class="kpi-card"><span>求解器</span><strong>{{ result?.solver_family || '-' }}</strong></div>
      <div class="kpi-card"><span>已分配</span><strong>{{ result?.summary?.assigned_orders || 0 }}</strong></div>
      <div class="kpi-card"><span>未分配</span><strong>{{ result?.summary?.unassigned_orders || 0 }}</strong></div>
      <div class="kpi-card"><span>时间窗</span><strong>{{ result?.summary?.time_window_hours || 0 }}h</strong></div>
      <div class="kpi-card"><span>均鲜度</span><strong>{{ result?.summary?.avg_freshness_score || 0 }}</strong></div>
      <div class="kpi-card"><span>容量违规</span><strong>{{ result?.constraint_validation?.capacity_violations || 0 }}</strong></div>
      <div class="kpi-card"><span>路径真实度</span><strong>{{ result?.authenticity_level || '-' }}</strong></div>
      <div class="kpi-card wide"><span>路径来源</span><strong>{{ result?.path_source || '-' }}</strong></div>
    </div>
    <section class="panel">
      <div class="panel-title">
        <h2>🎬 高德 JS API 求解回放</h2>
        <small>路网/卫星/交通图层 · 车辆移动轨迹 · 鲜度衰减同步曲线</small>
      </div>
      <el-alert
        v-if="animationNotice"
        class="animation-notice"
        type="warning"
        :closable="false"
        show-icon
        :title="animationNotice"
      />
      <DispatchReplayMap ref="replayRef" :result="result" :network="network" />
    </section>
    <section v-if="compareData.length" class="panel">
      <div class="panel-title"><h2>📊 三算法求解对比（归一化%）</h2><small>成本/距离/鲜度/分配数</small></div>
      <div ref="compareRef" class="dispatch-anim"></div>
      <el-table :data="compareData" height="180" style="margin-top:12px">
        <el-table-column prop="solver" label="算法" min-width="160" />
        <el-table-column prop="cost" label="总成本(元)" width="120" />
        <el-table-column prop="distance" label="总距离(km)" width="120" />
        <el-table-column prop="freshness" label="均鲜度" width="90" />
        <el-table-column prop="assigned" label="已分配" width="80" />
        <el-table-column prop="unassigned" label="未分配" width="80" />
        <el-table-column prop="time" label="耗时(s)" width="90" />
      </el-table>
    </section>
    <section class="panel">
      <div class="panel-title">
        <h2>📐 多目标 VRPTW 数学模型</h2>
        <small>{{ mathModel?.model_stage || 'explainable model contract' }}</small>
      </div>
      <div ref="mathRef" class="math-model-katex"></div>
      <div v-if="mathModel?.model_id" class="model-contract-grid">
        <div class="model-score-card">
          <span>综合目标值</span>
          <strong>{{ activeObjectiveScore }}</strong>
          <small>
            {{ mathModel.score_direction === 'lower_is_better' ? '越低越优' : '越高越优' }}
            <em v-if="scoreDeltaText"> · {{ scoreDeltaText }}</em>
          </small>
        </div>
        <div class="model-score-card">
          <span>服务水平</span>
          <strong>{{ percent(mathModel.current_solution?.service_level) }}</strong>
          <small>{{ mathModel.current_solution?.assigned_orders || 0 }} / {{ mathModel.current_solution?.candidate_orders || 0 }} 单</small>
        </div>
        <div class="model-score-card">
          <span>碳排估算</span>
          <strong>{{ mathModel.current_solution?.carbon_kg || 0 }}</strong>
          <small>kgCO2e · 确定性估算</small>
        </div>
        <div class="model-score-card">
          <span>硬约束</span>
          <strong>{{ mathModel.current_solution?.hard_constraint_ok ? 'OK' : 'CHECK' }}</strong>
          <small>{{ mathModel.solver_family }} / {{ mathModel.execution_mode }}</small>
        </div>
      </div>
      <div v-if="mathModel?.model_id" class="weight-lab">
        <div class="weight-lab-copy">
          <div class="panel-title compact">
            <h2>🎚️ 权重实验台</h2>
            <small>成本 / 鲜度 / 时效 / 碳排可现场调权，先即时重评分，再按需请求 solver 重算。</small>
          </div>
          <div class="weight-controls">
            <div v-for="control in weightControls" :key="control.key" class="weight-control">
              <div class="weight-control-head">
                <span>{{ control.label }}</span>
                <strong>{{ Math.round(weightDraft[control.key] || 0) }}%</strong>
              </div>
              <el-slider v-model="weightDraft[control.key]" :min="0" :max="100" :step="1" />
              <small>{{ control.description }}</small>
            </div>
          </div>
          <div class="weight-actions">
            <el-tag :type="Math.abs(weightTotal - 100) <= 1 ? 'success' : 'warning'" size="small">合计 {{ Math.round(weightTotal) }}%，系统自动归一化</el-tag>
            <el-button size="small" @click="resetWeights">恢复默认</el-button>
            <el-button size="small" type="primary" :loading="loading" @click="applyWeightsRecompute">按权重重算路线</el-button>
            <el-button size="small" type="success" :loading="compareLoading" @click="compareAll">生成候选方案对比</el-button>
          </div>
          <el-alert
            class="weight-truth"
            type="info"
            :closable="false"
            show-icon
            :title="mathModel.weight_sensitivity?.truth_note || '权重即时反馈是 scorecard 重评分；路线变化以重新求解后的 plans 为准。'"
          />
        </div>
        <div class="weight-rank-panel">
          <div class="rank-header">
            <span>当前权重推荐</span>
            <strong>{{ recommendedCandidate?.solver || '-' }}</strong>
          </div>
          <div ref="weightParetoRef" class="weight-pareto-chart"></div>
          <div class="rank-list">
            <div v-for="(row, index) in weightedRanking.slice(0, 4)" :key="row.solver" class="rank-row" :class="{ best: index === 0 }">
              <span>{{ index + 1 }}. {{ row.solver }}</span>
              <strong>{{ formatScore(row.live_score) }}</strong>
              <small>成本 {{ formatPct(row.objectives.transport_cost) }} · 鲜度风险 {{ formatPct(row.objectives.freshness_risk) }} · 碳 {{ formatPct(row.objectives.carbon) }}</small>
            </div>
          </div>
        </div>
      </div>
      <div v-if="previewObjectiveTerms.length" class="model-objectives">
        <div v-for="term in previewObjectiveTerms" :key="term.key" class="objective-term">
          <div class="term-head">
            <span>{{ term.label }}</span>
            <strong>{{ formatScore(term.contribution) }}</strong>
          </div>
          <div class="term-bar"><i :style="{ width: Math.round(term.normalized_value * 100) + '%' }"></i></div>
          <small>权重 {{ formatPct(term.weight) }} · 原值 {{ term.raw_value }} {{ term.unit }}</small>
        </div>
      </div>
      <div v-if="constraintBlocks.length" class="constraint-grid">
        <div v-for="block in constraintBlocks" :key="block.id" class="constraint-card" :class="block.status">
          <div class="constraint-head">
            <strong>{{ block.name }}</strong>
            <span>{{ block.hard ? '硬约束' : '软目标' }}</span>
          </div>
          <code>{{ block.display || block.latex }}</code>
          <small>{{ block.explanation }}</small>
        </div>
      </div>
      <ol v-if="mathModel?.algorithm_pseudocode?.length" class="algorithm-steps">
        <li v-for="step in mathModel.algorithm_pseudocode" :key="step">{{ step }}</li>
      </ol>
      <details class="model-details"><summary>📝 文字说明</summary><pre class="model-explain">{{ model }}</pre></details>
    </section>
    <section class="panel">
      <h2>调度方案明细</h2>
      <el-table :data="result?.plans || []" height="280">
        <el-table-column prop="route_id" label="路线" min-width="170" />
        <el-table-column prop="customer" label="门店" min-width="120" />
        <el-table-column prop="vehicle_type" label="车型" width="90" />
        <el-table-column prop="distance_km" label="距离(km)" width="90" />
        <el-table-column prop="duration_hours" label="时长(h)" width="90" />
        <el-table-column prop="freshness_score" label="鲜度" width="80" />
        <el-table-column prop="cost" label="成本" width="80" />
        <el-table-column prop="authenticity_level" label="真实度" width="80" />
        <el-table-column prop="distance_source" label="距离来源" min-width="150" />
        <el-table-column prop="path_source" label="路径来源" min-width="170" />
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { optimizeFoodSupplyDispatchFresh, getFoodSupplyNetwork } from '@/api/foodSupplyCase'
import DispatchReplayMap from '@/components/case/DispatchReplayMap.vue'

const OBJECTIVE_KEYS = ['transport_cost', 'freshness_risk', 'sla_penalty', 'carbon', 'load_balance']
const DEFAULT_WEIGHT_DRAFT = {
  transport_cost: 32,
  freshness_risk: 26,
  sla_penalty: 18,
  carbon: 14,
  load_balance: 10,
}
const fallbackWeightControls = [
  { key: 'transport_cost', label: '成本', description: '低运输成本、少车辆里程。' },
  { key: 'freshness_risk', label: '鲜度', description: '鲜度风险越低越好。' },
  { key: 'sla_penalty', label: '时效', description: '准时履约和未分配惩罚。' },
  { key: 'carbon', label: '碳排', description: '低碳排、低能源消耗。' },
  { key: 'load_balance', label: '均衡', description: '车辆工作量均衡。' },
]

const result = ref(null)
const network = ref(null)
const loading = ref(false)
const solver = ref('ortools')
const routeProvider = ref('amap')
const mathRef = ref(null)
const weightParetoRef = ref(null)
const replayRef = ref(null)
const weightDraft = ref({ ...DEFAULT_WEIGHT_DRAFT })
const canPlayReplay = computed(() => Number(result.value?.animation?.frame_count || 0) > 1)
const mathModel = computed(() => result.value?.mathematical_model || null)
const objectiveTerms = computed(() => mathModel.value?.objective_terms || [])
const weightControls = computed(() => {
  const controls = mathModel.value?.weight_controls
  return Array.isArray(controls) && controls.length ? controls : fallbackWeightControls
})
const weightTotal = computed(() => OBJECTIVE_KEYS.reduce((sum, key) => sum + Number(weightDraft.value[key] || 0), 0))
const normalizedWeights = computed(() => normalizeWeights(weightDraft.value))
const previewObjectiveTerms = computed(() => {
  return objectiveTerms.value.map((term) => {
    const weight = normalizedWeights.value[term.key] ?? Number(term.weight || 0)
    const normalizedValue = Number(term.normalized_value || 0)
    return {
      ...term,
      weight,
      contribution: round4(weight * normalizedValue),
    }
  })
})
const previewObjectiveScore = computed(() => round4(previewObjectiveTerms.value.reduce((sum, term) => sum + Number(term.contribution || 0), 0)))
const activeObjectiveScore = computed(() => mathModel.value ? formatScore(previewObjectiveScore.value) : '-')
const scoreDeltaText = computed(() => {
  if (!mathModel.value) return ''
  const delta = round4(previewObjectiveScore.value - Number(mathModel.value.objective_score || 0))
  if (Math.abs(delta) < 0.0001) return ''
  return `${delta > 0 ? '+' : ''}${formatScore(delta)} 即时预览`
})
const constraintBlocks = computed(() => mathModel.value?.constraint_blocks || [])
const animationNotice = computed(() => {
  if (loading.value || !result.value) return ''
  const assigned = Number(result.value?.summary?.assigned_orders || 0)
  const frames = Number(result.value?.animation?.frame_count || 0)
  if (assigned > 0 && frames <= 1) {
    return '当前调度已生成方案，但未收到动画帧。请刷新页面或重启后端，确认 dispatch-fresh 已加载最新动画契约。'
  }
  if (assigned <= 0) return '当前波次没有可回放路线，请调整日期、门店数量或车辆约束后重新求解。'
  return ''
})

const fallbackFormula = "\\begin{aligned} \\min \\quad & w_1 \\sum_{k}\\sum_{i,j} c_{ij} x_{ijk} + w_2 \\sum_{i,j} d_{ij} q_i \\cdot e_{\\text{carbon}} - w_3 \\bar{F} + w_4 \\text{SLA} \\\\ \\text{s.t.} \\quad & \\sum_k \\sum_j x_{ijk} = 1, \\quad \\forall i \\in C \\quad (\\text{每顾客一访}) \\\\ & \\sum_i q_i y_{ik} \\le Q_k, \\quad \\forall k \\quad (\\text{容量}) \\\\ & s_i + \\tau_i + t_{ij} \\le s_j, \\quad \\forall (i,j) \\quad (\\text{时间窗}) \\\\ & 0 \\le s_i \\le 2880\\,\\text{min}, \\quad \\forall i \\quad (\\text{48h 硬约束}) \\\\ & F(s_i,T,n) = 1 - \\tfrac{s_i}{L(T)} - 0.05n \\ge F_{\\min} \\quad (\\text{鲜度}) \\end{aligned}"
const formula = computed(() => mathModel.value?.objective_latex || fallbackFormula)

async function renderMath() {
  if (!mathRef.value) return
  try {
    if (!window.katex) {
      await new Promise((resolve, reject) => {
        const link = document.createElement('link'); link.rel = 'stylesheet'
        link.href = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css'
        document.head.appendChild(link)
        const s = document.createElement('script')
        s.src = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js'
        s.onload = resolve; s.onerror = reject
        document.head.appendChild(s)
      })
    }
    window.katex.render(formula.value, mathRef.value, { displayMode: true, throwOnError: false })
  } catch (e) {
    if (mathRef.value) mathRef.value.textContent = formula.value
  }
}

function percent(value) {
  const n = Number(value || 0)
  return `${Math.round(n * 100)}%`
}

function round4(value) {
  return Math.round(Number(value || 0) * 10000) / 10000
}

function formatScore(value) {
  if (value == null || Number.isNaN(Number(value))) return '-'
  return String(Math.round(Number(value) * 10000) / 10000)
}

function formatPct(value) {
  if (value == null || Number.isNaN(Number(value))) return '-'
  return `${Math.round(Number(value) * 100)}%`
}

function normalizeWeights(raw) {
  const values = {}
  OBJECTIVE_KEYS.forEach((key) => {
    values[key] = Math.max(0, Number(raw?.[key] || 0))
  })
  const total = OBJECTIVE_KEYS.reduce((sum, key) => sum + values[key], 0)
  if (total <= 0) return normalizeWeights(DEFAULT_WEIGHT_DRAFT)
  return OBJECTIVE_KEYS.reduce((acc, key) => {
    acc[key] = round4(values[key] / total)
    return acc
  }, {})
}

function resetWeights() {
  weightDraft.value = { ...DEFAULT_WEIGHT_DRAFT }
  nextTick(renderWeightPareto)
}

function objectiveMapFromModel(model) {
  const objectives = {}
  ;(model?.objective_terms || []).forEach((term) => {
    objectives[term.key] = Number(term.normalized_value || 0)
  })
  OBJECTIVE_KEYS.forEach((key) => {
    if (objectives[key] == null) objectives[key] = 0
  })
  return objectives
}

function weightedScore(objectives, weights = normalizedWeights.value) {
  return round4(OBJECTIVE_KEYS.reduce((sum, key) => sum + Number(objectives?.[key] || 0) * Number(weights[key] || 0), 0))
}

function buildCompareRow(response, fallbackSolver, elapsed = 0) {
  const plans = response?.plans || []
  const model = response?.mathematical_model || {}
  const objectives = objectiveMapFromModel(model)
  return {
    solver: response?.solver_family || fallbackSolver,
    cost: Math.round(plans.reduce((s, x) => s + Number(x.cost || 0), 0)),
    distance: Math.round(plans.reduce((s, x) => s + Number(x.distance_km || 0), 0)),
    freshness: Number(response?.summary?.avg_freshness_score || 0),
    assigned: Number(response?.summary?.assigned_orders || 0),
    unassigned: Number(response?.summary?.unassigned_orders || 0),
    time: Math.round(Number(elapsed || 0) * 100) / 100,
    objective_score: Number(model?.objective_score ?? weightedScore(objectives)),
    objectives,
    weights: model?.weights || normalizedWeights.value,
    model_stage: model?.model_stage,
    authenticity_level: response?.authenticity_level || '-',
  }
}

const solutionCandidates = computed(() => {
  const rows = compareData.value.length
    ? compareData.value
    : (result.value ? [buildCompareRow(result.value, result.value?.solver_family || solver.value)] : [])
  return rows.map((row) => ({
    ...row,
    live_score: weightedScore(row.objectives),
  }))
})

const weightedRanking = computed(() => {
  return [...solutionCandidates.value].sort((a, b) => a.live_score - b.live_score)
})
const recommendedCandidate = computed(() => weightedRanking.value[0] || null)

const model = computed(() => {
  if (!mathModel.value) {
    return `鲜度感知 VRPTW 数学模型（Freshness-Aware Vehicle Routing with Time Windows）

目标 Objective:
  min  Σ_k Σ_(i,j) c_ij · x_ijk                       // 最小总运输成本

约束 Constraints:
  (1) Σ_k Σ_j x_ijk = 1            ∀ i ∈ Customers     // 每个顾客恰被一辆车访问一次
  (2) Σ_j x_pjk = Σ_j x_jpk        ∀ k                 // depot 流量守恒（进出相等）
  (3) Σ_i q_i · y_ik ≤ Q_k         ∀ k                 // 容量约束（载重不超）
  (4) s_i + service_i + tt_ij ≤ s_j  ∀ (i,j) ∈ A        // 时间连续 + 时间窗（48h 硬约束）
  (5) 0 ≤ s_i ≤ 2880 (min)          ∀ i                 // 48h = 2880min 服务时间窗
  (6) freshness(s_i, T, n) ≥ F_min  ∀ i                 // 鲜度衰减下限
  (7) x_ijk ∈ {0,1}                                     // 0-1 决策变量

鲜度衰减模型 Freshness Decay:
  freshness = 1 - (s_i / shelf_life(T)) - 0.05 · n_transfers
  T = 4℃  : shelf_life = 240h（冷链）
  T = 25℃ : shelf_life = 120h
  T = 30℃ : shelf_life = 96h （案例基准：8 成熟 30℃ 保存 3-5 天）
  T = 35℃ : shelf_life = 72h

求解器 Solver:
  • greedy baseline（贪心：最近邻 + 容量安全）
  • OR-Tools VRPTW（PATH_CHEAPEST_ARC + Time dimension + Capacity dimension，3s 时限）`
  }
  const m = mathModel.value
  const terms = (m.objective_terms || []).map((t) => `  • ${t.label}: weight=${t.weight}, normalized=${t.normalized_value}, contribution=${t.contribution}, raw=${t.raw_value} ${t.unit}`).join('\n')
  const constraints = (m.constraint_blocks || []).map((c) => `  • ${c.name} [${c.hard ? 'hard' : 'soft'} / ${c.status}]: ${c.explanation}`).join('\n')
  const steps = (m.algorithm_pseudocode || []).map((s, i) => `  ${i + 1}. ${s}`).join('\n')
  return `${m.model_name} (${m.model_id})

模型定位:
  ${m.model_stage}
  当前 solver=${m.solver_family}, execution=${m.execution_mode}

目标项分解:
${terms}

约束:
${constraints}

求解流程:
${steps}

复杂度说明:
  ${m.complexity_note}

真实性边界:
  ${(m.truth_notes || []).join('\n  ')}`
})

async function load() {
  loading.value = true
  try {
    if (!network.value) network.value = await getFoodSupplyNetwork()
    result.value = await optimizeFoodSupplyDispatchFresh({
      wave_date: '06-01', store_limit: 8, solver_mode: solver.value,
      route_provider: routeProvider.value,
      time_window_hours: 48, freshness_window_days: 4, persist: false,
      objective_weights: normalizedWeights.value,
    })
    await nextTick()
    await renderMath()
    renderWeightPareto()
    return true
  } catch (e) { ElMessage.error('调度加载失败：' + (e.message || '后端未启动')) }
  finally { loading.value = false }
  return false
}

async function applyWeightsRecompute() {
  const ok = await load()
  if (ok) ElMessage.success('已按当前权重刷新调度评分；路线变化以新 plans 为准')
}

function playAnim() { replayRef.value?.playFromStart?.() || replayRef.value?.play?.() }

const compareData = ref([])
const compareLoading = ref(false)
const compareRef = ref(null)
let compareChart = null
let weightParetoChart = null

async function compareAll() {
  compareLoading.value = true
  try {
    const base = {
      wave_date: '06-01',
      store_limit: 8,
      route_provider: routeProvider.value,
      time_window_hours: 48,
      freshness_window_days: 4,
      persist: false,
      objective_weights: normalizedWeights.value,
    }
    const t0 = Date.now()
    const [g, o, p] = await Promise.all([
      optimizeFoodSupplyDispatchFresh({ ...base, solver_mode: 'greedy' }),
      optimizeFoodSupplyDispatchFresh({ ...base, solver_mode: 'ortools' }),
      optimizeFoodSupplyDispatchFresh({ ...base, solver_mode: 'pso' }),
    ])
    const elapsed = (Date.now() - t0) / 1000 / 3
    compareData.value = [g, o, p].map((r, i) => buildCompareRow(r, ['greedy', 'ortools', 'pso'][i], elapsed))
    await nextTick()
    renderCompare()
    renderWeightPareto()
    ElMessage.success('三算法候选方案对比完成')
  } catch (e) { ElMessage.error('对比失败：' + (e.message || '后端未启动')) }
  finally { compareLoading.value = false }
}

function renderCompare() {
  if (!compareRef.value || !compareData.value.length) return
  if (!compareChart) compareChart = echarts.init(compareRef.value)
  const d = compareData.value
  const maxCost = Math.max(...d.map(x => x.cost)) || 1
  const maxDist = Math.max(...d.map(x => x.distance)) || 1
  const maxAssigned = Math.max(...d.map(x => x.assigned)) || 1
  compareChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { textStyle: { color: '#aac', fontSize: 11 }, top: 0 },
    grid: { left: 50, right: 30, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: d.map(x => x.solver), axisLabel: { color: '#9bb3d4', fontSize: 11 } },
    yAxis: { type: 'value', max: 100, axisLabel: { color: '#7a8fb0', formatter: '{value}%' } },
    series: [
      { name: '成本(归一)', type: 'bar', data: d.map(x => Math.round(x.cost / maxCost * 100)), itemStyle: { color: '#1890ff', borderRadius: [4, 4, 0, 0] } },
      { name: '距离(归一)', type: 'bar', data: d.map(x => Math.round(x.distance / maxDist * 100)), itemStyle: { color: '#5eead4', borderRadius: [4, 4, 0, 0] } },
      { name: '鲜度%', type: 'bar', data: d.map(x => Math.round(x.freshness * 100)), itemStyle: { color: '#52c41a', borderRadius: [4, 4, 0, 0] } },
      { name: '分配数(归一)', type: 'bar', data: d.map(x => Math.round(x.assigned / maxAssigned * 100)), itemStyle: { color: '#faad14', borderRadius: [4, 4, 0, 0] } },
    ],
  })
}

function renderWeightPareto() {
  if (!weightParetoRef.value) return
  if (!weightParetoChart) weightParetoChart = echarts.init(weightParetoRef.value)
  const rows = solutionCandidates.value
  if (!rows.length) {
    weightParetoChart.setOption({
      title: {
        text: '等待候选方案',
        subtext: '先刷新调度或生成候选方案对比。',
        left: 'center',
        top: 'center',
        textStyle: { color: '#cfe5ff', fontSize: 14 },
        subtextStyle: { color: '#7a8fb0', fontSize: 11 },
      },
    }, true)
    return
  }
  const best = recommendedCandidate.value
  const toPoint = (row) => ({
    name: row.solver,
    value: [
      Math.round(Number(row.objectives.transport_cost || 0) * 1000) / 10,
      Math.round(Number(row.objectives.freshness_risk || 0) * 1000) / 10,
      row.live_score,
    ],
    row,
  })
  weightParetoChart.setOption({
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(6,14,28,.96)',
      borderColor: 'rgba(94,234,212,.22)',
      textStyle: { color: '#e6f0ff', fontSize: 12 },
      formatter: (params) => {
        const row = params.data?.row || {}
        const obj = row.objectives || {}
        return [
          `<strong>${row.solver || '-'}</strong>`,
          `综合目标值: ${formatScore(row.live_score)}`,
          `成本风险: ${formatPct(obj.transport_cost)}`,
          `鲜度风险: ${formatPct(obj.freshness_risk)}`,
          `时效惩罚: ${formatPct(obj.sla_penalty)}`,
          `碳排压力: ${formatPct(obj.carbon)}`,
          `真实度: ${row.authenticity_level || '-'}`,
        ].join('<br/>')
      },
    },
    legend: { top: 0, textStyle: { color: '#9bb3d4', fontSize: 11 } },
    grid: { left: 52, right: 24, top: 42, bottom: 42 },
    xAxis: {
      name: '成本压力%',
      type: 'value',
      axisLabel: { color: '#9bb3d4', fontSize: 11 },
      nameTextStyle: { color: '#7a8fb0' },
      splitLine: { lineStyle: { color: 'rgba(120,200,255,.08)', type: 'dashed' } },
    },
    yAxis: {
      name: '鲜度风险%',
      type: 'value',
      axisLabel: { color: '#9bb3d4', fontSize: 11 },
      nameTextStyle: { color: '#7a8fb0' },
      splitLine: { lineStyle: { color: 'rgba(120,200,255,.08)', type: 'dashed' } },
    },
    series: [
      {
        name: '候选方案',
        type: 'scatter',
        symbolSize: (value, params) => 18 + Math.max(0, 18 * (1 - Number(params.data?.row?.objectives?.carbon || 0))),
        data: rows.map(toPoint),
        itemStyle: { color: '#60a5fa', opacity: 0.82 },
      },
      {
        name: '当前权重最优',
        type: 'scatter',
        symbol: 'diamond',
        symbolSize: 28,
        data: best ? [toPoint(best)] : [],
        itemStyle: { color: '#5eead4', shadowBlur: 18, shadowColor: 'rgba(94,234,212,.55)' },
      },
    ],
  }, true)
}

function resizeCharts() {
  compareChart?.resize()
  weightParetoChart?.resize()
}

watch([solutionCandidates, normalizedWeights], async () => {
  await nextTick()
  renderWeightPareto()
}, { deep: true })

onMounted(load)
onMounted(() => {
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  compareChart?.dispose()
  compareChart = null
  weightParetoChart?.dispose()
  weightParetoChart = null
})
</script>

<style scoped>
.case-page { color: #e6f0ff; }
.page-hero { margin-bottom: 18px; }
.page-hero h1 { margin: 0 0 4px; font-size: 22px; color: #a8d8ff; }
.page-hero p { margin: 0 0 10px; color: #7a8fb0; font-size: 13px; }
.hero-actions { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; margin-bottom: 18px; }
.kpi-card { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 12px; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.kpi-card.wide { grid-column: span 2; }
.kpi-card span { font-size: 11px; color: #7a8fb0; }
.kpi-card strong { font-size: 18px; color: #5eead4; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.panel { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.panel-title { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.panel-title.compact { margin-bottom: 10px; align-items: flex-start; gap: 12px; }
.panel-title.compact small { color: #7a8fb0; line-height: 1.5; text-align: right; max-width: 520px; }
.animation-notice { margin-bottom: 12px; }
.panel h2 { margin: 0 0 12px; font-size: 15px; color: #a8d8ff; }
.dispatch-anim { height: 380px; width: 100%; }
.math-model { background: rgba(7,17,31,0.8); border: 1px solid rgba(120,200,255,0.1); border-radius: 8px; padding: 14px; color: #b8d4f0; font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; line-height: 1.7; white-space: pre-wrap; margin: 0; }
.math-model-katex { overflow-x: auto; padding: 12px; border-radius: 10px; border: 1px solid rgba(120,200,255,.12); background: rgba(7,17,31,.56); }
.model-contract-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 12px; }
.model-score-card { border: 1px solid rgba(120,200,255,.14); border-radius: 10px; background: rgba(7,17,31,.66); padding: 12px; display: flex; flex-direction: column; gap: 4px; }
.model-score-card span,
.model-score-card small { color: #7a8fb0; font-size: 11px; }
.model-score-card small em { color: #fbbf24; font-style: normal; }
.model-score-card strong { color: #5eead4; font-size: 20px; }
.weight-lab { display: grid; grid-template-columns: minmax(300px, 1fr) minmax(330px, .9fr); gap: 14px; margin-top: 12px; border: 1px solid rgba(94,234,212,.18); border-radius: 12px; padding: 12px; background: linear-gradient(135deg, rgba(7,17,31,.78), rgba(12,31,44,.62)); }
.weight-lab-copy,
.weight-rank-panel { min-width: 0; }
.weight-controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
.weight-control { border: 1px solid rgba(120,200,255,.12); border-radius: 10px; padding: 10px 10px 4px; background: rgba(8,20,35,.72); }
.weight-control-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; color: #cfe5ff; font-size: 12px; }
.weight-control-head strong { color: #5eead4; font-size: 14px; }
.weight-control small { display: block; min-height: 32px; color: #7a8fb0; font-size: 11px; line-height: 1.45; }
.weight-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.weight-truth { margin-top: 10px; }
.rank-header { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 8px; }
.rank-header span { color: #7a8fb0; font-size: 12px; }
.rank-header strong { color: #5eead4; font-size: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.weight-pareto-chart { height: 260px; width: 100%; border: 1px solid rgba(120,200,255,.1); border-radius: 10px; background: rgba(7,17,31,.54); }
.rank-list { display: grid; gap: 8px; margin-top: 10px; }
.rank-row { border: 1px solid rgba(120,200,255,.1); border-radius: 10px; padding: 8px 10px; background: rgba(8,20,35,.7); display: grid; grid-template-columns: 1fr auto; gap: 4px 10px; align-items: center; }
.rank-row.best { border-color: rgba(94,234,212,.42); background: rgba(20,83,68,.26); }
.rank-row span { color: #cfe5ff; font-size: 12px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-row strong { color: #fbbf24; font-size: 13px; }
.rank-row small { grid-column: 1 / -1; color: #7a8fb0; font-size: 11px; line-height: 1.45; }
.model-objectives { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin-top: 12px; }
.objective-term { border: 1px solid rgba(120,200,255,.12); border-radius: 10px; padding: 10px; background: rgba(10,22,38,.7); }
.term-head { display: flex; justify-content: space-between; gap: 8px; color: #cfe5ff; font-size: 12px; }
.term-head strong { color: #fbbf24; }
.term-bar { height: 7px; border-radius: 999px; background: rgba(120,200,255,.1); overflow: hidden; margin: 8px 0; }
.term-bar i { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #5eead4, #60a5fa); }
.objective-term small { color: #7a8fb0; font-size: 11px; }
.constraint-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 10px; margin-top: 12px; }
.constraint-card { border: 1px solid rgba(120,200,255,.12); border-radius: 10px; padding: 10px; background: rgba(7,17,31,.66); display: flex; flex-direction: column; gap: 8px; }
.constraint-card.violated { border-color: rgba(248,113,113,.45); }
.constraint-card.partially_assigned { border-color: rgba(251,191,36,.38); }
.constraint-head { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.constraint-head strong { color: #cfe5ff; font-size: 12px; }
.constraint-head span { color: #5eead4; font-size: 11px; }
.constraint-card code { color: #a8d8ff; white-space: normal; word-break: break-word; font-size: 11px; }
.constraint-card small { color: #7a8fb0; line-height: 1.5; }
.algorithm-steps { margin: 12px 0 0; padding-left: 18px; color: #b8d4f0; font-size: 12px; line-height: 1.7; }
.model-details { margin-top: 12px; }
.model-explain { white-space: pre-wrap; overflow-x: auto; color: #b8d4f0; font-size: 12px; line-height: 1.65; }

@media (max-width: 980px) {
  .weight-lab { grid-template-columns: 1fr; }
  .panel-title.compact { flex-direction: column; }
  .panel-title.compact small { text-align: left; max-width: none; }
  .kpi-card.wide { grid-column: span 1; }
}
</style>
