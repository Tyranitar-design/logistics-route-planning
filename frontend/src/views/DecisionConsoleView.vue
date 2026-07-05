<template>
  <div class="decision-console">
    <section class="console-hero cc-panel cc-panel--strong">
      <div>
        <span class="cc-kicker">AI Decision Layer</span>
        <h1>智能决策中枢</h1>
        <p>统一承载预测、异常、运营、调度 shadow、求解器健康和真实数据可见性。</p>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" type="primary" @click="loadConsoleData">
          <el-icon><Refresh /></el-icon>
          刷新控制塔
        </el-button>
        <el-button :loading="advancedShadowLoading" type="warning" @click="loadAdvancedShadow">
          <el-icon><Refresh /></el-icon>
          高级 Shadow
        </el-button>
        <el-button @click="agentDrawerVisible = true">专家 Agent</el-button>
        <el-button @click="go('/ml-prediction')">AI 预测</el-button>
        <el-button @click="go('/anomaly-detection')">异常检测</el-button>
        <el-button @click="go('/dispatch')">智能调度</el-button>
      </div>
    </section>

    <section class="demo-health-strip cc-panel cc-panel--strong" v-loading="loading">
      <div class="demo-health-head">
        <div>
          <span class="panel-eyebrow">Demo Readiness</span>
          <h2>演示健康条</h2>
        </div>
        <div class="demo-health-score">
          <strong>{{ formatNumber(demoReadiness.score) }}</strong>
          <el-tag :type="tagType(demoReadiness.status)" effect="dark">{{ demoReadiness.status || 'loading' }}</el-tag>
        </div>
      </div>
      <div class="demo-health-grid">
        <article v-for="item in demoHealthItems" :key="item.id" class="demo-health-item">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <el-tag size="small" :type="tagType(item.status)" effect="dark">{{ item.status }}</el-tag>
          <small>{{ item.helper }}</small>
        </article>
      </div>
      <div v-if="demoBlockingIssues.length || demoWarnings.length || demoRecommendedActions.length" class="demo-health-actions">
        <span v-for="issue in demoBlockingIssues" :key="`block-${issue}`" class="danger">{{ issue }}</span>
        <span v-for="warning in demoWarnings" :key="`warn-${warning}`">{{ warning }}</span>
        <span v-for="action in demoRecommendedActions.slice(0, 3)" :key="`action-${action}`">{{ action }}</span>
      </div>
    </section>

    <section class="metric-grid" v-loading="loading">
      <article
        v-for="metric in topMetrics"
        :key="metric.label"
        class="metric-tile cc-panel"
        :class="`metric-tile--${metric.tone || 'default'}`"
      >
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>{{ metric.helper }}</small>
      </article>
    </section>

    <section class="visual-grid" v-loading="loading">
      <article class="visual-panel cc-panel cc-panel--strong">
        <div class="panel-title-row">
          <div>
            <span class="panel-eyebrow">Visual Readiness</span>
            <h2>AI 能力雷达</h2>
          </div>
          <el-tag effect="dark" :type="controlTower.score >= 75 ? 'success' : 'warning'">
            {{ formatNumber(controlTower.score, 1) }}
          </el-tag>
        </div>
        <div ref="readinessRadarChart" class="visual-chart"></div>
      </article>

      <article class="visual-panel cc-panel cc-panel--strong">
        <div class="panel-title-row">
          <div>
            <span class="panel-eyebrow">Forecast</span>
            <h2>需求预测曲线</h2>
          </div>
          <el-tag effect="dark" type="success">shipment_facts</el-tag>
        </div>
        <div ref="forecastChart" class="visual-chart"></div>
      </article>

      <article class="visual-panel cc-panel cc-panel--strong">
        <div class="panel-title-row">
          <div>
            <span class="panel-eyebrow">Risk Distribution</span>
            <h2>异常信号分布</h2>
          </div>
          <el-tag effect="dark" :type="anomalySummary.anomaly_count ? 'warning' : 'success'">
            {{ formatNumber(anomalySummary.anomaly_count) }}
          </el-tag>
        </div>
        <div ref="anomalyChart" class="visual-chart"></div>
      </article>
    </section>

    <section class="console-grid">
      <article class="console-panel cc-panel cc-panel--strong control-tower">
        <div class="panel-title-row">
          <div>
            <span class="panel-eyebrow">Readiness</span>
            <h2>决策控制塔</h2>
          </div>
          <el-tag :type="controlTower.status === 'ready' ? 'success' : 'warning'" effect="dark">
            {{ controlTower.status }}
          </el-tag>
        </div>

        <div class="score-strip">
          <div>
            <span>总评分</span>
            <strong>{{ formatNumber(controlTower.score, 1) }}</strong>
          </div>
          <div>
            <span>AI</span>
            <strong>{{ componentScore('ai_prediction') }}</strong>
          </div>
          <div>
            <span>调度</span>
            <strong>{{ componentScore('dispatch_shadow') }}</strong>
          </div>
          <div>
            <span>求解器</span>
            <strong>{{ componentScore('solver_provider') }}</strong>
          </div>
        </div>

        <div class="component-table">
          <div class="table-head">
            <span>组件</span>
            <span>分数</span>
            <span>状态</span>
            <span>说明</span>
          </div>
          <div v-for="component in controlTower.components" :key="component.id" class="table-row">
            <span>{{ component.label }}</span>
            <strong>{{ formatNumber(component.score, 1) }}</strong>
            <el-tag size="small" :type="tagType(component.status)" effect="dark">{{ component.status }}</el-tag>
            <span>{{ component.detail }}</span>
          </div>
        </div>

        <div class="gate-list">
          <article v-for="gate in controlTower.gates" :key="gate.id" class="gate-item">
            <span :class="{ passed: gate.passed }"></span>
            <div>
              <strong>{{ gate.id }}</strong>
              <p>{{ gate.detail }}</p>
            </div>
          </article>
        </div>
      </article>

      <article class="console-panel cc-panel">
        <PanelHeader title="AI 预测" :result="results.predictionBaseline" />
        <div class="signal-list">
          <article v-for="task in predictionTasks" :key="task" class="signal-row">
            <div>
              <span>{{ task }}</span>
              <strong>{{ predictionTask(task)?.model || predictionTask(task)?.model_family || 'not_ready' }}</strong>
              <p>{{ metricLine(predictionTask(task)?.metrics) }}</p>
            </div>
            <el-tag size="small" :type="tagType(predictionTask(task)?.provider_status)" effect="dark">
              {{ predictionTask(task)?.provider_status || 'unknown' }}
            </el-tag>
          </article>
        </div>
        <TruthLine :source="results.predictionBaseline?.data" />
      </article>

      <article class="console-panel cc-panel ai-deep-panel">
        <PanelHeader title="AI 深度预测增强" :result="results.predictionTimeSeriesBenchmark" />
        <div class="score-strip">
          <div>
            <span>最佳时序模型</span>
            <strong>{{ timeSeriesBestModel }}</strong>
          </div>
          <div>
            <span>训练窗口</span>
            <strong>{{ formatNumber(timeSeriesReadiness.training_windows) }}</strong>
          </div>
          <div>
            <span>运力缺口天</span>
            <strong>{{ formatNumber(capacityGap.summary?.shortage_days) }}</strong>
          </div>
          <div>
            <span>成本风险天</span>
            <strong>{{ formatNumber(costVolatility.summary?.risk_days) }}</strong>
          </div>
        </div>
        <div class="forecast-ribbon">
          <article v-for="row in capacityForecastRows" :key="`cap-${row.date}`">
            <span>{{ row.date || '-' }}</span>
            <strong>{{ row.status || 'covered' }}</strong>
            <div class="mini-bar">
              <i :style="{ width: utilizationWidth(row) }" :class="{ warn: row.status === 'shortage' }"></i>
            </div>
            <small>{{ formatNumber(row.predicted_weight_kg, 0) }} kg</small>
          </article>
        </div>
        <div class="data-list">
          <article v-for="item in deepPredictionRecommendations" :key="item" class="data-row">
            <span>deep forecast</span>
            <strong>{{ item }}</strong>
          </article>
          <p v-if="!deepPredictionRecommendations.length" class="empty-note">
            {{ results.predictionTimeSeriesBenchmark.error || results.predictionCapacityGapForecast.error || '暂无深度预测增强建议。' }}
          </p>
        </div>
        <p class="panel-note">LSTM/TFT/深度预测当前作为 shadow readiness 展示，不直接替代调度硬约束。</p>
        <TruthLine :source="results.predictionTimeSeriesBenchmark?.data" />
      </article>

      <article class="console-panel cc-panel">
        <PanelHeader title="异常治理" :result="results.anomalyDetect" />
        <div class="anomaly-kpis">
          <div>
            <strong>{{ formatNumber(anomalySummary.records_scanned) }}</strong>
            <span>扫描记录</span>
          </div>
          <div>
            <strong>{{ formatNumber(anomalySummary.anomaly_count) }}</strong>
            <span>异常信号</span>
          </div>
          <div>
            <strong>{{ percent(anomalySummary.anomaly_rate) }}</strong>
            <span>异常率</span>
          </div>
        </div>
        <div class="data-list">
          <article v-for="item in anomalyRows" :key="item.anomaly_id || item.id" class="data-row">
            <span>{{ item.anomaly_type || item.type || 'unknown' }}</span>
            <strong>{{ laneText(item) }}</strong>
            <p>{{ item.explanation || item.message || item.fallback_reason || '暂无解释' }}</p>
          </article>
          <p v-if="!anomalyRows.length" class="empty-note">暂无异常明细或后端未返回结果。</p>
        </div>
      </article>

      <article class="console-panel cc-panel">
        <PanelHeader title="运营与成本" :result="results.operationsSummary" />
        <div class="score-strip">
          <div>
            <span>运费总额</span>
            <strong>{{ formatNumber(operationsKpis.total_freight, 0) }}</strong>
          </div>
          <div>
            <span>单均运费</span>
            <strong>{{ formatNumber(operationsKpis.avg_freight_per_paid_shipment, 2) }}</strong>
          </div>
          <div>
            <span>准时率</span>
            <strong>{{ percent(operationsKpis.on_time_rate) }}</strong>
          </div>
          <div>
            <span>异常率</span>
            <strong>{{ percent(operationsKpis.exception_rate) }}</strong>
          </div>
        </div>
        <div class="data-list">
          <article v-for="lane in topLanes" :key="lane.lane" class="data-row">
            <span>{{ lane.lane || 'lane' }}</span>
            <strong>{{ formatNumber(lane.total_freight, 0) }} · {{ percent(lane.freight_share) }}</strong>
            <p>{{ formatNumber(lane.shipment_count) }} 单 · {{ formatNumber(lane.freight_per_kg, 3) }} / kg</p>
          </article>
          <p v-if="!topLanes.length" class="empty-note">暂无真实成本运营总览。</p>
        </div>
      </article>

      <article class="console-panel cc-panel">
        <PanelHeader title="调度 Shadow" :result="results.dispatchHealth" />
        <div class="dispatch-grid">
          <div>
            <span>可调度订单</span>
            <strong>{{ formatNumber(dispatchHealth.dispatchable_orders) }}</strong>
          </div>
          <div>
            <span>可用车辆</span>
            <strong>{{ formatNumber(dispatchHealth.vehicle_source?.available_vehicles) }}</strong>
          </div>
          <div>
            <span>总载重</span>
            <strong>{{ formatNumber(dispatchHealth.vehicle_source?.total_capacity_weight_tons, 1) }} t</strong>
          </div>
          <div>
            <span>数据源</span>
            <strong>{{ dispatchHealth.data_source || 'not_connected' }}</strong>
          </div>
        </div>
        <p class="panel-note">{{ dispatchHealth.message || results.dispatchHealth?.error || '等待调度健康接口返回。' }}</p>
        <TruthLine :source="dispatchHealth" />
      </article>

      <article class="console-panel cc-panel dispatch-learning-panel">
        <PanelHeader title="调度学习链与 RL Shadow" :result="results.dispatchShadowBenchmark" />
        <div class="score-strip">
          <div>
            <span>学习样本</span>
            <strong>{{ formatNumber(dispatchLearningSummary.sample_count || dispatchLearningSummary.row_count) }}</strong>
          </div>
          <div>
            <span>最佳策略</span>
            <strong>{{ bestPolicyName }}</strong>
          </div>
          <div>
            <span>Reward R2</span>
            <strong>{{ formatNumber(rewardModel.metrics?.all?.r2, 2) }}</strong>
          </div>
          <div>
            <span>Fitted-Q</span>
            <strong>{{ formatNumber(fittedQ.summary?.sample_count) }}</strong>
          </div>
        </div>
        <div class="component-table compact">
          <div class="table-head">
            <span>模块</span>
            <span>证据</span>
            <span>状态</span>
            <span>边界</span>
          </div>
          <div v-for="row in dispatchLearningRows" :key="row.name" class="table-row">
            <span>{{ row.name }}</span>
            <strong>{{ row.value }}</strong>
            <el-tag size="small" :type="tagType(row.status)" effect="dark">{{ row.status }}</el-tag>
            <span>{{ row.boundary }}</span>
          </div>
        </div>
        <div class="data-list">
          <article v-for="item in dispatchLearningRecommendations" :key="item" class="data-row">
            <span>shadow recommendation</span>
            <strong>{{ item }}</strong>
          </article>
        </div>
        <p class="panel-note">DQN/PPO/Fitted-Q 只做候选策略评分和动态重调度建议；容量、唯一分配、时间窗仍由求解器保底。</p>
        <TruthLine :source="results.dispatchShadowBenchmark?.data" />
      </article>

      <article class="console-panel cc-panel">
        <PanelHeader title="求解器与 Gurobi" :result="results.solverBenchmark" />
        <div class="component-table compact">
          <div class="table-head">
            <span>solver</span>
            <span>distance</span>
            <span>objective</span>
            <span>status</span>
          </div>
          <div v-for="row in solverRows" :key="row.solver" class="table-row">
            <span>{{ row.solver || '-' }}</span>
            <strong>{{ formatNumber(row.total_distance_km, 1) }} km</strong>
            <span>{{ formatNumber(row.objective, 1) }}</span>
            <el-tag size="small" :type="tagType(row.provider_status || (row.success ? 'ok' : 'degraded'))" effect="dark">
              {{ row.provider_status || (row.success ? 'ok' : 'degraded') }}
            </el-tag>
          </div>
        </div>
        <p v-if="!solverRows.length" class="empty-note">暂无 solver benchmark 行或后端未连接。</p>
        <div class="provider-line">
          <span>Gurobi</span>
          <el-tag :type="gurobiHealth.available ? 'success' : 'warning'" effect="dark">
            {{ gurobiHealth.provider_status || (gurobiHealth.available ? 'ok' : 'degraded') }}
          </el-tag>
          <strong>{{ gurobiHealth.status || gurobiHealth.fallback_reason || results.gurobiHealth?.error || 'not_reported' }}</strong>
        </div>
      </article>

      <article class="console-panel cc-panel">
        <PanelHeader title="优化/AI 能力矩阵" :result="results.optimizationCapabilities" />
        <div class="score-strip">
          <div>
            <span>可用能力</span>
            <strong>{{ formatNumber(capabilitySummary.available) }}/{{ formatNumber(capabilitySummary.total) }}</strong>
          </div>
          <div>
            <span>精确求解</span>
            <strong>{{ yesNo(capabilitySummary.exact_solver_available) }}</strong>
          </div>
          <div>
            <span>RL Shadow</span>
            <strong>{{ yesNo(capabilitySummary.rl_shadow_available) }}</strong>
          </div>
          <div>
            <span>地理空间</span>
            <strong>{{ yesNo(capabilitySummary.geospatial_available) }}</strong>
          </div>
        </div>
        <div class="component-table compact">
          <div class="table-head">
            <span>capability</span>
            <span>version</span>
            <span>status</span>
            <span>mode</span>
          </div>
          <div v-for="row in capabilityHighlights" :key="row.id" class="table-row">
            <span>{{ row.label }}</span>
            <strong>{{ row.version || '-' }}</strong>
            <el-tag size="small" :type="tagType(row.provider_status)" effect="dark">
              {{ row.provider_status || 'unknown' }}
            </el-tag>
            <span>{{ row.fallback_reason || row.execution_mode || row.category }}</span>
          </div>
        </div>
        <p class="panel-note">能力矩阵是安全探测：不返回 key、密码或 license 内容；RL/深度模型仍保持 shadow / background 边界。</p>
        <TruthLine :source="results.optimizationCapabilities?.data" />
      </article>

      <article class="console-panel cc-panel">
        <PanelHeader title="模块建议" :result="results.operationsScorecard" />
        <div class="data-list">
          <article v-for="item in recommendations" :key="item" class="data-row">
            <span>recommendation</span>
            <strong>{{ item }}</strong>
          </article>
        </div>
        <p class="panel-note">该页面是 Vue 单前端只读控制台，不写调度或物流事实表。</p>
      </article>
    </section>

    <el-drawer v-model="agentDrawerVisible" size="520px" title="专家 Agent" append-to-body class="agent-drawer">
      <div class="agent-panel">
        <el-alert
          :type="agentState.api_key_configured ? 'success' : 'warning'"
          :closable="false"
          show-icon
          :title="agentState.api_key_configured ? 'MiniMax-M3 已由后端环境变量启用' : 'MiniMax-M3 未配置或处于降级'"
          :description="agentState.fallback_reason || 'Agent 仅提供建议、解释和 dry-run 草稿；写入动作必须人工确认。'"
        />

        <div class="agent-form">
          <label>
            <span>角色</span>
            <el-select v-model="agentForm.agent_role" class="agent-field">
              <el-option v-for="role in agentRoles" :key="role.value" :label="role.label" :value="role.value" />
            </el-select>
          </label>
          <label>
            <span>只读工具</span>
            <el-select v-model="agentForm.tool_name" class="agent-field">
              <el-option label="运行态能力" value="runtime_capabilities" />
              <el-option label="GIS Provider 健康" value="gis_provider_health" />
              <el-option label="调度预览" value="dispatch_preview" />
              <el-option label="企业汇总" value="enterprise_summary" />
            </el-select>
          </label>
          <label>
            <span>问题</span>
            <el-input
              v-model="agentForm.question"
              type="textarea"
              :rows="4"
              resize="none"
              maxlength="800"
              show-word-limit
            />
          </label>
        </div>

        <div class="agent-actions">
          <el-button :loading="agentPreviewLoading" @click="runAgentToolPreview">工具预演</el-button>
          <el-button :loading="agentChatLoading" type="primary" @click="runAgentChat">获取建议</el-button>
          <el-button :loading="agentScenarioLoading" type="warning" @click="createAgentScenarioDraft">生成 dry-run 草稿</el-button>
        </div>

        <div class="agent-boundary">
          <span>边界</span>
          <strong>advisory_with_human_confirmation</strong>
          <small>默认 persist:false，不修改订单、车辆、shipment_facts 或调度 assignments。</small>
        </div>

        <div class="agent-output-list">
          <section v-if="agentPreviewResult" class="agent-output">
            <div class="panel-title-row">
              <div>
                <span class="panel-eyebrow">Preview</span>
                <h2>工具预演</h2>
              </div>
              <el-tag :type="tagType(agentPreviewResult.provider_status)" effect="dark">
                {{ agentPreviewResult.provider_status || 'unknown' }}
              </el-tag>
            </div>
            <pre>{{ formatJson(agentPreviewResult.preview || agentPreviewResult) }}</pre>
          </section>

          <section v-if="agentChatResult" class="agent-output">
            <div class="panel-title-row">
              <div>
                <span class="panel-eyebrow">Advice</span>
                <h2>{{ agentChatResult.agent_label || 'Agent 建议' }}</h2>
              </div>
              <el-tag :type="tagType(agentChatResult.provider_status)" effect="dark">
                {{ agentChatResult.provider_status || 'unknown' }}
              </el-tag>
            </div>
            <div class="agent-answer-text">{{ agentChatResult.answer || agentChatResult.fallback_reason }}</div>
          </section>

          <section v-if="agentScenarioResult" class="agent-output">
            <div class="panel-title-row">
              <div>
                <span class="panel-eyebrow">Dry Run</span>
                <h2>场景草稿</h2>
              </div>
              <el-tag :type="agentScenarioResult.persisted ? 'danger' : 'success'" effect="dark">
                persisted: {{ yesNo(agentScenarioResult.persisted) }}
              </el-tag>
            </div>
            <pre>{{ formatJson(agentScenarioResult) }}</pre>
          </section>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  evaluatePredictionBaselines,
  evaluateTimeSeriesBenchmark,
  forecastCapacityGap,
  forecastCostVolatility,
  getDemandForecast,
  getPredictionHealth,
  getPredictionModelStatus,
  getPredictionScorecard
} from '@/api/aiPrediction'
import {
  detectShipmentAnomalies,
  getAiAnomalyHealth,
  getAiAnomalyScorecard
} from '@/api/aiAnomaly'
import { getOperationsScorecard, getOperationsSummary } from '@/api/analytics'
import {
  getDispatchFittedQShadowModel,
  getDispatchHealth,
  getDispatchLearningDataset,
  getDispatchPolicyScorer,
  getDispatchRewardModel,
  getDispatchRlShadowRunner,
  getDispatchShadowBenchmark,
  getDispatchShadowBenchmarkSnapshot
} from '@/api/dispatch'
import { getGurobiHealth, getOptimizationCapabilities, getSolverBenchmarkDemo } from '@/api/optimization'
import { getRuntimeCapabilities } from '@/api/runtime'
import { getGisProviderHealth } from '@/api/gis'
import { chatWithAgent, previewAgentTool } from '@/api/agent'
import { createDecisionScenario } from '@/api/decision'

const router = useRouter()
const loading = ref(false)
const advancedShadowLoading = ref(false)
const agentDrawerVisible = ref(false)
const agentPreviewLoading = ref(false)
const agentChatLoading = ref(false)
const agentScenarioLoading = ref(false)
const generatedAt = ref(null)
const predictionTasks = ['demand', 'eta', 'delay', 'cost']
const readinessRadarChart = ref(null)
const forecastChart = ref(null)
const anomalyChart = ref(null)
let charts = []

const agentRoles = [
  { label: 'GIS 路网专家', value: 'gis_expert' },
  { label: '智能调度专家', value: 'dispatch_expert' },
  { label: '成本风险专家', value: 'cost_risk_expert' },
  { label: '仓网设计专家', value: 'network_design_expert' },
  { label: '数据质量专家', value: 'data_quality_expert' },
  { label: '运营报告专家', value: 'operations_report_expert' }
]

const agentForm = ref({
  agent_role: 'operations_report_expert',
  tool_name: 'runtime_capabilities',
  question: '请基于当前控制塔状态，指出演示前需要关注的阻塞项、降级原因和下一步建议。'
})
const agentPreviewResult = ref(null)
const agentChatResult = ref(null)
const agentScenarioResult = ref(null)

const emptyResult = () => ({ ok: false, data: null, error: 'NOT_LOADED' })

const results = ref({
  predictionHealth: emptyResult(),
  predictionBaseline: emptyResult(),
  predictionForecast: emptyResult(),
  predictionTimeSeriesBenchmark: emptyResult(),
  predictionCapacityGapForecast: emptyResult(),
  predictionCostVolatilityForecast: emptyResult(),
  predictionModelStatus: emptyResult(),
  predictionScorecard: emptyResult(),
  anomalyHealth: emptyResult(),
  anomalyDetect: emptyResult(),
  anomalyScorecard: emptyResult(),
  operationsSummary: emptyResult(),
  operationsScorecard: emptyResult(),
  dispatchHealth: emptyResult(),
  dispatchLearningDataset: emptyResult(),
  dispatchPolicyScorer: emptyResult(),
  dispatchRewardModel: emptyResult(),
  dispatchRlShadowRunner: emptyResult(),
  dispatchFittedQShadowModel: emptyResult(),
  dispatchShadowBenchmark: emptyResult(),
  dispatchShadowBenchmarkSnapshot: emptyResult(),
  gurobiHealth: emptyResult(),
  optimizationCapabilities: emptyResult(),
  solverBenchmark: emptyResult(),
  runtimeCapabilities: emptyResult(),
  gisProviderHealth: emptyResult()
})

const PanelHeader = defineComponent({
  name: 'DecisionConsolePanelHeader',
  props: {
    title: { type: String, required: true },
    result: { type: Object, default: () => ({}) }
  },
  setup(props) {
    return () =>
      h('div', { class: 'panel-title-row' }, [
        h('div', [h('span', { class: 'panel-eyebrow' }, 'Module'), h('h2', props.title)]),
        h(
          'span',
          { class: ['result-pill', props.result?.ok ? 'result-pill--ok' : 'result-pill--warn'] },
          props.result?.ok ? 'ok' : 'degraded'
        )
      ])
  }
})

const TruthLine = defineComponent({
  name: 'DecisionConsoleTruthLine',
  props: {
    source: { type: Object, default: () => ({}) }
  },
  setup(props) {
    return () =>
      h('div', { class: 'truth-line' }, [
        h('span', `source: ${props.source?.data_source || 'unknown'}`),
        h('span', `truth: ${props.source?.authenticity_level || '-'}`),
        h('span', `provider: ${props.source?.provider_status || 'unknown'}`),
        props.source?.fallback_reason ? h('span', `fallback: ${props.source.fallback_reason}`) : null
      ])
  }
})

async function safeCall(key, runner) {
  try {
    const data = await runner()
    return {
      key,
      ok: data?.success !== false,
      data,
      error: data?.success === false ? data?.fallback_reason || data?.error || 'REQUEST_DEGRADED' : null
    }
  } catch (error) {
    return {
      key,
      ok: false,
      data: error?.response?.data || null,
      error: error?.response?.data?.error || error?.response?.data?.fallback_reason || error?.message || 'REQUEST_FAILED'
    }
  }
}

async function runCallBatches(factories, batchSize = 2) {
  const items = []
  for (let index = 0; index < factories.length; index += batchSize) {
    const batch = factories.slice(index, index + batchSize)
    items.push(...(await Promise.all(batch.map((factory) => factory()))))
  }
  return items
}

async function loadConsoleData() {
  loading.value = true
  try {
    const calls = await runCallBatches([
      () => safeCall('predictionHealth', getPredictionHealth),
      () => safeCall('predictionBaseline', () =>
      evaluatePredictionBaselines({
        tasks: predictionTasks,
        horizon_days: 7,
        runtime_profile: 'interactive',
        limit: 5000
      })
      ),
      () => safeCall('predictionForecast', () => getDemandForecast(14, null, 5000, { runtime_profile: 'interactive' })),
      () => safeCall('predictionTimeSeriesBenchmark', () =>
      evaluateTimeSeriesBenchmark({
        task: 'demand',
        horizon_days: 14,
        test_days: 14,
        sequence_length: 14,
        runtime_profile: 'interactive',
        limit: 5000
      })
      ),
      () => safeCall('predictionCapacityGapForecast', () =>
      forecastCapacityGap({
        horizon_days: 14,
        test_days: 14,
        sequence_length: 14,
        runtime_profile: 'interactive',
        limit: 5000
      })
      ),
      () => safeCall('predictionCostVolatilityForecast', () =>
      forecastCostVolatility({
        horizon_days: 14,
        test_days: 14,
        sequence_length: 14,
        runtime_profile: 'interactive',
        limit: 5000
      })
      ),
      () => safeCall('predictionModelStatus', getPredictionModelStatus),
      () => safeCall('predictionScorecard', () =>
      getPredictionScorecard({
        horizon_days: 14,
        test_days: 14,
        sequence_length: 14,
        runtime_profile: 'interactive',
        limit: 5000
      })
      ),
      () => safeCall('anomalyHealth', getAiAnomalyHealth),
      () => safeCall('anomalyDetect', () =>
      detectShipmentAnomalies({
        runtime_profile: 'interactive',
        limit: 5000,
        anomaly_limit: 8,
        use_ml: false
      })
      ),
      () => safeCall('anomalyScorecard', () =>
      getAiAnomalyScorecard({
        runtime_profile: 'interactive',
        limit: 5000,
        anomaly_limit: 80,
        use_ml: false
      })
      ),
      () => safeCall('operationsSummary', () =>
      getOperationsSummary({
        limit: 5000,
        trend_days: 30,
        lane_limit: 8
      })
      ),
      () => safeCall('operationsScorecard', () =>
      getOperationsScorecard({
        limit: 5000,
        trend_days: 30,
        lane_limit: 8
      })
      ),
      () => safeCall('dispatchHealth', getDispatchHealth),
      () => safeCall('dispatchLearningDataset', getDispatchLearningDataset),
      () => safeCall('dispatchPolicyScorer', getDispatchPolicyScorer),
      () => safeCall('dispatchRewardModel', getDispatchRewardModel),
      () => safeCall('dispatchShadowBenchmark', getDispatchShadowBenchmark),
      () => safeCall('gurobiHealth', getGurobiHealth),
      () => safeCall('optimizationCapabilities', getOptimizationCapabilities),
      () => safeCall('solverBenchmark', getSolverBenchmarkDemo),
      () => safeCall('runtimeCapabilities', () => getRuntimeCapabilities({ solver_probe: false })),
      () => safeCall('gisProviderHealth', getGisProviderHealth)
    ], 2)

    results.value = {
      ...results.value,
      ...calls.reduce((acc, item) => {
        acc[item.key] = item
        return acc
      }, {})
    }
    generatedAt.value = new Date().toISOString()
    await nextTick()
    renderVisualCharts()

    if (calls.some((item) => !item.ok)) {
      ElMessage.warning('部分控制塔模块处于降级状态，页面已保留可解释原因。')
    }
  } finally {
    loading.value = false
  }
}

async function loadAdvancedShadow() {
  advancedShadowLoading.value = true
  const fullShadowParams = {
    runtime_profile: 'full',
    scenario_limit: 50,
    row_limit: 100,
    anomaly_source_limit: 50000,
    anomaly_limit: 80,
    use_ml: false,
    top_k: 10,
    test_ratio: 0.3
  }
  try {
    const calls = await runCallBatches([
      () => safeCall('dispatchRlShadowRunner', () => getDispatchRlShadowRunner(fullShadowParams)),
      () => safeCall('dispatchFittedQShadowModel', () => getDispatchFittedQShadowModel(fullShadowParams)),
      () => safeCall('dispatchShadowBenchmarkSnapshot', () => getDispatchShadowBenchmarkSnapshot(fullShadowParams)),
      () => safeCall('dispatchShadowBenchmark', () => getDispatchShadowBenchmark(fullShadowParams))
    ], 1)

    results.value = {
      ...results.value,
      ...calls.reduce((acc, item) => {
        acc[item.key] = item
        return acc
      }, {})
    }
    await nextTick()
    renderVisualCharts()
    if (calls.some((item) => !item.ok)) {
      ElMessage.warning('高级 Shadow 已返回降级信息，请查看模块边界和 fallback_reason。')
    } else {
      ElMessage.success('高级 Shadow 刷新完成')
    }
  } finally {
    advancedShadowLoading.value = false
  }
}

function buildAgentContext() {
  return {
    page: 'DecisionConsoleView',
    generated_at: generatedAt.value,
    demo_readiness: demoReadiness.value,
    database_runtime: runtimeState.value.database_runtime,
    registered_capabilities: {
      summary: runtimeRegisteredSummary.value,
      missing: runtimeState.value.registered_capabilities?.missing || []
    },
    gis_truth: {
      provider_status: gisState.value.provider_status,
      distance_source: gisState.value.distance_source,
      path_source: gisState.value.path_source,
      authenticity_level: gisState.value.authenticity_level,
      fallback_reason: gisState.value.fallback_reason
    },
    dispatch_health: {
      provider_status: dispatchHealth.value.provider_status,
      dispatchable_orders: dispatchHealth.value.dispatchable_orders,
      data_source: dispatchHealth.value.data_source,
      fallback_reason: dispatchHealth.value.fallback_reason
    },
    solver_summary: {
      optional_capabilities: capabilitySummary.value,
      gurobi: {
        available: gurobiHealth.value.available,
        provider_status: gurobiHealth.value.provider_status,
        fallback_reason: gurobiHealth.value.fallback_reason
      }
    },
    boundaries: runtimeState.value.platform_boundaries || {
      agent_mode: 'advisory_with_human_confirmation',
      rl_policy_mode: 'shadow_rerank_only'
    }
  }
}

async function runAgentToolPreview() {
  agentPreviewLoading.value = true
  try {
    const data = await previewAgentTool({
      tool_name: agentForm.value.tool_name,
      parameters: {
        persist: false,
        runtime_profile: 'interactive',
        limit: 20,
        policy_mode: 'solver_only',
        context: buildAgentContext()
      }
    })
    agentPreviewResult.value = data
    if (data?.success === false) {
      ElMessage.warning(data.fallback_reason || 'Agent 工具预演已降级。')
    } else {
      ElMessage.success('只读工具预演完成')
    }
  } catch (error) {
    agentPreviewResult.value = error?.response?.data || {
      provider_status: 'degraded',
      fallback_reason: error?.message || 'AGENT_TOOL_PREVIEW_FAILED'
    }
  } finally {
    agentPreviewLoading.value = false
  }
}

async function runAgentChat() {
  if (!String(agentForm.value.question || '').trim()) {
    ElMessage.warning('请先输入一个要交给专家 Agent 的问题。')
    return
  }
  agentChatLoading.value = true
  try {
    const data = await chatWithAgent({
      agent_role: agentForm.value.agent_role,
      question: agentForm.value.question,
      task_context: buildAgentContext(),
      timeout_seconds: 45,
      temperature: 0.2
    })
    agentChatResult.value = data
    if (data?.success === false) {
      ElMessage.warning(data.fallback_reason || 'Agent 当前处于降级建议模式。')
    } else {
      ElMessage.success('专家 Agent 建议已返回')
    }
  } catch (error) {
    agentChatResult.value = error?.response?.data || {
      provider_status: 'degraded',
      fallback_reason: error?.message || 'AGENT_CHAT_FAILED',
      answer: 'Agent 请求未完成，请检查后端 /api/agent/chat 或 MiniMax 环境变量。'
    }
  } finally {
    agentChatLoading.value = false
  }
}

async function createAgentScenarioDraft() {
  agentScenarioLoading.value = true
  try {
    const data = await createDecisionScenario({
      scenario_type: 'dispatch',
      name: '专家 Agent dry-run 草稿',
      persist: false,
      provider_status: agentChatResult.value?.provider_status || agentPreviewResult.value?.provider_status || 'preview',
      summary: {
        source: 'decision_console_agent_drawer',
        agent_role: agentForm.value.agent_role,
        tool_name: agentForm.value.tool_name,
        has_advice: Boolean(agentChatResult.value?.answer)
      },
      payload: {
        question: agentForm.value.question,
        context: buildAgentContext(),
        tool_preview: agentPreviewResult.value?.preview || null,
        advice: agentChatResult.value?.answer || null
      },
      diagnostics: {
        business_mutation: 'none',
        persist: false,
        requires_human_confirmation: true
      }
    })
    agentScenarioResult.value = data
    ElMessage.success('已生成 dry-run 场景草稿，未写业务事实表。')
  } catch (error) {
    agentScenarioResult.value = error?.response?.data || {
      provider_status: 'degraded',
      fallback_reason: error?.message || 'DECISION_SCENARIO_DRY_RUN_FAILED',
      persisted: false
    }
  } finally {
    agentScenarioLoading.value = false
  }
}

function boundedScore(value, fallback = 0) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return fallback
  return Math.max(0, Math.min(100, numberValue))
}

function averageScore(values) {
  const numbers = values.filter((value) => Number.isFinite(Number(value)))
  if (!numbers.length) return 0
  return numbers.reduce((sum, value) => sum + Number(value), 0) / numbers.length
}

function formatNumber(value, digits = 0) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return '-'
  return new Intl.NumberFormat('zh-CN', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits
  }).format(numberValue)
}

function percent(value) {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return '-'
  return `${formatNumber(numberValue * 100, 1)}%`
}

function metricLine(metrics = {}) {
  if (!metrics || typeof metrics !== 'object') return '暂无指标'
  const entries = Object.entries(metrics).filter(([, value]) => value !== null && value !== undefined)
  if (!entries.length) return '暂无指标'
  return entries
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${formatNumber(value, 3)}`)
    .join(' · ')
}

function tagType(status) {
  const normalized = String(status || '').toLowerCase()
  if (['ok', 'ready', 'success', 'passed'].includes(normalized)) return 'success'
  if (['critical', 'danger', 'unsafe', 'failed', 'blocked'].includes(normalized)) return 'danger'
  if (['watch', 'warning', 'warn', 'degraded', 'shadow', 'auth_required'].includes(normalized)) return 'warning'
  return 'info'
}

function yesNo(value) {
  return value ? 'yes' : 'no'
}

function formatJson(value) {
  try {
    return JSON.stringify(value || {}, null, 2)
  } catch (error) {
    return String(value || '')
  }
}

function laneText(item = {}) {
  const origin = item.origin_city || item.origin || item.source || '-'
  const destination = item.destination_city || item.destination || item.target || '-'
  return `${origin} -> ${destination}`
}

function go(path) {
  router.push(path)
}

function predictionTask(task) {
  return results.value.predictionBaseline?.data?.results?.[task]
}

const predictionHealth = computed(() => results.value.predictionHealth?.data || {})
const anomalyHealth = computed(() => results.value.anomalyHealth?.data || {})
const anomalySummary = computed(() => results.value.anomalyDetect?.data?.summary || {})
const operationsKpis = computed(() => results.value.operationsSummary?.data?.kpis || {})
const dispatchHealth = computed(() => results.value.dispatchHealth?.data || {})
const gurobiHealth = computed(() => results.value.gurobiHealth?.data || {})
const timeSeries = computed(() => results.value.predictionTimeSeriesBenchmark?.data || {})
const capacityGap = computed(() => results.value.predictionCapacityGapForecast?.data || {})
const costVolatility = computed(() => results.value.predictionCostVolatilityForecast?.data || {})
const dispatchLearningDataset = computed(() => results.value.dispatchLearningDataset?.data || {})
const policyScorer = computed(() => results.value.dispatchPolicyScorer?.data || {})
const rewardModel = computed(() => results.value.dispatchRewardModel?.data || {})
const rlShadow = computed(() => results.value.dispatchRlShadowRunner?.data || {})
const fittedQ = computed(() => results.value.dispatchFittedQShadowModel?.data || {})
const shadowSnapshot = computed(() => results.value.dispatchShadowBenchmarkSnapshot?.data || {})
const capabilitySummary = computed(() => results.value.optimizationCapabilities?.data?.summary || {})
const capabilityRows = computed(() => results.value.optimizationCapabilities?.data?.capabilities || [])
const runtimeState = computed(() => results.value.runtimeCapabilities?.data || {})
const runtimeRegisteredSummary = computed(() => runtimeState.value.registered_capabilities?.summary || {})
const demoReadiness = computed(() => runtimeState.value.demo_readiness || {})
const demoBlockingIssues = computed(() => demoReadiness.value.blocking_issues || [])
const demoWarnings = computed(() => demoReadiness.value.warnings || [])
const demoRecommendedActions = computed(() => demoReadiness.value.recommended_actions || [])
const agentState = computed(() => runtimeState.value.agent_gateway || {})
const gisState = computed(() => results.value.gisProviderHealth?.data || {})
const topLanes = computed(() => (results.value.operationsSummary?.data?.top_lanes || []).slice(0, 4))
const anomalyRows = computed(() => (results.value.anomalyDetect?.data?.anomalies || []).slice(0, 5))
const solverRows = computed(() => (results.value.solverBenchmark?.data?.rankings || []).slice(0, 5))
const forecastRows = computed(() => (results.value.predictionForecast?.data?.forecast || []).slice(0, 14))
const capacityForecastRows = computed(() => (capacityGap.value.forecast || []).slice(0, 7))
const timeSeriesReadiness = computed(() => timeSeries.value.deep_learning_readiness || {})
const timeSeriesBestModel = computed(() => timeSeries.value.backtest?.best_model?.model_id || 'not_ready')
const dispatchLearningSummary = computed(() => dispatchLearningDataset.value.summary || dispatchLearningDataset.value.readiness || {})
const bestPolicyName = computed(() => policyScorer.value.best_policy?.name || policyScorer.value.best_policy?.policy_id || 'not_ready')

const demoHealthItems = computed(() => {
  const db = runtimeState.value.database_runtime || {}
  const checks = demoReadiness.value.checks || {}
  const solverProviderStatus = runtimeState.value.solver_registry?.provider_status || capabilitySummary.value.provider_status
  return [
    {
      id: 'postgresql',
      label: 'PostgreSQL',
      value: `${db.backend || '-'} · ${formatNumber(db.shipment_facts)}`,
      status: checks.postgresql_connected && checks.shipment_facts_visible ? 'ok' : 'blocked',
      helper: db.primary_order_source || db.warning || 'shipment_facts'
    },
    {
      id: 'runtime_routes',
      label: '运行态路由',
      value: `${formatNumber(runtimeRegisteredSummary.value.available)}/${formatNumber(runtimeRegisteredSummary.value.total)}`,
      status: checks.expected_routes_registered ? 'ok' : 'degraded',
      helper: runtimeState.value.interpreter?.using_project_venv ? 'backend .venv' : '可能是旧后端进程'
    },
    {
      id: 'gis_provider',
      label: 'GIS Provider',
      value: `${gisState.value.authenticity_level || '-'} · ${gisState.value.distance_source || '-'}`,
      status: gisState.value.provider_status || 'unknown',
      helper: gisState.value.fallback_reason || gisState.value.path_source || 'PostGIS / 高德 / 天地图 / 本地图算法'
    },
    {
      id: 'agent_gateway',
      label: '专家 Agent',
      value: agentState.value.api_key_configured ? 'MiniMax-M3' : 'degraded',
      status: agentState.value.provider_status || 'degraded',
      helper: agentState.value.fallback_reason || '建议 + 人工确认'
    },
    {
      id: 'dispatch_health',
      label: '调度健康',
      value: formatNumber(dispatchHealth.value.dispatchable_orders),
      status: results.value.dispatchHealth?.ok ? dispatchHealth.value.provider_status || 'ok' : 'degraded',
      helper: dispatchHealth.value.fallback_reason || dispatchHealth.value.data_source || results.value.dispatchHealth?.error || 'dispatch health'
    },
    {
      id: 'solver_runtime',
      label: '可选 Solver',
      value: `${formatNumber(capabilitySummary.value.available)}/${formatNumber(capabilitySummary.value.total)}`,
      status: solverProviderStatus || 'not_checked',
      helper: `Gurobi ${yesNo(gurobiHealth.value.available)} · RL ${yesNo(capabilitySummary.value.rl_shadow_available)}`
    }
  ]
})

const controlTower = computed(() => {
  const predictionScore = boundedScore(
    results.value.predictionScorecard?.data?.summary?.readiness_score,
    ((results.value.predictionBaseline?.data?.summary?.ready_tasks?.length || 0) / 4) * 100
  )
  const anomalyScore = boundedScore(
    results.value.anomalyScorecard?.data?.summary?.readiness_score,
    results.value.anomalyDetect?.data?.summary ? 60 : 0
  )
  const operationsScore = boundedScore(results.value.operationsScorecard?.data?.summary?.readiness_score, 0)
  const dispatchScore = boundedScore(
    results.value.dispatchShadowBenchmark?.data?.summary?.readiness_score,
    dispatchHealth.value.dispatchable_orders ? 65 : results.value.dispatchHealth?.ok ? 40 : 0
  )
  const solverCount = Number(results.value.solverBenchmark?.data?.summary?.solver_count || 0)
  const feasibleSolverCount = Number(results.value.solverBenchmark?.data?.summary?.feasible_solver_count || 0)
  const solverRatioScore = solverCount ? (feasibleSolverCount / solverCount) * 100 : results.value.solverBenchmark?.ok ? 45 : 0
  const gurobiScore = gurobiHealth.value.available ? 100 : results.value.gurobiHealth?.ok ? 55 : 0
  const solverScore = boundedScore(averageScore([solverRatioScore, gurobiScore]))
  const capabilityTotal = Number(capabilitySummary.value.total || 0)
  const capabilityScore = capabilityTotal
    ? boundedScore((Number(capabilitySummary.value.available || 0) / capabilityTotal) * 100)
    : results.value.optimizationCapabilities?.ok
      ? 50
      : 0
  const runtimeTotal = Number(runtimeRegisteredSummary.value.total || 0)
  const runtimeAvailable = Number(runtimeRegisteredSummary.value.available || 0)
  const runtimeScore = runtimeTotal ? boundedScore((runtimeAvailable / runtimeTotal) * 100) : results.value.runtimeCapabilities?.ok ? 50 : 0
  const gisSummary = gisState.value.summary || {}
  const gisScore = boundedScore(
    averageScore([
      gisSummary.real_provider_available ? 100 : 35,
      gisSummary.postgis_available ? 100 : 45,
      gisSummary.local_graph_available ? 100 : 45,
      gisSummary.geospatial_runtime_available ? 100 : 60
    ])
  )

  const components = [
    {
      id: 'runtime_process',
      label: 'Runtime Process',
      score: runtimeScore,
      status: runtimeState.value.provider_status || (runtimeScore >= 90 ? 'ok' : 'degraded'),
      detail: `${formatNumber(runtimeAvailable)}/${formatNumber(runtimeTotal)} routes · venv ${yesNo(
        runtimeState.value.interpreter?.using_project_venv
      )}`
    },
    {
      id: 'gis_provider',
      label: 'GIS Provider',
      score: gisScore,
      status: gisState.value.provider_status || (gisScore >= 80 ? 'ok' : 'degraded'),
      detail: `${gisState.value.authenticity_level || '-'} · ${gisState.value.distance_source || 'unknown'}`
    },
    {
      id: 'ai_prediction',
      label: 'AI Prediction',
      score: predictionScore,
      status: results.value.predictionScorecard?.data?.summary?.status || (predictionScore >= 75 ? 'ready' : 'watch'),
      detail: `${results.value.predictionBaseline?.data?.summary?.ready_tasks?.length || 0}/4 tasks · ${
        results.value.predictionScorecard?.data?.model_family || 'baseline'
      }`
    },
    {
      id: 'anomaly_governance',
      label: 'Anomaly Governance',
      score: anomalyScore,
      status: results.value.anomalyScorecard?.data?.summary?.status || (anomalyScore >= 75 ? 'ready' : 'watch'),
      detail: `${formatNumber(results.value.anomalyScorecard?.data?.summary?.high_risk_count || 0)} high risk · ${formatNumber(
        anomalySummary.value.anomaly_count
      )} signals`
    },
    {
      id: 'operations_cost',
      label: 'Operations & Cost',
      score: operationsScore,
      status: results.value.operationsScorecard?.data?.summary?.status || (operationsScore >= 75 ? 'ready' : 'watch'),
      detail: `${formatNumber(operationsKpis.value.total_freight, 0)} freight · ${percent(operationsKpis.value.on_time_rate)} on-time`
    },
    {
      id: 'dispatch_shadow',
      label: 'Dispatch Shadow',
      score: dispatchScore,
      status: results.value.dispatchShadowBenchmark?.data?.summary?.deployable
        ? 'unsafe'
        : results.value.dispatchShadowBenchmark?.data?.provider_status || 'shadow',
      detail: `${formatNumber(dispatchHealth.value.dispatchable_orders)} orders · deployable ${yesNo(
        results.value.dispatchShadowBenchmark?.data?.summary?.deployable
      )}`
    },
    {
      id: 'solver_provider',
      label: 'Solver & Provider',
      score: solverScore,
      status: gurobiHealth.value.available ? 'ok' : gurobiHealth.value.provider_status || 'degraded',
      detail: `${formatNumber(feasibleSolverCount)}/${formatNumber(solverCount)} feasible · Gurobi ${yesNo(gurobiHealth.value.available)}`
    },
    {
      id: 'optional_capabilities',
      label: 'Optional Runtime',
      score: capabilityScore,
      status: capabilitySummary.value.provider_status || (capabilityScore >= 80 ? 'ok' : 'degraded'),
      detail: `${formatNumber(capabilitySummary.value.available)}/${formatNumber(capabilitySummary.value.total)} runtimes · RL ${yesNo(
        capabilitySummary.value.rl_shadow_available
      )}`
    }
  ]

  const score = boundedScore(averageScore(components.map((component) => component.score)))
  const gates = [
    {
      id: 'real_data_visible',
      passed: Boolean(predictionHealth.value?.summary?.total_records || results.value.operationsSummary?.data?.summary?.records_scanned),
      detail: 'shipment_facts 真实数据证据可见。'
    },
    {
      id: 'scorecards_loaded',
      passed: Boolean(results.value.predictionScorecard?.ok || results.value.anomalyScorecard?.ok || results.value.operationsScorecard?.ok),
      detail: '至少一个模块级 readiness scorecard 可用。'
    },
    {
      id: 'dispatch_readable',
      passed: Boolean(results.value.dispatchHealth?.ok),
      detail: '调度健康接口可通过当前 Vue 登录态读取。'
    },
    {
      id: 'solver_benchmark_visible',
      passed: Boolean(results.value.solverBenchmark?.ok || results.value.gurobiHealth?.ok),
      detail: '求解器 benchmark 或 Gurobi provider health 可见。'
    },
    {
      id: 'optional_capabilities_visible',
      passed: Boolean(results.value.optimizationCapabilities?.ok),
      detail: '可选优化/AI/RL/地理空间 runtime 能力矩阵可见。'
    },
    {
      id: 'runtime_routes_visible',
      passed: Boolean(results.value.runtimeCapabilities?.ok && !runtimeState.value.registered_capabilities?.missing?.length),
      detail: '运行态关键接口注册摘要可见，能识别旧后端进程。'
    },
    {
      id: 'gis_provider_truth_visible',
      passed: Boolean(results.value.gisProviderHealth?.ok),
      detail: 'GIS provider、PostGIS 和本地图算法健康状态可见。'
    },
    {
      id: 'shadow_boundary_preserved',
      passed: results.value.dispatchShadowBenchmark?.data?.summary?.deployable !== true,
      detail: 'AI/RL 调度输出仍保持 shadow / non-deployable 边界。'
    }
  ]

  return {
    score,
    status: score >= 85 ? 'ready' : score >= 65 ? 'watch' : 'needs_work',
    components,
    gates
  }
})

const topMetrics = computed(() => [
  {
    label: '控制塔评分',
    value: formatNumber(controlTower.value.score, 1),
    helper: controlTower.value.status,
    tone: controlTower.value.score >= 85 ? 'good' : 'warn'
  },
  {
    label: '真实运单',
    value: formatNumber(predictionHealth.value?.summary?.total_records || anomalyHealth.value?.summary?.total_records),
    helper: 'shipment_facts',
    tone: 'good'
  },
  {
    label: '异常信号',
    value: formatNumber(anomalySummary.value.anomaly_count),
    helper: percent(anomalySummary.value.anomaly_rate),
    tone: anomalySummary.value.anomaly_count ? 'warn' : 'good'
  },
  {
    label: '可调度订单',
    value: formatNumber(dispatchHealth.value.dispatchable_orders),
    helper: 'dispatch health',
    tone: 'default'
  },
  {
    label: '训练模型',
    value: formatNumber(results.value.predictionModelStatus?.data?.model_count),
    helper: 'in-memory models',
    tone: 'default'
  },
  {
    label: '可选能力',
    value: `${formatNumber(capabilitySummary.value.available)}/${formatNumber(capabilitySummary.value.total)}`,
    helper: capabilitySummary.value.provider_status || 'runtime probes',
    tone: capabilitySummary.value.degraded ? 'warn' : 'good'
  },
  {
    label: '运行态路由',
    value: `${formatNumber(runtimeRegisteredSummary.value.available)}/${formatNumber(runtimeRegisteredSummary.value.total)}`,
    helper: runtimeState.value.interpreter?.using_project_venv ? 'backend .venv' : 'check python',
    tone: runtimeState.value.provider_status === 'ok' ? 'good' : 'warn'
  },
  {
    label: 'GIS 底座',
    value: gisState.value.authenticity_level || '-',
    helper: gisState.value.provider_status || 'provider health',
    tone: gisState.value.provider_status === 'ok' ? 'good' : 'warn'
  },
  {
    label: '真实运费',
    value: formatNumber(operationsKpis.value.total_freight, 0),
    helper: `${formatNumber(operationsKpis.value.freight_per_kg, 2)} / kg`,
    tone: 'good'
  }
])

const deepPredictionRecommendations = computed(() => {
  const items = [
    ...(timeSeries.value.recommendations || []),
    ...(capacityGap.value.recommendations || []),
    ...(costVolatility.value.recommendations || []),
    timeSeriesReadiness.value.recommended_next_step
  ].filter(Boolean)
  return [...new Set(items)].slice(0, 6)
})

const dispatchLearningRows = computed(() => [
  {
    name: 'Learning Dataset',
    value: formatNumber(dispatchLearningSummary.value.sample_count || dispatchLearningSummary.value.row_count),
    status: dispatchLearningDataset.value.provider_status || (dispatchLearningSummary.value.sample_count ? 'ok' : 'shadow'),
    boundary: dispatchLearningDataset.value.target_definition?.hard_constraints_note || 'hard constraints kept in solver'
  },
  {
    name: 'Policy Scorer',
    value: bestPolicyName.value,
    status: policyScorer.value.provider_status || 'shadow',
    boundary: policyScorer.value.target_definition?.scoring_note || 'offline policy ranking only'
  },
  {
    name: 'Reward Model',
    value: formatNumber(rewardModel.value.metrics?.rank_accuracy?.accuracy, 2),
    status: rewardModel.value.provider_status || (rewardModel.value.metrics ? 'ok' : 'shadow'),
    boundary: rewardModel.value.model?.training_note || 'proxy reward, no business mutation'
  },
  {
    name: 'RL Shadow',
    value: formatNumber(rlShadow.value.summary?.episode_count),
    status: rlShadow.value.provider_status || 'shadow',
    boundary: rlShadow.value.fallback_reason || 'DQN-style shadow runner only'
  },
  {
    name: 'Fitted-Q',
    value: formatNumber(fittedQ.value.summary?.sample_count),
    status: fittedQ.value.provider_status || 'shadow',
    boundary: fittedQ.value.fallback_reason || 'candidate action value estimation'
  },
  {
    name: 'Snapshot',
    value: shadowSnapshot.value.snapshot?.content_hash?.slice(0, 12) || 'not_ready',
    status: shadowSnapshot.value.provider_status || 'audit',
    boundary: shadowSnapshot.value.snapshot?.mutation || 'none'
  }
])

const capabilityHighlights = computed(() => {
  const priority = ['gurobi', 'cplex_docplex', 'ortools', 'pymoo', 'torch', 'stable_baselines3', 'optuna', 'lightgbm', 'transformers', 'geospatial_stack']
  const rows = [...capabilityRows.value].sort((a, b) => {
    const left = priority.indexOf(a.id)
    const right = priority.indexOf(b.id)
    return (left === -1 ? 999 : left) - (right === -1 ? 999 : right)
  })
  return rows.slice(0, 10)
})

const dispatchLearningRecommendations = computed(() => {
  const items = [
    ...(policyScorer.value.recommendations || []),
    ...(rewardModel.value.recommendations || []),
    ...(fittedQ.value.recommendations || []),
    ...(results.value.dispatchShadowBenchmark?.data?.recommendations || [])
  ].filter(Boolean)
  return [...new Set(items)].slice(0, 6)
})

const recommendations = computed(() => {
  const items = [
    ...(results.value.predictionScorecard?.data?.recommendations || []),
    ...(results.value.anomalyScorecard?.data?.recommendations || []),
    ...(results.value.operationsScorecard?.data?.recommendations || []),
    ...(results.value.optimizationCapabilities?.data?.recommendations || []),
    ...(controlTower.value.components.some((component) => component.score < 70)
      ? ['优先处理低于 70 分的控制塔组件，避免只看单点绿色指标。']
      : []),
    ...(!controlTower.value.gates.every((gate) => gate.passed)
      ? ['存在未通过控制塔 gate，建议先补齐认证、后端服务或真实数据可见性。']
      : []),
    '控制塔分数是只读聚合，不写业务数据，也不替代调度求解器或财务结算。'
  ]
  return [...new Set(items)].slice(0, 8)
})

function componentScore(id) {
  const component = controlTower.value.components.find((item) => item.id === id)
  return formatNumber(component?.score, 1)
}

function utilizationWidth(row = {}) {
  const raw = Number(row.weight_utilization ?? row.volume_utilization ?? 0)
  if (!Number.isFinite(raw)) return '3%'
  return `${Math.max(3, Math.min(100, raw * 100))}%`
}

function initChart(domRef) {
  if (!domRef) return null
  const existing = echarts.getInstanceByDom(domRef)
  if (existing) existing.dispose()
  const chart = echarts.init(domRef)
  charts.push(chart)
  return chart
}

function renderVisualCharts() {
  charts.forEach((chart) => chart.dispose())
  charts = []
  renderReadinessRadar()
  renderForecastChart()
  renderAnomalyChart()
}

function renderReadinessRadar() {
  const chart = initChart(readinessRadarChart.value)
  if (!chart) return
  const components = controlTower.value.components
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', backgroundColor: 'rgba(5, 12, 24, 0.92)', borderColor: 'rgba(0,212,255,.35)', textStyle: { color: '#fff' } },
    radar: {
      radius: '66%',
      indicator: components.map((item) => ({ name: item.label, max: 100 })),
      splitNumber: 4,
      axisName: { color: 'rgba(218,235,255,.72)', fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(0,212,255,.2)' } },
      splitLine: { lineStyle: { color: 'rgba(0,212,255,.14)' } },
      splitArea: { areaStyle: { color: ['rgba(0,212,255,.03)', 'rgba(30,230,143,.035)'] } }
    },
    series: [
      {
        type: 'radar',
        data: [{ value: components.map((item) => Number(item.score || 0)), name: 'readiness' }],
        symbolSize: 5,
        lineStyle: { width: 3, color: '#00d4ff' },
        itemStyle: { color: '#1ee68f' },
        areaStyle: { color: 'rgba(0,212,255,.18)' }
      }
    ]
  })
}

function renderForecastChart() {
  const chart = initChart(forecastChart.value)
  if (!chart) return
  const rows = forecastRows.value
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(5, 12, 24, 0.92)', borderColor: 'rgba(30,230,143,.35)', textStyle: { color: '#fff' } },
    grid: { left: 40, right: 18, top: 26, bottom: 34 },
    xAxis: {
      type: 'category',
      data: rows.map((item) => String(item.date || '').slice(5)),
      axisLine: { lineStyle: { color: 'rgba(0,212,255,.25)' } },
      axisLabel: { color: 'rgba(218,235,255,.62)' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(0,212,255,.1)' } },
      axisLabel: { color: 'rgba(218,235,255,.62)' }
    },
    series: [
      {
        name: '预测订单',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: rows.map((item) => Number(item.predicted_orders ?? item.predicted_value ?? 0)),
        lineStyle: { color: '#1ee68f', width: 3 },
        itemStyle: { color: '#1ee68f' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(30,230,143,.28)' },
            { offset: 1, color: 'rgba(30,230,143,.02)' }
          ])
        }
      }
    ]
  })
}

function renderAnomalyChart() {
  const chart = initChart(anomalyChart.value)
  if (!chart) return
  const entries = Object.entries(anomalySummary.value.by_type || {}).slice(0, 8)
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', backgroundColor: 'rgba(5, 12, 24, 0.92)', borderColor: 'rgba(255,191,71,.35)', textStyle: { color: '#fff' } },
    series: [
      {
        type: 'pie',
        radius: ['46%', '72%'],
        center: ['50%', '52%'],
        avoidLabelOverlap: true,
        label: { color: 'rgba(218,235,255,.72)', formatter: '{b}\\n{c}' },
        labelLine: { lineStyle: { color: 'rgba(218,235,255,.24)' } },
        data: entries.length ? entries.map(([name, value]) => ({ name, value })) : [{ name: 'no_signal', value: 1 }],
        color: ['#00d4ff', '#1ee68f', '#ffbf47', '#ff6b8a', '#8b5cf6', '#38bdf8', '#f97316', '#22c55e']
      }
    ]
  })
}

function resizeCharts() {
  charts.forEach((chart) => chart.resize())
}

onMounted(() => {
  loadConsoleData()
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  charts.forEach((chart) => chart.dispose())
  charts = []
})
</script>

<style scoped>
.decision-console {
  display: flex;
  flex-direction: column;
  gap: 18px;
  color: var(--cc-text-primary);
}

.console-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 24px;
}

.console-hero h1 {
  margin: 8px 0;
  font-size: 30px;
  line-height: 1.2;
}

.console-hero p {
  max-width: 720px;
  margin: 0;
  color: var(--cc-text-secondary);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.demo-health-strip {
  padding: 18px;
}

.demo-health-head,
.demo-health-score {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.demo-health-head {
  margin-bottom: 14px;
}

.demo-health-head h2 {
  margin: 2px 0 0;
  font-size: 18px;
}

.demo-health-score strong {
  color: var(--cc-text-primary);
  font-size: 28px;
  line-height: 1;
}

.demo-health-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.demo-health-item {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px 8px;
  min-width: 0;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.055);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.035);
}

.demo-health-item span,
.demo-health-item small {
  min-width: 0;
  overflow: hidden;
  color: var(--cc-text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.demo-health-item strong {
  grid-column: 1 / -1;
  min-width: 0;
  overflow: hidden;
  color: var(--cc-text-primary);
  font-size: 17px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.demo-health-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.demo-health-actions span {
  max-width: 100%;
  padding: 6px 9px;
  overflow: hidden;
  color: var(--cc-text-secondary);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 1px solid rgba(255, 191, 71, 0.18);
  border-radius: 999px;
  background: rgba(255, 191, 71, 0.08);
}

.demo-health-actions span.danger {
  color: #ffd6df;
  border-color: rgba(255, 107, 138, 0.3);
  background: rgba(255, 107, 138, 0.12);
}

.agent-panel,
.agent-form,
.agent-output-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.agent-panel {
  color: #ecf7ff;
}

:global(.agent-drawer),
:global(.agent-drawer .el-drawer),
:global(.el-drawer.agent-drawer) {
  color: #ecf7ff;
  border-left: 1px solid rgba(0, 212, 255, 0.26);
  background:
    linear-gradient(180deg, rgba(9, 21, 38, 0.98), rgba(6, 14, 28, 0.98)),
    #07111f;
  box-shadow: -20px 0 60px rgba(0, 0, 0, 0.42);
}

:global(.agent-drawer .el-drawer__header) {
  padding: 20px 22px 12px;
  margin-bottom: 0;
  color: #ecf7ff;
  border-bottom: 1px solid rgba(0, 212, 255, 0.16);
}

:global(.agent-drawer .el-drawer__title) {
  color: #ecf7ff;
  font-size: 18px;
  font-weight: 700;
}

:global(.agent-drawer .el-drawer__close-btn) {
  color: rgba(236, 247, 255, 0.82);
}

:global(.agent-drawer .el-drawer__body) {
  padding: 18px 20px 24px;
  color: #ecf7ff;
  background: transparent;
}

:global(.agent-drawer .el-alert) {
  border: 1px solid rgba(30, 230, 143, 0.22);
  background: rgba(30, 230, 143, 0.1);
}

:global(.agent-drawer .el-alert__title),
:global(.agent-drawer .el-alert__description) {
  color: #eef8ff;
}

.agent-form {
  margin-top: 16px;
}

.agent-form label {
  display: flex;
  flex-direction: column;
  gap: 7px;
  color: var(--cc-text-muted);
  font-size: 12px;
}

.agent-field {
  width: 100%;
}

.agent-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.agent-boundary {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 12px;
  color: rgba(236, 247, 255, 0.72);
  border: 1px solid rgba(0, 212, 255, 0.18);
  border-radius: 12px;
  background: rgba(0, 212, 255, 0.08);
}

.agent-boundary strong {
  color: #ffffff;
}

.agent-output {
  padding: 14px;
  border: 1px solid rgba(0, 212, 255, 0.18);
  border-radius: 12px;
  background: rgba(8, 22, 38, 0.9);
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.22);
}

.agent-output .panel-title-row h2 {
  color: #ffffff;
}

.agent-output .panel-eyebrow {
  color: #88e7ff;
}

.agent-answer-text {
  margin: 0;
  color: #f3f9ff;
  font-size: 14px;
  line-height: 1.78;
  white-space: pre-wrap;
  word-break: break-word;
}

.agent-output pre {
  max-height: 260px;
  margin: 0;
  padding: 12px;
  overflow: auto;
  color: #f1f8ff;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid rgba(136, 231, 255, 0.18);
  border-radius: 10px;
  background: rgba(2, 8, 18, 0.74);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 14px;
  min-height: 128px;
}

.metric-tile {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 112px;
  padding: 16px;
  border-radius: 14px;
}

.metric-tile span,
.metric-tile small {
  color: var(--cc-text-muted);
}

.metric-tile strong {
  margin: 10px 0;
  font-size: 26px;
  line-height: 1;
}

.metric-tile--good {
  border-color: rgba(30, 230, 143, 0.24);
}

.metric-tile--warn {
  border-color: rgba(255, 191, 71, 0.28);
}

.visual-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  min-height: 320px;
}

.visual-panel,
.ai-deep-panel,
.dispatch-learning-panel {
  position: relative;
  overflow: hidden;
}

.visual-panel {
  min-width: 0;
  padding: 18px;
  border-radius: 16px;
}

.visual-chart {
  width: 100%;
  min-height: 240px;
}

.ai-deep-panel::before,
.dispatch-learning-panel::before,
.visual-panel::before {
  position: absolute;
  inset: 0;
  pointer-events: none;
  content: '';
  background:
    linear-gradient(135deg, rgba(0, 212, 255, 0.08), transparent 34%),
    linear-gradient(315deg, rgba(30, 230, 143, 0.07), transparent 30%);
  opacity: 0.72;
}

.visual-panel > *,
.ai-deep-panel > *,
.dispatch-learning-panel > * {
  position: relative;
  z-index: 1;
}

.forecast-ribbon {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 16px;
}

.forecast-ribbon article {
  min-width: 0;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.055);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.035);
}

.forecast-ribbon span,
.forecast-ribbon small {
  display: block;
  overflow: hidden;
  color: var(--cc-text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.forecast-ribbon strong {
  display: block;
  margin: 5px 0;
  overflow: hidden;
  color: var(--cc-text-primary);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mini-bar {
  height: 6px;
  margin: 7px 0;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
}

.mini-bar i {
  display: block;
  width: 0;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--cc-cyan), var(--cc-success));
}

.mini-bar i.warn {
  background: linear-gradient(90deg, var(--cc-amber), #ff6b8a);
}

.console-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(360px, 0.9fr);
  gap: 16px;
}

.console-panel {
  min-width: 0;
  padding: 18px;
  border-radius: 16px;
}

.control-tower {
  grid-row: span 2;
}

.panel-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 16px;
}

.panel-title-row h2 {
  margin: 2px 0 0;
  font-size: 18px;
}

.panel-eyebrow {
  color: var(--cc-text-muted);
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.result-pill {
  display: inline-flex;
  align-items: center;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 11px;
  color: var(--cc-text-primary);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 191, 71, 0.14);
}

.result-pill--ok {
  background: rgba(30, 230, 143, 0.12);
  border-color: rgba(30, 230, 143, 0.22);
}

.score-strip,
.dispatch-grid,
.anomaly-kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.anomaly-kpis {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.score-strip > div,
.dispatch-grid > div,
.anomaly-kpis > div {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.055);
}

.score-strip span,
.dispatch-grid span,
.anomaly-kpis span {
  color: var(--cc-text-muted);
  font-size: 12px;
}

.score-strip strong,
.dispatch-grid strong,
.anomaly-kpis strong {
  overflow: hidden;
  color: var(--cc-text-primary);
  font-size: 18px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.component-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.table-head,
.table-row {
  display: grid;
  grid-template-columns: 1.1fr 0.45fr 0.55fr 1.5fr;
  gap: 10px;
  align-items: center;
  min-width: 0;
}

.compact .table-head,
.compact .table-row {
  grid-template-columns: 1fr 0.8fr 0.7fr 0.7fr;
}

.table-head {
  color: var(--cc-text-muted);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.table-row {
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.035);
}

.table-row > span,
.table-row > strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gate-list,
.signal-list,
.data-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.gate-item,
.signal-row,
.data-row {
  display: flex;
  gap: 12px;
  min-width: 0;
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.045);
}

.signal-row {
  align-items: center;
  justify-content: space-between;
}

.gate-item > span {
  flex: 0 0 auto;
  width: 9px;
  height: 9px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--cc-amber);
  box-shadow: 0 0 0 5px rgba(255, 191, 71, 0.12);
}

.gate-item > span.passed {
  background: var(--cc-success);
  box-shadow: 0 0 0 5px rgba(30, 230, 143, 0.12);
}

.signal-row > div,
.gate-item > div,
.data-row {
  min-width: 0;
}

.signal-row span,
.data-row span {
  color: var(--cc-text-muted);
  font-size: 12px;
}

.signal-row strong,
.data-row strong,
.gate-item strong {
  display: block;
  margin: 3px 0;
  color: var(--cc-text-primary);
}

.signal-row p,
.data-row p,
.gate-item p,
.panel-note {
  margin: 0;
  color: var(--cc-text-secondary);
  font-size: 12px;
}

.truth-line,
.provider-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  color: var(--cc-text-muted);
  font-size: 12px;
}

.truth-line span,
.provider-line span,
.provider-line strong {
  display: inline-flex;
  min-width: 0;
  padding: 5px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
}

.empty-note {
  margin: 0;
  padding: 12px;
  color: var(--cc-text-muted);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.035);
}

.panel-note {
  padding: 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.035);
}

@media (max-width: 1480px) {
  .metric-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .demo-health-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .visual-grid {
    grid-template-columns: 1fr;
  }

  .console-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .console-hero {
    align-items: stretch;
    flex-direction: column;
  }

  .hero-actions {
    justify-content: flex-start;
  }

  .metric-grid,
  .demo-health-grid,
  .visual-grid,
  .forecast-ribbon,
  .score-strip,
  .dispatch-grid,
  .anomaly-kpis {
    grid-template-columns: 1fr;
  }

  .table-head {
    display: none;
  }

  .table-row,
  .compact .table-row {
    grid-template-columns: 1fr;
  }
}
</style>
