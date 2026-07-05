<template>
  <div class="dispatch-console">
    <section class="health-band">
      <div class="health-copy">
        <span class="section-kicker">COMMAND LAYER</span>
        <h2>智能调度控制台</h2>
        <p>{{ healthMessage }}</p>
      </div>
      <div class="health-metrics">
        <div class="metric">
          <span>订单源</span>
          <strong>{{ sourceLabel(dispatchHealth?.data_source) }}</strong>
        </div>
        <div class="metric">
          <span>可调度订单</span>
          <strong>{{ dispatchHealth?.dispatchable_orders || 0 }}</strong>
        </div>
        <div class="metric">
          <span>可用车辆</span>
          <strong>{{ dispatchHealth?.vehicle_source?.available_vehicles || 0 }}</strong>
        </div>
        <div class="metric">
          <span>运力吨位</span>
          <strong>{{ formatNumber(dispatchHealth?.vehicle_source?.total_capacity_weight_tons) }}t</strong>
        </div>
      </div>
    </section>

    <el-alert
      v-if="diagnosticRecommendations.length"
      class="truth-alert"
      type="info"
      :closable="false"
      show-icon
    >
      <template #title>{{ diagnosticRecommendations.join('；') }}</template>
    </el-alert>

    <el-row :gutter="18" class="main-grid">
      <el-col :xs="24" :lg="7">
        <el-card class="panel-card">
          <template #header>
            <div class="card-header">
              <span>调度波次</span>
              <el-tag type="success">{{ pendingOrders.length }} 单</el-tag>
            </div>
          </template>

          <div class="filter-grid">
            <el-input v-model="waveFilters.search" placeholder="订单/客户" clearable size="small" />
            <el-input v-model="waveFilters.city" placeholder="城市" clearable size="small" />
            <el-select v-model="waveFilters.data_source" size="small" class="source-select">
              <el-option label="自动优先真实明细" value="auto" />
              <el-option label="真实明细" value="shipment_fact" />
              <el-option label="旧订单表" value="orders" />
            </el-select>
            <el-input-number
              v-model="waveFilters.limit"
              :min="1"
              :max="500"
              size="small"
              controls-position="right"
              class="limit-input"
            />
          </div>

          <div class="toolbar-row">
            <el-button size="small" @click="loadDispatchWave" :loading="waveLoading">生成波次</el-button>
            <el-button size="small" @click="selectAllOrders">全选</el-button>
            <el-button size="small" @click="selectedOrders = []">清空</el-button>
          </div>

          <el-select
            v-model="selectedOrders"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="默认使用当前波次"
            class="full-select"
          >
            <el-option
              v-for="order in filteredOrders"
              :key="order.id"
              :label="`${order.order_number} - ${order.customer_name || order.destination_name || '客户'} (${formatWeight(order)}t)`"
              :value="order.id"
            />
          </el-select>

          <div class="order-list">
            <div
              v-for="order in filteredOrders"
              :key="order.id"
              class="order-item"
              :class="{ selected: selectedOrders.includes(order.id) }"
              @click="toggleOrder(order.id)"
            >
              <el-checkbox :model-value="selectedOrders.includes(order.id)" @click.stop @change="toggleOrder(order.id)" />
              <div class="order-info">
                <div class="order-title">
                  <span>{{ order.order_number }}</span>
                  <el-tag size="small" :type="order.data_source === 'shipment_fact' ? 'success' : 'info'">
                    {{ sourceLabel(order.data_source) }}
                  </el-tag>
                </div>
                <div class="order-meta">
                  <span>{{ order.origin_name || '未知起点' }}</span>
                  <span>{{ order.destination_name || '未知终点' }}</span>
                  <span>{{ formatWeight(order) }}t</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card class="panel-card">
          <template #header>
            <div class="card-header">
              <span>调度配置</span>
              <el-tag :type="truthTagType">{{ authenticityLabel }}</el-tag>
            </div>
          </template>

          <el-form :model="dispatchConfig" label-width="112px" size="small">
            <el-form-item label="调度算法">
              <el-select v-model="dispatchConfig.algorithm" class="full-select">
                <el-option
                  v-for="algo in algorithms"
                  :key="algo.id"
                  :label="`${algo.name} - ${algo.performance || ''}`"
                  :value="algo.id"
                />
              </el-select>
              <div class="config-hint">{{ currentAlgorithm?.description }}</div>
            </el-form-item>

            <el-form-item label="AI策略层">
              <el-select v-model="dispatchConfig.policy_mode" class="full-select">
                <el-option label="Solver Only" value="solver_only" />
                <el-option label="Shadow Rerank" value="shadow_rerank" />
                <el-option label="DQN Shadow" value="dqn_shadow" />
              </el-select>
              <div class="config-hint">AI 只做候选方案评分，硬约束仍由求解器校验</div>
            </el-form-item>

            <el-form-item label="选择车辆">
              <el-select v-model="selectedVehicles" multiple placeholder="默认全部可用车辆" class="full-select">
                <el-option
                  v-for="vehicle in availableVehicles"
                  :key="vehicle.id"
                  :label="`${vehicle.plate_number} (${vehicleCapacity(vehicle)}t)`"
                  :value="vehicle.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="每车上限">
              <el-input-number v-model="dispatchConfig.max_orders_per_vehicle" :min="1" :max="50" />
            </el-form-item>

            <el-form-item label="真实距离">
              <el-switch v-model="dispatchConfig.use_precise_distance" />
              <span class="config-hint">小波次优先 provider，大波次自动降级</span>
            </el-form-item>

            <el-divider content-position="left">目标权重</el-divider>

            <el-form-item label="成本">
              <el-slider v-model="dispatchConfig.weights.cost" :min="0" :max="1" :step="0.1" show-input :show-input-controls="false" />
            </el-form-item>
            <el-form-item label="时间">
              <el-slider v-model="dispatchConfig.weights.time" :min="0" :max="1" :step="0.1" show-input :show-input-controls="false" />
            </el-form-item>
            <el-form-item label="满意度">
              <el-slider v-model="dispatchConfig.weights.satisfaction" :min="0" :max="1" :step="0.1" show-input :show-input-controls="false" />
            </el-form-item>
          </el-form>

          <div class="config-actions">
            <el-button type="primary" @click="handlePreview" :loading="previewLoading">预览调度</el-button>
            <el-button type="success" @click="handleSmartDispatch" :loading="dispatchLoading">智能调度</el-button>
            <el-button @click="handleCompareSolvers" :loading="compareLoading">求解器对比</el-button>
          </div>
        </el-card>

        <el-card class="panel-card summary-card" v-if="dispatchSummary">
          <template #header>
            <div class="card-header">
              <span>调度汇总</span>
              <el-tag>{{ activeScenarioCode || '预览' }}</el-tag>
            </div>
          </template>
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="已分配">{{ dispatchSummary.total_orders_assigned || dispatchSummary.assigned_orders }} 单</el-descriptions-item>
            <el-descriptions-item label="未分配">{{ dispatchSummary.total_orders_unassigned || dispatchSummary.unassigned_orders }} 单</el-descriptions-item>
            <el-descriptions-item label="使用车辆">{{ dispatchSummary.total_vehicles_used || dispatchSummary.vehicles_used }} 辆</el-descriptions-item>
            <el-descriptions-item label="平均载重率">{{ percent(dispatchSummary.average_load_utilization) }}</el-descriptions-item>
            <el-descriptions-item label="总里程">{{ formatNumber(dispatchSummary.total_distance_km || dispatchSummary.total_distance) }} 公里</el-descriptions-item>
            <el-descriptions-item label="总成本"><span class="cost">{{ formatNumber(dispatchSummary.total_cost) }} 元</span></el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card class="panel-card summary-card" v-if="solverPlan || constraintValidation || rlRerank">
          <template #header>
            <div class="card-header">
              <span>Solver + AI Shadow</span>
              <el-tag :type="constraintValidation?.passed ? 'success' : 'warning'">
                {{ constraintValidation?.passed ? '约束通过' : '需复核' }}
              </el-tag>
            </div>
          </template>
          <div class="policy-grid">
            <div class="policy-cell">
              <span>策略模式</span>
              <strong>{{ dispatchSummary?.policy_mode || dispatchConfig.policy_mode }}</strong>
            </div>
            <div class="policy-cell">
              <span>Solver</span>
              <strong>{{ solverPlan?.solver || '-' }}</strong>
            </div>
            <div class="policy-cell">
              <span>AI可部署</span>
              <strong>{{ rlRerank?.deployable ? '是' : '否' }}</strong>
            </div>
            <div class="policy-cell">
              <span>违规数</span>
              <strong>{{ constraintValidation?.violation_count ?? 0 }}</strong>
            </div>
          </div>
          <el-table v-if="rlCandidates.length" :data="rlCandidates" size="small" max-height="180" class="shadow-table">
            <el-table-column prop="shadow_rank" label="AI序" width="64" />
            <el-table-column prop="vehicle_id" label="车辆" width="70" />
            <el-table-column prop="order_count" label="单数" width="64" />
            <el-table-column prop="policy_score" label="策略分" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="9">
        <el-card class="panel-card result-card">
          <template #header>
            <div class="card-header">
              <span>调度结果</span>
              <el-button v-if="dispatchPlans.length" type="success" size="small" @click="handleApplyAll" :loading="applyLoading">确认执行</el-button>
            </div>
          </template>

          <div v-if="!dispatchPlans.length" class="empty-state">
            <span class="empty-icon">📋</span>
            <p>生成波次后点击预览，系统会返回可解释方案</p>
          </div>

          <el-collapse v-else v-model="activePlan" class="plan-list">
            <el-collapse-item v-for="(plan, index) in dispatchPlans" :key="plan.vehicle_id" :name="index">
              <template #title>
                <div class="plan-title">
                  <strong>{{ plan.vehicle_info?.plate_number }}</strong>
                  <el-tag size="small">{{ plan.orders?.length || 0 }} 单</el-tag>
                  <el-tag type="warning" size="small">{{ formatNumber(plan.total_cost) }} 元</el-tag>
                  <el-tag size="small" type="success">{{ percent(plan.load_utilization) }}</el-tag>
                </div>
              </template>
              <div class="plan-detail">
                <el-descriptions :column="2" size="small">
                  <el-descriptions-item label="总距离">{{ formatNumber(plan.total_distance) }} 公里</el-descriptions-item>
                  <el-descriptions-item label="预计时长">{{ formatNumber(plan.total_duration) }} 分钟</el-descriptions-item>
                  <el-descriptions-item label="载重">{{ vehicleCapacity(plan.vehicle_info) }} 吨</el-descriptions-item>
                  <el-descriptions-item label="评分">{{ formatNumber(plan.score) }}</el-descriptions-item>
                </el-descriptions>
                <div class="assigned-orders">
                  <el-tag v-for="order in plan.orders" :key="order.ref || order.id" size="small">
                    {{ order.order_number }}
                  </el-tag>
                </div>
                <el-alert v-if="plan.suggestions?.length" type="info" :closable="false" class="mini-alert">
                  <template #title>{{ plan.suggestions.join('；') }}</template>
                </el-alert>
              </div>
            </el-collapse-item>
          </el-collapse>

          <div v-if="unassignedOrders.length" class="unassigned-section">
            <el-divider />
            <h4>未分配订单</h4>
            <el-table :data="unassignedOrders" size="small" max-height="220">
              <el-table-column prop="order_number" label="订单号" width="150" />
              <el-table-column prop="reason" label="原因" />
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="18" class="bottom-grid">
      <el-col :xs="24" :lg="8">
        <el-card class="panel-card">
          <template #header>诊断解释</template>
          <div class="diagnostic-list">
            <div v-for="item in diagnosticRows" :key="item.label" class="diagnostic-row">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="8">
        <el-card class="panel-card">
          <template #header>
            <div class="card-header">
              <span>AI Shadow</span>
              <el-button size="small" @click="handlePolicyJob" :loading="policyJobLoading">后台评估</el-button>
            </div>
          </template>
          <div v-if="aiShadow || policyJobStatus" class="ai-shadow">
            <div class="shadow-score">
              <span>风险分</span>
              <strong>{{ aiShadow.risk_score ?? 0 }}</strong>
            </div>
            <el-tag v-for="model in shadowModels" :key="model" class="shadow-tag">{{ model }}</el-tag>
            <p v-if="policyJobStatus">后台任务：{{ policyJobStatus }}</p>
            <p v-for="tip in aiShadow.recommendations || []" :key="tip">{{ tip }}</p>
          </div>
          <el-empty v-else description="尚未运行调度" :image-size="70" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="8">
        <el-card class="panel-card">
          <template #header>求解器对比</template>
          <el-table v-if="solverComparison.length" :data="solverComparison" size="small" max-height="240">
            <el-table-column prop="solver" label="求解器" width="105" />
            <el-table-column prop="assigned_orders" label="分配" width="70" />
            <el-table-column prop="total_cost" label="成本" />
            <el-table-column prop="status" label="状态" />
          </el-table>
          <el-empty v-else description="点击求解器对比" :image-size="70" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getOrders } from '@/api/orders'
import { getVehicles } from '@/api/vehicles'
import {
  applyDispatch,
  compareDispatchSolvers,
  createDispatchWave,
  createDispatchPolicyJob,
  getAlgorithms,
  getDispatchHealth,
  getDispatchPolicyJob,
  previewDispatch,
  smartDispatch
} from '@/api/dispatch'

const dispatchHealth = ref(null)
const pendingOrders = ref([])
const availableVehicles = ref([])
const selectedOrders = ref([])
const selectedVehicles = ref([])
const dispatchPlans = ref([])
const unassignedOrders = ref([])
const dispatchSummary = ref(null)
const dispatchDiagnostics = ref(null)
const aiShadow = ref(null)
const solverPlan = ref(null)
const rlRerank = ref(null)
const constraintValidation = ref(null)
const solverComparison = ref([])
const activeScenarioId = ref(null)
const activeScenarioCode = ref('')
const activePlan = ref([0])
const policyJobLoading = ref(false)
const policyJob = ref(null)

const waveFilters = ref({
  search: '',
  city: '',
  data_source: 'auto',
  limit: 100
})

const dispatchConfig = ref({
  algorithm: 'balanced',
  policy_mode: 'solver_only',
  max_orders_per_vehicle: 5,
  use_precise_distance: true,
  consider_weather: true,
  consider_traffic: true,
  weights: {
    cost: 0.4,
    time: 0.3,
    satisfaction: 0.3
  }
})

const algorithms = ref([
  { id: 'balanced', name: '均衡策略', description: '综合考虑距离、容量、成本', performance: '快速' },
  { id: 'greedy', name: '贪心算法', description: '局部最优快速分配', performance: '极快' },
  { id: 'capacity_first', name: '载重优先', description: '优先提升车辆装载率', performance: '快速' }
])

const waveLoading = ref(false)
const previewLoading = ref(false)
const dispatchLoading = ref(false)
const applyLoading = ref(false)
const compareLoading = ref(false)

const currentAlgorithm = computed(() => algorithms.value.find(item => item.id === dispatchConfig.value.algorithm))
const healthMessage = computed(() => dispatchHealth.value?.message || '正在检查调度数据链路')
const effectiveDiagnostics = computed(() => dispatchDiagnostics.value || dispatchHealth.value?.diagnostics || {})
const diagnosticRecommendations = computed(() => effectiveDiagnostics.value?.recommendations || [])
const authenticityLabel = computed(() => {
  const level = lastTruth.value.authenticity_level || 'C'
  return `真实性 ${level}`
})
const truthTagType = computed(() => {
  const level = lastTruth.value.authenticity_level || 'C'
  if (level.startsWith('B')) return 'success'
  if (level === 'C') return 'warning'
  return 'info'
})
const lastTruth = ref({})

const filteredOrders = computed(() => {
  const search = waveFilters.value.search?.toLowerCase()
  if (!search) return pendingOrders.value
  return pendingOrders.value.filter(order =>
    order.order_number?.toLowerCase().includes(search) ||
    order.customer_name?.toLowerCase().includes(search) ||
    order.origin_name?.toLowerCase().includes(search) ||
    order.destination_name?.toLowerCase().includes(search)
  )
})

const diagnosticRows = computed(() => {
  const d = effectiveDiagnostics.value || {}
  const reasons = d.reason_counts || {}
  return [
    { label: '订单数量', value: d.order_count ?? 0 },
    { label: '车辆数量', value: d.vehicle_count ?? 0 },
    { label: '缺坐标订单', value: d.missing_coordinate_orders ?? 0 },
    { label: '零重量订单', value: d.zero_weight_orders ?? 0 },
    { label: '重量缺口', value: `${formatNumber(d.capacity_gap_weight_kg)} kg` },
    { label: '容量告警', value: Object.keys(reasons).length ? Object.keys(reasons).join(', ') : '无' }
  ]
})

const shadowModels = computed(() => {
  const models = aiShadow.value?.models || {}
  return Object.entries(models).map(([key, value]) => `${key}: ${value}`)
})

const rlCandidates = computed(() => (rlRerank.value?.candidates || []).slice(0, 5))
const policyJobStatus = computed(() => {
  const job = policyJob.value?.job || policyJob.value
  if (!job) return ''
  return `${job.policy_family || 'shadow'} · ${job.status || 'unknown'}`
})

onMounted(async () => {
  await Promise.all([loadHealth(), loadAlgorithms(), loadAvailableVehicles(), loadPendingOrders()])
  await loadDispatchWave()
})

async function loadHealth() {
  try {
    const res = await getDispatchHealth()
    dispatchHealth.value = res
    dispatchDiagnostics.value = res.diagnostics
    lastTruth.value = {
      authenticity_level: res.authenticity_level,
      provider_status: res.provider_status,
      data_source: res.data_source
    }
  } catch (error) {
    console.error('加载调度健康失败:', error)
  }
}

async function loadAlgorithms() {
  try {
    const res = await getAlgorithms()
    if (res.success) algorithms.value = res.algorithms || algorithms.value
  } catch (error) {
    console.error('加载算法列表失败:', error)
  }
}

async function loadPendingOrders() {
  try {
    if (waveFilters.value.data_source !== 'orders') return
    const res = await getOrders({ status: 'pending', per_page: waveFilters.value.limit })
    pendingOrders.value = res.orders || []
  } catch (error) {
    console.error('加载订单失败:', error)
  }
}

async function loadAvailableVehicles() {
  try {
    const res = await getVehicles({ status: 'available', per_page: 200 })
    availableVehicles.value = normalizeVehicles(res.vehicles || [])
  } catch (error) {
    console.error('加载车辆失败:', error)
  }
}

async function loadDispatchWave() {
  waveLoading.value = true
  try {
    const res = await createDispatchWave(buildPayload(false))
    if (res.success) {
      pendingOrders.value = res.wave?.orders || pendingOrders.value
      availableVehicles.value = normalizeVehicles(res.wave?.vehicles || availableVehicles.value)
      dispatchDiagnostics.value = res.wave?.diagnostics || dispatchDiagnostics.value
      lastTruth.value = {
        authenticity_level: res.authenticity_level,
        data_source: res.data_source
      }
      if (!selectedOrders.value.length) {
        selectedOrders.value = pendingOrders.value.slice(0, Math.min(20, pendingOrders.value.length)).map(order => order.id)
      }
    }
  } catch (error) {
    ElMessage.error('生成调度波次失败')
  } finally {
    waveLoading.value = false
  }
}

function buildPayload(includeSelection = true) {
  return {
    search: waveFilters.value.search || undefined,
    city: waveFilters.value.city || undefined,
    data_source: waveFilters.value.data_source,
    limit: waveFilters.value.limit,
    order_ids: includeSelection && selectedOrders.value.length ? selectedOrders.value : undefined,
    vehicle_ids: selectedVehicles.value.length ? selectedVehicles.value : undefined,
    ...dispatchConfig.value
  }
}

function applyResult(res) {
  dispatchPlans.value = res.plans || []
  unassignedOrders.value = res.unassigned_orders || []
  dispatchSummary.value = res.summary || null
  dispatchDiagnostics.value = res.diagnostics || null
  aiShadow.value = res.ai_shadow || null
  solverPlan.value = res.solver_plan || null
  rlRerank.value = res.rl_rerank || null
  constraintValidation.value = res.constraint_validation || null
  activeScenarioId.value = res.scenario_id || null
  activeScenarioCode.value = res.scenario_code || ''
  lastTruth.value = {
    authenticity_level: res.authenticity_level,
    provider_status: res.provider_status,
    data_source: res.data_source,
    distance_source: res.distance_source,
    fallback_reason: res.fallback_reason
  }
}

async function handlePreview() {
  previewLoading.value = true
  try {
    const res = await previewDispatch(buildPayload(true))
    if (res.success) {
      applyResult(res)
      ElMessage.success(`预览完成：${res.summary?.assigned_orders || 0} 单已分配`)
    } else {
      ElMessage.error(res.error || '预览失败')
    }
  } catch (error) {
    ElMessage.error('预览调度失败')
  } finally {
    previewLoading.value = false
  }
}

async function handleSmartDispatch() {
  dispatchLoading.value = true
  try {
    const res = await smartDispatch(buildPayload(true))
    if (res.success) {
      applyResult(res)
      ElMessage.success(`${currentAlgorithm.value?.name || '智能调度'}完成：${res.summary?.assigned_orders || 0} 单已分配`)
    } else {
      ElMessage.error(res.error || '智能调度失败')
    }
  } catch (error) {
    ElMessage.error('执行智能调度失败')
  } finally {
    dispatchLoading.value = false
  }
}

async function handleCompareSolvers() {
  compareLoading.value = true
  try {
    const res = await compareDispatchSolvers({
      ...buildPayload(true),
      solvers: ['greedy', 'balanced', 'capacity_first', 'ortools', 'alns', 'genetic']
    })
    if (res.success) {
      solverComparison.value = res.results || []
      ElMessage.success(res.best_solver ? `推荐求解器：${res.best_solver}` : '求解器对比完成')
    } else {
      ElMessage.error(res.error || '求解器对比失败')
    }
  } catch (error) {
    ElMessage.error('求解器对比失败')
  } finally {
    compareLoading.value = false
  }
}

async function handlePolicyJob() {
  policyJobLoading.value = true
  try {
    const res = await createDispatchPolicyJob({
      policy_family: dispatchConfig.value.policy_mode === 'dqn_shadow' ? 'dqn' : 'fitted_q',
      scenario_id: activeScenarioId.value || undefined,
      runtime_profile: 'full',
      scenario_limit: activeScenarioId.value ? 1 : 50,
      row_limit: activeScenarioId.value ? 50 : 200,
      top_k: 10,
      use_ml: false
    })
    if (res.success) {
      policyJob.value = res.job
      ElMessage.success('AI Shadow 后台任务已创建')
      setTimeout(() => pollPolicyJob(res.job?.job_id), 1200)
    } else {
      ElMessage.warning(res.fallback_reason || 'AI Shadow 后台任务创建失败')
    }
  } catch (error) {
    ElMessage.error('AI Shadow 后台任务创建失败')
  } finally {
    policyJobLoading.value = false
  }
}

async function pollPolicyJob(jobId) {
  if (!jobId) return
  try {
    const res = await getDispatchPolicyJob(jobId)
    if (res.success) {
      policyJob.value = res.job
      const status = res.job?.status
      if (status && !['completed', 'failed'].includes(status)) {
        setTimeout(() => pollPolicyJob(jobId), 1600)
      } else if (status === 'completed') {
        ElMessage.success('AI Shadow 后台任务完成')
      }
    }
  } catch (error) {
    console.warn('轮询 AI Shadow 任务失败:', error)
  }
}

async function handleApplyAll() {
  if (!dispatchPlans.value.length) return
  try {
    await ElMessageBox.confirm(
      '确认执行当前调度方案？系统会写入调度场景与分配记录，不会覆盖原始真实物流明细。',
      '确认执行',
      { type: 'warning' }
    )
    applyLoading.value = true
    const res = await applyDispatch({
      scenario_id: activeScenarioId.value,
      scenario_code: activeScenarioCode.value,
      plans: dispatchPlans.value,
      summary: dispatchSummary.value,
      diagnostics: dispatchDiagnostics.value,
      ai_shadow: aiShadow.value,
      ...lastTruth.value
    })
    if (res.success) {
      ElMessage.success(res.message)
      await loadHealth()
    } else {
      ElMessage.error(res.error || '执行失败')
    }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('执行调度失败')
  } finally {
    applyLoading.value = false
  }
}

function selectAllOrders() {
  selectedOrders.value = filteredOrders.value.map(order => order.id)
}

function toggleOrder(orderId) {
  if (selectedOrders.value.includes(orderId)) {
    selectedOrders.value = selectedOrders.value.filter(id => id !== orderId)
  } else {
    selectedOrders.value = [...selectedOrders.value, orderId]
  }
}

function normalizeVehicles(vehicles) {
  return vehicles.map(vehicle => ({
    ...vehicle,
    capacity_weight: vehicle.capacity_weight ?? vehicle.load_capacity ?? vehicle.capacity ?? 0,
    capacity_volume: vehicle.capacity_volume ?? vehicle.volume_capacity ?? 0
  }))
}

function sourceLabel(source) {
  const map = {
    shipment_fact: '真实明细',
    orders: '订单表',
    none: '无数据'
  }
  return map[source] || source || '未知'
}

function vehicleCapacity(vehicle = {}) {
  return formatNumber(vehicle.capacity_weight ?? vehicle.load_capacity ?? vehicle.capacity ?? 0)
}

function formatWeight(order = {}) {
  const tons = order.weight ?? ((order.weight_kg || 0) / 1000)
  return formatNumber(tons)
}

function formatNumber(value) {
  const number = Number(value || 0)
  if (Number.isNaN(number)) return '0'
  return number.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function percent(value) {
  const number = Number(value || 0)
  return `${Math.round(number * 100)}%`
}
</script>

<style scoped>
.dispatch-console {
  padding: 20px;
  color: #e5f4ff;
}

.health-band {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(420px, 1fr);
  gap: 18px;
  padding: 22px;
  margin-bottom: 16px;
  border: 1px solid rgba(0, 212, 255, 0.26);
  border-radius: 8px;
  background: rgba(8, 22, 36, 0.86);
}

.section-kicker {
  display: block;
  margin-bottom: 8px;
  color: #00d4ff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
}

.health-copy h2 {
  margin: 0 0 8px;
  font-size: 26px;
  line-height: 1.2;
}

.health-copy p {
  margin: 0;
  color: #9bb4c8;
  line-height: 1.6;
}

.health-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric {
  padding: 14px;
  border: 1px solid rgba(0, 212, 255, 0.18);
  border-radius: 8px;
  background: rgba(15, 34, 52, 0.88);
}

.metric span {
  display: block;
  color: #8ca9bd;
  font-size: 12px;
}

.metric strong {
  display: block;
  margin-top: 8px;
  color: #f4fbff;
  font-size: 20px;
  line-height: 1.1;
}

.truth-alert {
  margin-bottom: 16px;
}

.main-grid,
.bottom-grid {
  row-gap: 18px;
}

.bottom-grid {
  margin-top: 18px;
}

.panel-card {
  border-radius: 8px;
}

.card-header,
.toolbar-row,
.plan-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.filter-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(132px, 1fr) 96px;
  gap: 8px;
  margin-bottom: 10px;
}

.source-select {
  width: 100%;
}

.limit-input {
  width: 96px;
}

.toolbar-row {
  justify-content: flex-start;
  margin-bottom: 10px;
}

.full-select {
  width: 100%;
}

.order-list {
  max-height: 420px;
  overflow-y: auto;
  margin-top: 12px;
}

.order-item {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 8px;
  padding: 10px;
  margin-bottom: 8px;
  border: 1px solid rgba(64, 158, 255, 0.18);
  border-radius: 8px;
  background: #f8fbff;
  color: #263445;
  cursor: pointer;
}

.order-item.selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.order-title,
.order-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.order-title {
  justify-content: space-between;
  font-weight: 700;
  min-width: 0;
}

.order-title span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.order-meta {
  margin-top: 4px;
  color: #6b7b8d;
  font-size: 12px;
  flex-wrap: wrap;
}

.config-hint {
  margin-top: 6px;
  color: #7d8da1;
  font-size: 12px;
  line-height: 1.4;
}

.config-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.summary-card {
  margin-top: 18px;
}

.cost {
  color: #e6a23c;
  font-weight: 700;
}

.policy-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.policy-cell {
  padding: 10px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #f8fbff;
}

.policy-cell span {
  display: block;
  color: #7b8da0;
  font-size: 12px;
}

.policy-cell strong {
  display: block;
  margin-top: 4px;
  color: #263445;
}

.shadow-table {
  margin-top: 8px;
}

.result-card {
  min-height: 520px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 260px;
  color: #8a98a8;
}

.empty-icon {
  font-size: 44px;
  margin-bottom: 12px;
}

.plan-list {
  max-height: 520px;
  overflow-y: auto;
}

.plan-title {
  width: 100%;
  justify-content: flex-start;
}

.plan-detail {
  padding: 10px 0;
}

.assigned-orders {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.mini-alert {
  margin-top: 12px;
}

.unassigned-section h4 {
  margin: 0 0 12px;
  color: #f56c6c;
}

.diagnostic-list {
  display: grid;
  gap: 8px;
}

.diagnostic-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #edf0f5;
  color: #425466;
}

.ai-shadow {
  color: #425466;
}

.shadow-score {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}

.shadow-score strong {
  color: #f59e0b;
  font-size: 28px;
}

.shadow-tag {
  margin: 0 6px 6px 0;
}

.ai-shadow p {
  margin: 8px 0 0;
  color: #60758a;
  line-height: 1.5;
}

:deep(.el-card__header) {
  font-weight: 700;
}

@media (max-width: 1180px) {
  .health-band {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .dispatch-console {
    padding: 12px;
  }

  .health-metrics,
  .filter-grid {
    grid-template-columns: 1fr;
  }

  .health-band {
    padding: 16px;
  }
}
</style>
