<template>
  <section class="insight-summary cc-panel">
    <div class="insight-header">
      <div>
        <span class="cc-kicker">Insight Layer</span>
        <h3>深度洞察</h3>
      </div>
      <p>把 AI、风控、网络设计与平台运行摘要压缩到首页，作为后续深入分析的入口。</p>
    </div>

    <div class="insight-grid">
      <article
        v-for="card in cards"
        :key="card.key"
        class="insight-card"
      >
        <div class="insight-card__head">
          <h4>{{ card.title }}</h4>
          <el-tag size="small" effect="dark">{{ card.status }}</el-tag>
        </div>

        <p>{{ card.summary }}</p>

        <div class="insight-metrics">
          <span
            v-for="metric in card.metrics"
            :key="`${card.key}-${metric.label}`"
            class="insight-metric"
          >
            <small>{{ metric.label }}</small>
            <strong>{{ metric.value }}</strong>
          </span>
        </div>

        <el-button text type="primary" @click="router.push(card.route)">
          查看详情
        </el-button>
      </article>
    </div>
  </section>
</template>

<script setup>
import { useRouter } from 'vue-router'

defineProps({
  cards: {
    type: Array,
    default: () => []
  }
})

const router = useRouter()
</script>

<style scoped>
.insight-summary {
  padding: 24px;
}

.insight-header {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 16px;
  margin-bottom: 18px;
}

.insight-header h3 {
  margin: 10px 0 0;
  font-size: 24px;
  color: var(--cc-text-primary);
}

.insight-header p {
  max-width: 520px;
  color: var(--cc-text-secondary);
  text-align: right;
  line-height: 1.7;
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.insight-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  padding: 18px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
}

.insight-card__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.insight-card h4 {
  margin: 0;
  color: var(--cc-text-primary);
  font-size: 18px;
}

.insight-card p {
  margin: 0;
  color: var(--cc-text-secondary);
  line-height: 1.7;
}

.insight-metrics {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.insight-metric {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
}

.insight-metric small {
  color: var(--cc-text-muted);
}

.insight-metric strong {
  color: var(--cc-text-primary);
}

@media (max-width: 1200px) {
  .insight-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .insight-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .insight-header p {
    text-align: left;
  }
}

@media (max-width: 768px) {
  .insight-summary {
    padding: 18px;
  }

  .insight-grid {
    grid-template-columns: 1fr;
  }
}
</style>
