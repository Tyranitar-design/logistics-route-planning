<template>
  <div class="solver-recommendation-card">
    <div class="card-header">
      <div class="title-wrap">
        <span class="emoji">🤖</span>
        <div>
          <h3>求解器推荐</h3>
          <p class="subtitle">系统基于问题规模、目标类型与实时性需求给出的建议</p>
        </div>
      </div>
      <el-tag type="success" effect="dark" size="large">
        推荐：{{ formatSolverName(recommendation?.recommended_solver) }}
      </el-tag>
    </div>

    <div v-if="recommendation" class="card-body">
      <el-row :gutter="12" class="summary-grid">
        <el-col :xs="24" :sm="12" :md="6">
          <div class="summary-item">
            <span class="label">问题类型</span>
            <span class="value">{{ recommendation.problem_summary?.problem_type || '-' }}</span>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="summary-item">
            <span class="label">客户规模</span>
            <span class="value">{{ recommendation.problem_summary?.n_customers ?? '-' }}</span>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="summary-item">
            <span class="label">规模等级</span>
            <span class="value">{{ recommendation.problem_summary?.scale || '-' }}</span>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="summary-item">
            <span class="label">模式偏好</span>
            <span class="value">{{ modeSummary }}</span>
          </div>
        </el-col>
      </el-row>

      <div class="section">
        <div class="section-title">✅ 推荐理由</div>
        <el-timeline>
          <el-timeline-item
            v-for="(item, index) in recommendation.reasoning || []"
            :key="index"
            type="primary"
            :hollow="index !== (recommendation.reasoning || []).length - 1"
          >
            {{ item }}
          </el-timeline-item>
        </el-timeline>
      </div>

      <div class="section" v-if="recommendation.alternatives?.length">
        <div class="section-title">🪄 备选求解器</div>
        <div class="alternatives">
          <el-tag
            v-for="solver in recommendation.alternatives"
            :key="solver"
            type="info"
            effect="plain"
            class="alt-tag"
          >
            {{ formatSolverName(solver) }}
          </el-tag>
        </div>
      </div>
    </div>

    <el-empty v-else description="暂无推荐结果" :image-size="80" />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  recommendation: {
    type: Object,
    default: null
  }
})

const solverNameMap = {
  ortools: 'OR-Tools',
  gurobi: 'Gurobi',
  gurobi_vrptw: 'Gurobi VRPTW',
  pyvrp: 'PyVRP',
  pymoo_nsga2: 'pymoo NSGA-II',
  pymoo_nsga3: 'pymoo NSGA-III',
  genetic: 'Genetic',
  alns: 'ALNS',
  column_generation: 'Column Generation',
  lagrangian: 'Lagrangian',
  drl_vrp: 'DRL VRP'
}

function formatSolverName(name) {
  if (!name) return '-'
  return solverNameMap[name] || name
}

const modeSummary = computed(() => {
  const summary = props.recommendation?.problem_summary
  if (!summary) return '-'

  const flags = []
  if (summary.require_high_accuracy) flags.push('高精度')
  if (summary.prefer_fast_response) flags.push('快速响应')
  if (summary.realtime) flags.push('实时')

  return flags.length ? flags.join(' / ') : '标准'
})
</script>

<style scoped>
.solver-recommendation-card {
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

.summary-grid {
  margin-bottom: 8px;
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
  font-size: 14px;
  font-weight: 600;
  color: #303133;
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

.alternatives {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.alt-tag {
  margin-right: 0;
}
</style>
