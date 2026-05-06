<template>
  <div class="distance-precision-card">
    <div class="card-header">
      <div class="title-wrap">
        <span class="emoji">🛰️</span>
        <div>
          <h3>距离精度报告</h3>
          <p class="subtitle">展示真实道路距离、近似距离与缓存来源分布</p>
        </div>
      </div>
      <el-tag :type="exactRatio >= 0.8 ? 'success' : exactRatio >= 0.4 ? 'warning' : 'danger'" effect="dark">
        精确率 {{ (exactRatio * 100).toFixed(1) }}%
      </el-tag>
    </div>

    <div class="summary-grid">
      <div class="summary-item">
        <span class="label">精确距离</span>
        <span class="value success">{{ exactCount }}</span>
      </div>
      <div class="summary-item">
        <span class="label">近似距离</span>
        <span class="value warning">{{ approxCount }}</span>
      </div>
      <div class="summary-item">
        <span class="label">总计</span>
        <span class="value">{{ totalCount }}</span>
      </div>
      <div class="summary-item">
        <span class="label">路线策略</span>
        <span class="value">{{ strategyLabel }}</span>
      </div>
    </div>

    <div class="progress-section">
      <div class="progress-row">
        <span class="progress-label">真实道路距离</span>
        <el-progress :percentage="Number((exactRatio * 100).toFixed(1))" status="success" :stroke-width="12" />
      </div>
      <div class="progress-row">
        <span class="progress-label">近似/回退距离</span>
        <el-progress :percentage="Number((approxRatio * 100).toFixed(1))" color="#E6A23C" :stroke-width="12" />
      </div>
    </div>

    <div class="section">
      <div class="section-title">📦 来源拆分</div>
      <div class="source-tags">
        <el-tag type="success" effect="plain">cache_exact: {{ sourceSummary?.cache_exact ?? 0 }}</el-tag>
        <el-tag type="warning" effect="plain">cache_approx: {{ sourceSummary?.cache_approx ?? 0 }}</el-tag>
        <el-tag type="primary" effect="plain">amap: {{ sourceSummary?.amap ?? 0 }}</el-tag>
        <el-tag type="info" effect="plain">fallback: {{ fallbackCount }}</el-tag>
      </div>
    </div>

    <div class="section meta-section">
      <div class="section-title">⚙️ 本次构建配置</div>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="距离来源">
          {{ distanceMetadata?.distance_source || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="距离提供器">
          {{ distanceMetadata?.distance_provider || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="use_precise_distance">
          <el-tag :type="distanceMetadata?.use_precise_distance ? 'success' : 'info'" size="small">
            {{ distanceMetadata?.use_precise_distance ? 'true' : 'false' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="strategy">
          {{ distanceMetadata?.strategy ?? '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <div v-if="cacheStats" class="section meta-section">
      <div class="section-title">🧠 缓存统计</div>
      <el-row :gutter="12">
        <el-col :xs="12" :sm="6">
          <div class="mini-stat">
            <span class="label">cache hits</span>
            <span class="value">{{ cacheStats.cache_hits ?? 0 }}</span>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="mini-stat">
            <span class="label">amap calls</span>
            <span class="value">{{ cacheStats.amap_calls ?? 0 }}</span>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="mini-stat">
            <span class="label">fallbacks</span>
            <span class="value">{{ cacheStats.haversine_fallbacks ?? 0 }}</span>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="mini-stat">
            <span class="label">total pairs</span>
            <span class="value">{{ cacheStats.total_pairs ?? totalCount }}</span>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  distancePrecision: {
    type: Object,
    default: () => ({})
  },
  sourceSummary: {
    type: Object,
    default: () => ({})
  },
  distanceMetadata: {
    type: Object,
    default: () => ({})
  }
})

const exactCount = computed(() => props.distancePrecision?.exact_count ?? 0)
const approxCount = computed(() => props.distancePrecision?.approx_count ?? 0)
const totalCount = computed(() => props.distancePrecision?.total_count ?? 0)

const exactRatio = computed(() => {
  if (!totalCount.value) return 0
  return exactCount.value / totalCount.value
})

const approxRatio = computed(() => {
  if (!totalCount.value) return 0
  return approxCount.value / totalCount.value
})

const fallbackCount = computed(() => {
  return (props.sourceSummary?.haversine_corrected ?? 0) + (props.distancePrecision?.fallback_count ?? 0)
})

const cacheStats = computed(() => props.distanceMetadata?.cache_stats || null)

const strategyLabel = computed(() => {
  const strategy = props.distanceMetadata?.strategy
  if (strategy === 0) return '0（默认）'
  if (strategy == null) return '-'
  return String(strategy)
})
</script>

<style scoped>
.distance-precision-card {
  border: 1px solid #ebeef5;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-item,
.mini-stat {
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

.value.success {
  color: #67c23a;
}

.value.warning {
  color: #e6a23c;
}

.progress-section {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.progress-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.progress-label {
  font-size: 13px;
  color: #606266;
  font-weight: 600;
}

.section {
  margin-top: 20px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.source-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-section :deep(.el-descriptions__label) {
  width: 120px;
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 600px) {
  .summary-grid {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }
}
</style>
