<template>
  <div class="case-page">
    <header class="page-hero">
      <h1>📊 案例总览</h1>
      <p>桃类生鲜仓配一体化 · 数据审计 + 真实性契约</p>
    </header>
    <div class="kpi-grid">
      <div class="kpi-card" v-for="k in kpis" :key="k.label">
        <span>{{ k.label }}</span><strong>{{ k.value }}</strong><small>{{ k.hint }}</small>
      </div>
    </div>
    <section class="panel">
      <div class="panel-title"><h2>数据审计</h2><el-tag :type="summary?.provider_status === 'ok' ? 'success' : 'warning'" size="small">{{ summary?.provider_status || 'loading' }}</el-tag></div>
      <el-table :data="sourceFiles" height="320">
        <el-table-column prop="name" label="源文件" min-width="280" />
        <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.exists ? 'success' : 'danger'" size="small">{{ row.exists ? '存在' : '缺失' }}</el-tag></template></el-table-column>
        <el-table-column prop="size_bytes" label="大小(B)" width="120" />
      </el-table>
    </section>
    <section class="panel truth-panel">
      <h2>真实性契约</h2>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="真实性等级">{{ summary?.authenticity_level || '-' }}</el-descriptions-item>
        <el-descriptions-item label="数据源">{{ summary?.data_source || '-' }}</el-descriptions-item>
        <el-descriptions-item label="距离源">{{ summary?.distance_source || '-' }}</el-descriptions-item>
        <el-descriptions-item label="降级原因">{{ summary?.fallback_reason || '无' }}</el-descriptions-item>
      </el-descriptions>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getFoodSupplySummary } from '@/api/foodSupplyCase'

const summary = ref(null)
const summaryData = computed(() => summary.value?.summary || {})
const sourceFiles = computed(() => summary.value?.source_files || [])
const kpis = computed(() => [
  { label: '果园', value: summaryData.value.orchard_count || 0, hint: 'A-E' },
  { label: '仓/中转', value: summaryData.value.facility_count || 0, hint: '仓库+中转场' },
  { label: 'B端门店', value: summaryData.value.b_store_count || 0, hint: '经销门店' },
  { label: 'B端需求', value: summaryData.value.b2b_demand_rows || 0, hint: '行' },
  { label: 'C端需求', value: summaryData.value.c2c_demand_rows || 0, hint: '行' },
  { label: '车辆', value: summaryData.value.vehicle_type_count || 0, hint: '4.2-13.5米' },
  { label: '无人机', value: summaryData.value.drone_type_count || 0, hint: '载重10kg' },
  { label: '真实性', value: summary.value?.authenticity_level || '-', hint: summary.value?.distance_source || '' },
])

async function load() {
  try {
    summary.value = await getFoodSupplySummary()
  } catch (e) { ElMessage.error('总览加载失败：' + (e.message || '后端未启动')) }
}
onMounted(load)
</script>

<style scoped>
.case-page { color: #e6f0ff; }
.page-hero { margin-bottom: 18px; }
.page-hero h1 { margin: 0 0 4px; font-size: 22px; color: #a8d8ff; }
.page-hero p { margin: 0; color: #7a8fb0; font-size: 13px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; margin-bottom: 18px; }
.kpi-card { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 4px; }
.kpi-card span { font-size: 11px; color: #7a8fb0; }
.kpi-card strong { font-size: 22px; color: #5eead4; }
.kpi-card small { font-size: 10px; color: #5a7090; }
.panel { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.panel-title { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.panel h2 { margin: 0; font-size: 15px; color: #a8d8ff; }
</style>
