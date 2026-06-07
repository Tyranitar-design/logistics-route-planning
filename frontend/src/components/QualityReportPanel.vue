<template>
  <div class="quality-report-panel">
    <div class="card-header">
      <div class="title-wrap">
        <span class="emoji">🩺</span>
        <div>
          <h3>质量报告</h3>
          <p class="subtitle">从真实性、可行性、目标质量和 Pareto 规模四个层面解释当前解集质量，而不是只给“成功/失败”。</p>
        </div>
      </div>
      <el-tag
        v-if="report"
        :type="report?.feasible ? 'success' : 'danger'"
        effect="dark"
        size="large"
      >
        {{ report?.feasible ? '质量通过' : '存在问题' }}
      </el-tag>
    </div>

    <div v-if="report" class="panel-body">
      <div class="hero-grid">
        <div class="hero-item hero-item--primary">
          <span class="hero-label">可行性状态</span>
          <strong>{{ report.feasible ? '当前解满足基础可行性检查' : '当前解存在可行性问题' }}</strong>
          <p>{{ feasibilitySummary }}</p>
        </div>
        <div class="hero-item">
          <span class="hero-label">主目标值</span>
          <strong>{{ formatNumber(report.objective_summary?.primary_objective) }}</strong>
        </div>
        <div class="hero-item">
          <span class="hero-label">Gap</span>
          <strong>{{ formatGap(report.objective_summary?.gap) }}</strong>
        </div>
        <div class="hero-item">
          <span class="hero-label">Pareto 规模</span>
          <strong>{{ report.pareto_summary?.pareto_front_size ?? report.pareto_summary?.metrics?.pareto_count ?? '-' }}</strong>
        </div>
      </div>

      <div class="section">
        <div class="section-title">✅ 可行性与告警</div>
        <el-alert
          v-if="report.feasible"
          title="当前解满足基础可行性检查"
          type="success"
          :closable="false"
          show-icon
        />
        <el-alert
          v-else
          title="当前解存在可行性问题"
          type="error"
          :closable="false"
          show-icon
        >
          <template #default>
            <ul class="violation-list">
              <li v-for="(item, index) in report.violations || []" :key="index">
                {{ item }}
              </li>
            </ul>
          </template>
        </el-alert>
      </div>

      <div class="section">
        <div class="section-title">🛰️ 距离真实性与精度</div>
        <div class="metrics-grid">
          <div class="metric-card">
            <span class="label">距离来源</span>
            <strong>{{ report.distance_precision_summary?.distance_source || '-' }}</strong>
          </div>
          <div class="metric-card">
            <span class="label">精确数量</span>
            <strong class="success">{{ report.distance_precision_summary?.exact_count ?? 0 }}</strong>
          </div>
          <div class="metric-card">
            <span class="label">近似数量</span>
            <strong class="warning">{{ report.distance_precision_summary?.approx_count ?? 0 }}</strong>
          </div>
          <div class="metric-card">
            <span class="label">精确比例</span>
            <strong>{{ formatPercent(report.distance_precision_summary?.exact_ratio) }}</strong>
          </div>
          <div class="metric-card">
            <span class="label">近似比例</span>
            <strong>{{ formatPercent(report.distance_precision_summary?.approx_ratio) }}</strong>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">🎯 目标摘要</div>
        <div class="metrics-grid">
          <div class="metric-card">
            <span class="label">主目标值</span>
            <strong>{{ formatNumber(report.objective_summary?.primary_objective) }}</strong>
          </div>
          <div class="metric-card">
            <span class="label">目标个数</span>
            <strong>{{ report.objective_summary?.n_objectives ?? '-' }}</strong>
          </div>
          <div class="metric-card metric-card--wide">
            <span class="label">目标向量</span>
            <strong>{{ formatObjectives(report.objective_summary?.objective_values) }}</strong>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">🤖 求解器摘要</div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="求解器">
            {{ report.solver_summary?.solver_name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="问题类型">
            {{ report.solver_summary?.problem_type || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="求解时间">
            {{ formatSeconds(report.solver_summary?.solve_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="迭代次数">
            {{ report.solver_summary?.iterations ?? '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="最优性证明">
            <el-tag :type="report.solver_summary?.is_optimal ? 'success' : 'info'" size="small">
              {{ report.solver_summary?.is_optimal ? '已证明最优' : '未证明 / 启发式' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="质量解读">
            {{ feasibilitySummary }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="section" v-if="report.pareto_summary?.enabled">
        <div class="section-title">📈 Pareto 摘要</div>
        <div class="metrics-grid">
          <div class="metric-card">
            <span class="label">前沿规模</span>
            <strong>{{ report.pareto_summary?.pareto_front_size ?? '-' }}</strong>
          </div>
          <div class="metric-card">
            <span class="label">Pareto 点数</span>
            <strong>{{ report.pareto_summary?.metrics?.pareto_count ?? '-' }}</strong>
          </div>
          <div class="metric-card">
            <span class="label">Spread</span>
            <strong>{{ formatNumber(report.pareto_summary?.metrics?.spread) }}</strong>
          </div>
        </div>
      </div>
    </div>

    <el-empty v-else description="暂无质量报告" :image-size="80" />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  report: {
    type: Object,
    default: null
  }
})

const feasibilitySummary = computed(() => {
  if (!props.report) return '-'
  if (props.report.feasible) return '当前结果可进入业务解释与对比阶段'
  if (props.report.violations?.length) return `${props.report.violations.length} 项问题待处理`
  return '当前结果存在质量风险'
})

function formatNumber(value) {
  if (value == null || Number.isNaN(Number(value))) return '-'
  return Number(value).toFixed(2)
}

function formatGap(value) {
  if (value == null || value === undefined) return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function formatPercent(value) {
  if (value == null || value === undefined) return '-'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function formatSeconds(value) {
  if (value == null || value === undefined) return '-'
  return `${Number(value).toFixed(3)} s`
}

function formatObjectives(values) {
  if (!Array.isArray(values) || values.length === 0) return '-'
  return values.map(v => formatNumber(v)).join(' / ')
}
</script>

<style scoped>
.quality-report-panel {
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(8, 19, 34, 0.96) 0%, rgba(10, 22, 38, 0.9) 100%);
  padding: 20px;
  color: #ecf7ff;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.22);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
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
  font-size: 20px;
  color: #ecf7ff;
}

.subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: rgba(236, 247, 255, 0.62);
}

.hero-grid {
  display: grid;
  grid-template-columns: 1.2fr repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.hero-item,
.metric-card {
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hero-item--primary {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.12), rgba(17, 224, 183, 0.08));
  border-color: rgba(0, 212, 255, 0.18);
}

.hero-label,
.label {
  font-size: 12px;
  color: rgba(236, 247, 255, 0.52);
}

.hero-item strong,
.metric-card strong {
  color: #ecf7ff;
  font-size: 16px;
  font-weight: 700;
}

.hero-item p {
  margin: 0;
  line-height: 1.75;
  color: rgba(236, 247, 255, 0.74);
}

.section {
  margin-top: 18px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #ecf7ff;
  margin-bottom: 12px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.metric-card--wide {
  grid-column: span 2;
}

.success {
  color: #1ee68f !important;
}

.warning {
  color: #ffbf47 !important;
}

.violation-list {
  margin: 8px 0 0 18px;
  padding: 0;
}

.violation-list li {
  margin-bottom: 4px;
}

@media (max-width: 1200px) {
  .hero-grid,
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-card--wide {
    grid-column: span 2;
  }
}

@media (max-width: 768px) {
  .hero-grid,
  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .metric-card--wide {
    grid-column: span 1;
  }
}
</style>
