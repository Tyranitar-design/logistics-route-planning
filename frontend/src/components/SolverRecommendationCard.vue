<template>
  <div class="solver-recommendation-card">
    <div class="card-header">
      <div class="title-wrap">
        <span class="emoji">🤖</span>
        <div>
          <h3>求解器推荐</h3>
          <p class="subtitle">用企业级摘要方式说明当前问题为什么适合这个 solver，而不是只给一个名字。</p>
        </div>
      </div>
      <el-tag v-if="recommendation" type="success" effect="dark" size="large">
        推荐：{{ formatSolverName(recommendation?.recommended_solver || recommendation?.recommended) }}
      </el-tag>
    </div>

    <div v-if="recommendation" class="card-body">
      <div class="hero-summary">
        <div class="hero-summary__main">
          <span class="hero-label">当前推荐结论</span>
          <h4>{{ formatSolverName(recommendation?.recommended_solver || recommendation?.recommended) }}</h4>
          <p>{{ recommendation.reason || recommendation.description || '系统已基于当前问题规模、目标复杂度与响应要求生成推荐。' }}</p>
        </div>
        <div class="hero-scoreboard">
          <div class="score-item">
            <span class="label">问题类型</span>
            <strong>{{ recommendation.problem_summary?.problem_type || '未标注' }}</strong>
          </div>
          <div class="score-item">
            <span class="label">客户规模</span>
            <strong>{{ recommendation.problem_summary?.n_customers ?? '-' }}</strong>
          </div>
          <div class="score-item">
            <span class="label">规模等级</span>
            <strong>{{ recommendation.problem_summary?.scale || '-' }}</strong>
          </div>
          <div class="score-item">
            <span class="label">模式偏好</span>
            <strong>{{ modeSummary }}</strong>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">🧭 决策画像</div>
        <div class="profile-grid">
          <div class="profile-item">
            <span class="label">是否追求高精度</span>
            <strong>{{ recommendation.problem_summary?.require_high_accuracy ? '是' : '否' }}</strong>
          </div>
          <div class="profile-item">
            <span class="label">是否偏好快速响应</span>
            <strong>{{ recommendation.problem_summary?.prefer_fast_response ? '是' : '否' }}</strong>
          </div>
          <div class="profile-item">
            <span class="label">是否实时场景</span>
            <strong>{{ recommendation.problem_summary?.realtime ? '是' : '否' }}</strong>
          </div>
          <div class="profile-item">
            <span class="label">核心判断</span>
            <strong>{{ modeSummary }}</strong>
          </div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">✅ 推荐理由</div>
        <div class="reason-timeline">
          <div
            v-for="(item, index) in recommendation.reasoning || []"
            :key="index"
            class="reason-item"
          >
            <span class="reason-index">{{ index + 1 }}</span>
            <span class="reason-text">{{ item }}</span>
          </div>
        </div>
      </div>

      <div class="section" v-if="recommendation.alternatives?.length">
        <div class="section-title">🪄 备选求解器</div>
        <div class="alternatives">
          <div
            v-for="solver in recommendation.alternatives"
            :key="solver"
            class="alt-card"
          >
            <span class="alt-label">备选</span>
            <strong>{{ formatSolverName(solver) }}</strong>
          </div>
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
  if (!summary) return '标准'

  const flags = []
  if (summary.require_high_accuracy) flags.push('高精度')
  if (summary.prefer_fast_response) flags.push('快速响应')
  if (summary.realtime) flags.push('实时')

  return flags.length ? flags.join(' / ') : '标准'
})
</script>

<style scoped>
.solver-recommendation-card {
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

.hero-summary {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 16px;
  margin-bottom: 18px;
}

.hero-summary__main {
  padding: 18px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.12), rgba(17, 224, 183, 0.08));
  border: 1px solid rgba(0, 212, 255, 0.18);
}

.hero-label {
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(236, 247, 255, 0.55);
}

.hero-summary__main h4 {
  margin: 10px 0 8px;
  font-size: 28px;
  color: #ffffff;
}

.hero-summary__main p {
  margin: 0;
  line-height: 1.8;
  color: rgba(236, 247, 255, 0.75);
}

.hero-scoreboard {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.score-item,
.profile-item {
  padding: 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.score-item .label,
.profile-item .label {
  font-size: 12px;
  color: rgba(236, 247, 255, 0.52);
}

.score-item strong,
.profile-item strong {
  color: #ecf7ff;
  font-size: 15px;
  font-weight: 700;
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

.profile-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.reason-timeline {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.reason-item {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(0, 212, 255, 0.08);
}

.reason-index {
  width: 28px;
  height: 28px;
  display: inline-grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(0, 212, 255, 0.16);
  color: #8be9ff;
  font-size: 12px;
  font-weight: 700;
}

.reason-text {
  line-height: 1.75;
  color: rgba(236, 247, 255, 0.78);
}

.alternatives {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.alt-card {
  padding: 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alt-label {
  font-size: 11px;
  color: rgba(236, 247, 255, 0.48);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.alt-card strong {
  color: #ecf7ff;
}

@media (max-width: 1200px) {
  .hero-summary {
    grid-template-columns: 1fr;
  }

  .profile-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .hero-scoreboard,
  .profile-grid,
  .alternatives {
    grid-template-columns: 1fr;
  }

  .hero-summary__main h4 {
    font-size: 22px;
  }
}
</style>
