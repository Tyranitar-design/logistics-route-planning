<template>
  <div class="quality-report-panel">
    <div class="card-header">
      <div class="title-wrap">
        <span class="emoji">🩺</span>
        <div>
          <h3>质量报告</h3>
          <p class="subtitle">统一展示可行性、目标摘要、求解质量与 Pareto 信息</p>
        </div>
      </div>
      <el-tag :type="report?.feasible ? 'success' : 'danger'" effect="dark" size="large">
        {{ report?.feasible ? '可行' : '存在问题' }}
      </el-tag>
    </div>

    <div v-if="report" class="panel-body">
      <div class="section">
        <div class="section-title">✅ 可行性状态</div>
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
        <div class="section-title">🎯 目标摘要</div>
        <el-row :gutter="12">
          <el-col :xs="24" :sm="12" :md="6">
            <div class="summary-item">
              <span class="label">主目标值</span>
              <span class="value">{{ formatNumber(report.objective_summary?.primary_objective) }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <div class="summary-item">
              <span class="label">目标个数</span>
              <span class="value">{{ report.objective_summary?.n_objectives ?? '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <div class="summary-item">
              <span class="label">Gap</span>
              <span class="value">{{ formatGap(report.objective_summary?.gap) }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <div class="summary-item">
              <span class="label">目标向量</span>
              <span class="value small">{{ formatObjectives(report.objective_summary?.objective_values) }}</span>
            </div>
          </el-col>
        </el-row>
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
          <el-descriptions-item label="是否最优">
            <el-tag :type="report.solver_summary?.is_optimal ? 'success' : 'info'" size="small">
              {{ report.solver_summary?.is_optimal ? '是' : '否 / 未证明' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="距离来源">
            {{ report.distance_precision_summary?.distance_source || '-' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="section">
        <div class="section-title">🛰️ 距离精度摘要</div>
        <el-row :gutter="12">
          <el-col :xs="24" :sm="12" :md="6">
            <div class="summary-item">
              <span class="label">精确数量</span>
              <span class="value success">{{ report.distance_precision_summary?.exact_count ?? 0 }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <div class="summary-item">
              <span class="label">近似数量</span>
              <span class="value warning">{{ report.distance_precision_summary?.approx_count ?? 0 }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <div class="summary-item">
              <span class="label">精确比例</span>
              <span class="value">{{ formatPercent(report.distance_precision_summary?.exact_ratio) }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <div class="summary-item">
              <span class="label">近似比例</span>
              <span class="value">{{ formatPercent(report.distance_precision_summary?.approx_ratio) }}</span>
            </div>
          </el-col>
        </el-row>
      </div>

      <div class="section" v-if="report.pareto_summary?.enabled">
        <div class="section-title">📈 Pareto 摘要</div>
        <el-row :gutter="12">
          <el-col :xs="24" :sm="12" :md="8">
            <div class="summary-item">
              <span class="label">前沿规模</span>
              <span class="value">{{ report.pareto_summary?.pareto_front_size ?? '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="summary-item">
              <span class="label">Pareto 点数</span>
              <span class="value">{{ report.pareto_summary?.metrics?.pareto_count ?? '-' }}</span>
            </div>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <div class="summary-item">
              <span class="label">Spread</span>
              <span class="value">{{ formatNumber(report.pareto_summary?.metrics?.spread) }}</span>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>

    <el-empty v-else description="暂无质量报告" :image-size="80" />
  </div>
</template>

<script setup>
const props = defineProps({
  report: {
    type: Object,
    default: null
  }
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
  border: 1px solid #ebeef5;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
  padding: 18px;
  box-shadow: 0 6px 18px rgba(31, 35, 41, 0.06);
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
  font-size: 18px;
  color: #303133;
}

.subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: #909399;
}

.section {
  margin-top: 18px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.summary-item {
  background: #fff;
  border: 1px solid #edf2f7;
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label {
  font-size: 12px;
  color: #909399;
}

.value {
  font-size: 16px;
  font-weight: 700;
  color: #303133;
}

.value.small {
  font-size: 13px;
  line-height: 1.4;
}

.value.success {
  color: #67c23a;
}

.value.warning {
  color: #e6a23c;
}

.violation-list {
  margin: 8px 0 0 18px;
  padding: 0;
}

.violation-list li {
  margin-bottom: 4px;
}
</style>
