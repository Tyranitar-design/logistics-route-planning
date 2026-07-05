<template>
  <div class="case-page">
    <header class="page-hero">
      <h1>🏆 场景横向对比</h1>
      <p>多方案持久化对比 · 成本/碳排/时效/鲜度/服务 · 推荐可行中最优</p>
      <el-button size="small" :loading="loading" @click="load" style="margin-top:10px">刷新对比</el-button>
    </header>
    <div class="kpi-grid">
      <div class="kpi-card"><span>对比场景</span><strong>{{ rows.length }}</strong></div>
      <div class="kpi-card"><span>推荐场景</span><strong style="font-size:13px">{{ compare?.recommended_scenario || '-' }}</strong></div>
      <div class="kpi-card"><span>推荐原因</span><strong style="font-size:11px">{{ compare?.recommendation_reason || '-' }}</strong></div>
    </div>
    <section class="panel">
      <h2>对比明细</h2>
      <el-table :data="rows" height="360">
        <el-table-column prop="name" label="场景" min-width="160" />
        <el-table-column prop="cost" label="成本(元)" width="100" />
        <el-table-column prop="carbon_kg" label="碳排(kg)" width="100" />
        <el-table-column prop="duration_min" label="时效(min)" width="100" />
        <el-table-column prop="freshness_score" label="鲜度" width="80" />
        <el-table-column prop="service_level" label="服务" width="80" />
        <el-table-column label="可行" width="80"><template #default="{ row }"><el-tag :type="row.feasible ? 'success' : 'info'" size="small">{{ row.feasible ? '是' : '否' }}</el-tag></template></el-table-column>
        <el-table-column label="推荐" width="90"><template #default="{ row }"><el-tag v-if="row.scenario_code === compare?.recommended_scenario" type="success" size="small">★ 推荐</el-tag></template></el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { compareFoodSupplyScenarios } from '@/api/foodSupplyCase'

const compare = ref(null)
const loading = ref(false)
const rows = computed(() => compare.value?.comparison || [])

async function load() {
  loading.value = true
  try { compare.value = await compareFoodSupplyScenarios({}) }
  catch (e) { ElMessage.error('场景对比失败：' + (e.message || '后端未启动')) }
  finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.case-page { color: #e6f0ff; }
.page-hero { margin-bottom: 18px; }
.page-hero h1 { margin: 0 0 4px; font-size: 22px; color: #a8d8ff; }
.page-hero p { margin: 0; color: #7a8fb0; font-size: 13px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin-bottom: 18px; }
.kpi-card { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 12px; display: flex; flex-direction: column; gap: 4px; }
.kpi-card span { font-size: 11px; color: #7a8fb0; }
.kpi-card strong { font-size: 16px; color: #5eead4; }
.panel { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.panel h2 { margin: 0 0 12px; font-size: 15px; color: #a8d8ff; }
</style>
