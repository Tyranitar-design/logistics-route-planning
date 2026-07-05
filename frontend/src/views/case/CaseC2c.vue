<template>
  <div class="case-page">
    <header class="page-hero">
      <h1>🚁 C 端地理 & 无人机最后一公里</h1>
      <p>22259 C 端地址聚合到区域中心 · 真实 geocoding（A 级）· 无人机 vs 车辆 vs 混合</p>
      <div class="hero-actions">
        <el-button size="small" :loading="loadingClusters" @click="loadClusters">刷新聚类</el-button>
        <el-button size="small" :loading="loadingLastMile" @click="loadLastMile">刷新最后一公里</el-button>
      </div>
    </header>
    <div class="kpi-grid">
      <div class="kpi-card"><span>原始 C 端行</span><strong>{{ clusters?.summary?.raw_row_count || 0 }}</strong></div>
      <div class="kpi-card"><span>聚类数</span><strong>{{ clusters?.summary?.cluster_count || 0 }}</strong></div>
      <div class="kpi-card"><span>A 级(真实)</span><strong>{{ aCount }}</strong></div>
      <div class="kpi-card"><span>C 级(兜底)</span><strong>{{ cCount }}</strong></div>
      <div class="kpi-card"><span>无人机可行</span><strong>{{ lastMile?.summary?.drone_feasible_clusters || 0 }}</strong></div>
    </div>
    <section class="panel">
      <h2>C 端区域聚类（真实性: {{ clusters?.authenticity_level || '-' }}）</h2>
      <el-table :data="clusters?.clusters || []" height="300">
        <el-table-column prop="region" label="区域" min-width="120" />
        <el-table-column prop="orders" label="订单" width="80" />
        <el-table-column prop="weight_kg" label="重量(kg)" width="100" />
        <el-table-column label="坐标" min-width="170"><template #default="{ row }"><span v-if="row.lon">{{ row.lon.toFixed(3) }}, {{ row.lat.toFixed(3) }}</span><span v-else style="color:#5a7090">待编码</span></template></el-table-column>
        <el-table-column prop="centroid_source" label="来源" min-width="180" show-overflow-tooltip />
        <el-table-column prop="cluster_authenticity_level" label="真实性" width="80"><template #default="{ row }"><el-tag :type="row.cluster_authenticity_level === 'A' ? 'success' : 'warning'" size="small">{{ row.cluster_authenticity_level }}</el-tag></template></el-table-column>
      </el-table>
    </section>
    <section class="panel">
      <h2>无人机最后一公里对比</h2>
      <el-table :data="lastMile?.clusters || []" height="340">
        <el-table-column prop="cluster" label="区域" min-width="100" />
        <el-table-column prop="weight_kg" label="重量(kg)" width="90" />
        <el-table-column prop="distance_km" label="距离(km)" width="90" />
        <el-table-column prop="distance_source" label="距离源" min-width="140" show-overflow-tooltip />
        <el-table-column label="无人机" min-width="180"><template #default="{ row }">{{ fmt(row, 'drone') }}</template></el-table-column>
        <el-table-column label="车辆" min-width="180"><template #default="{ row }">{{ fmt(row, 'vehicle') }}</template></el-table-column>
        <el-table-column label="混合" min-width="180"><template #default="{ row }">{{ fmt(row, 'hybrid') }}</template></el-table-column>
        <el-table-column prop="recommended_mode" label="推荐" width="90" />
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getFoodSupplyC2cClusters, optimizeFoodSupplyLastMile } from '@/api/foodSupplyCase'

const clusters = ref(null)
const lastMile = ref(null)
const loadingClusters = ref(false)
const loadingLastMile = ref(false)
const aCount = computed(() => (clusters.value?.clusters || []).filter(c => c.cluster_authenticity_level === 'A').length)
const cCount = computed(() => (clusters.value?.clusters || []).filter(c => c.cluster_authenticity_level !== 'A').length)

function fmt(row, mode) {
  const m = (row.modes || []).find(x => x.mode === mode)
  if (!m) return '-'
  const tag = m.feasible ? '' : ' (不可行)'
  return `${m.cost} 元 / ${m.duration_min} min${tag}`
}

async function loadClusters() {
  loadingClusters.value = true
  try { clusters.value = await getFoodSupplyC2cClusters({ cluster_limit: 40 }) }
  catch (e) { ElMessage.error('聚类加载失败：' + (e.message || '后端未启动')) }
  finally { loadingClusters.value = false }
}
async function loadLastMile() {
  loadingLastMile.value = true
  try { lastMile.value = await optimizeFoodSupplyLastMile({ cluster_limit: 10, distance_mode: 'amap', persist: false }) }
  catch (e) { ElMessage.error('最后一公里加载失败：' + (e.message || '后端未启动')) }
  finally { loadingLastMile.value = false }
}
onMounted(() => { loadClusters(); loadLastMile() })
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
</style>
