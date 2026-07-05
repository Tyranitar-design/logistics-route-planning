<template>
  <div class="case-page">
    <header class="page-hero">
      <h1>🔬 C 端聚类分析</h1>
      <p>22,259 C 端地址 → 区域聚合 + 四级 geocoding · 聚类算法与结果说明</p>
    </header>
    <div class="kpi-grid">
      <div class="kpi-card"><span>原始行</span><strong>{{ clusters?.summary?.raw_row_count || 0 }}</strong></div>
      <div class="kpi-card"><span>聚类数</span><strong>{{ clusters?.summary?.cluster_count || 0 }}</strong></div>
      <div class="kpi-card"><span>A级(真实)</span><strong>{{ aCount }}</strong></div>
      <div class="kpi-card"><span>C级(兜底)</span><strong>{{ cCount }}</strong></div>
      <div class="kpi-card"><span>A级占比</span><strong>{{ pctA }}%</strong></div>
      <div class="kpi-card"><span>缓存坐标</span><strong>{{ geoStatus?.cache_count || 0 }}</strong></div>
    </div>
    <section class="panel">
      <h2>📋 聚类算法说明</h2>
      <div class="algo-desc">
        <p><b>输入</b>：C 端消费者需求表 22,259 行（日期 / 对方地区 / 重量 / 箱数 / 收件地址）</p>
        <p><b>聚类维度</b>：按「对方地区」字段聚合（如"合肥"/"阜阳/亳州"），跨日期汇总订单数、总重量、总箱数、唯一地址数</p>
        <p><b>坐标解析（四级 geocoding 策略，逐级降级）</b>：</p>
        <ol>
          <li><b>首 token</b>：组合 region 取首段（"阜阳/亳州"→"阜阳"）调高德 geocode</li>
          <li><b>"市"后缀重试</b>：失败则加"市"（"通化"→"通化市"，高德对地级市识别更好）</li>
          <li><b>POI 搜索</b>：仍失败则高德 place/text 关键词搜索（救回"大兴安岭"等非常规地名）</li>
          <li><b>本地兜底</b>：公开城市坐标库（authenticity C 级，绝不造假）</li>
        </ol>
        <p><b>结果</b>：{{ clusters?.summary?.cluster_count || 0 }} 个区域聚类，<b>{{ aCount }} 个 A 级真实坐标（{{ pctA }}%）</b>，{{ cCount }} 个 C 级本地兜底。缓存写入 <code>case_food_geocoding_cache</code> 表，后续所有端点读缓存复用。</p>
      </div>
    </section>
    <section class="panel">
      <h2>真实性分布（A vs C）</h2>
      <div ref="pieRef" class="cluster-chart"></div>
    </section>
    <section class="panel">
      <h2>区域订单量 Top 12</h2>
      <div ref="barRef" class="cluster-chart"></div>
    </section>
    <section class="panel">
      <h2>聚类明细</h2>
      <el-table :data="clusters?.clusters || []" height="340">
        <el-table-column prop="region" label="区域" min-width="120" />
        <el-table-column prop="orders" label="订单" width="80" />
        <el-table-column prop="weight_kg" label="重量(kg)" width="100" />
        <el-table-column prop="address_count" label="地址数" width="90" />
        <el-table-column label="坐标" min-width="170"><template #default="{ row }"><span v-if="row.lon">{{ row.lon.toFixed(3) }}, {{ row.lat.toFixed(3) }}</span><span v-else style="color:#5a7090">待编码</span></template></el-table-column>
        <el-table-column prop="centroid_source" label="来源" min-width="170" show-overflow-tooltip />
        <el-table-column prop="cluster_authenticity_level" label="真实性" width="80"><template #default="{ row }"><el-tag :type="row.cluster_authenticity_level === 'A' ? 'success' : 'warning'" size="small">{{ row.cluster_authenticity_level }}</el-tag></template></el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getFoodSupplyC2cClusters, getFoodSupplyC2cGeocodeStatus } from '@/api/foodSupplyCase'

const clusters = ref(null)
const geoStatus = ref(null)
const pieRef = ref(null)
const barRef = ref(null)
const aCount = computed(() => (clusters.value?.clusters || []).filter(c => c.cluster_authenticity_level === 'A').length)
const cCount = computed(() => (clusters.value?.clusters || []).filter(c => c.cluster_authenticity_level !== 'A').length)
const pctA = computed(() => {
  const t = (clusters.value?.clusters || []).length
  return t ? Math.round(aCount.value / t * 100) : 0
})

function renderCharts() {
  const cls = clusters.value?.clusters || []
  if (pieRef.value) {
    echarts.init(pieRef.value).setOption({
      tooltip: { trigger: 'item' },
      legend: { bottom: 0, textStyle: { color: '#aac' } },
      series: [{ type: 'pie', radius: ['40%', '70%'], data: [
        { value: aCount.value, name: 'A 级（真实 geocoding）', itemStyle: { color: '#52c41a' } },
        { value: cCount.value, name: 'C 级（本地兜底）', itemStyle: { color: '#faad14' } },
      ], label: { color: '#d6e6ff' } }],
    })
  }
  if (barRef.value) {
    const top = [...cls].sort((a, b) => b.orders - a.orders).slice(0, 12)
    echarts.init(barRef.value).setOption({
      tooltip: {}, grid: { left: 90, right: 20, top: 10, bottom: 30 },
      xAxis: { type: 'value', axisLabel: { color: '#7a8fb0' } },
      yAxis: { type: 'category', data: top.map(c => c.region), axisLabel: { color: '#9bb3d4' } },
      series: [{ type: 'bar', data: top.map(c => c.orders), itemStyle: { color: '#5eead4', borderRadius: [0, 4, 4, 0] } }],
    })
  }
}

async function load() {
  try {
    const [cl, gs] = await Promise.all([getFoodSupplyC2cClusters({ cluster_limit: 60 }), getFoodSupplyC2cGeocodeStatus()])
    clusters.value = cl; geoStatus.value = gs
    await nextTick(); renderCharts()
  } catch (e) { ElMessage.error('聚类加载失败：' + (e.message || '后端未启动')) }
}
onMounted(load)
</script>

<style scoped>
.case-page { color: #e6f0ff; }
.page-hero { margin-bottom: 18px; }
.page-hero h1 { margin: 0 0 4px; font-size: 22px; color: #a8d8ff; }
.page-hero p { margin: 0; color: #7a8fb0; font-size: 13px; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 12px; margin-bottom: 18px; }
.kpi-card { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 12px; display: flex; flex-direction: column; gap: 4px; }
.kpi-card span { font-size: 11px; color: #7a8fb0; }
.kpi-card strong { font-size: 18px; color: #5eead4; }
.panel { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.panel h2 { margin: 0 0 12px; font-size: 15px; color: #a8d8ff; }
.algo-desc p { margin: 6px 0; color: #c8d8ec; font-size: 13px; line-height: 1.7; }
.algo-desc b { color: #5eead4; }
.algo-desc ol { margin: 6px 0 6px 20px; color: #c8d8ec; font-size: 13px; line-height: 1.8; }
.algo-desc code { background: rgba(94,234,212,0.1); color: #5eead4; padding: 1px 6px; border-radius: 3px; font-size: 12px; }
.cluster-chart { height: 300px; width: 100%; }
</style>
