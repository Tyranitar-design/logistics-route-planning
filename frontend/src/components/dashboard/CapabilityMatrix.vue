<template>
  <section class="capability-matrix cc-panel cc-panel--strong">
    <div class="matrix-header">
      <div>
        <span class="cc-kicker">Platform Matrix</span>
        <h3>平台能力总览</h3>
      </div>
      <p>让首页不仅展示现场态势，也一眼看清整个平台的能力版图。</p>
    </div>

    <div class="matrix-grid">
      <article
        v-for="item in capabilities"
        :key="item.key"
        class="matrix-card"
      >
        <div class="matrix-card__head">
          <span class="matrix-icon">{{ item.icon }}</span>
          <el-tag size="small" effect="dark">{{ item.status }}</el-tag>
        </div>

        <h4>{{ item.title }}</h4>
        <p>{{ item.summary }}</p>

        <div class="matrix-metrics">
          <span
            v-for="metric in item.metrics"
            :key="`${item.key}-${metric.label}`"
            class="matrix-metric"
          >
            <small>{{ metric.label }}</small>
            <strong>{{ metric.value }}</strong>
          </span>
        </div>

        <el-button text type="primary" @click="router.push(item.route)">
          进入模块
        </el-button>
      </article>
    </div>
  </section>
</template>

<script setup>
import { useRouter } from 'vue-router'

defineProps({
  capabilities: {
    type: Array,
    default: () => []
  }
})

const router = useRouter()
</script>

<style scoped>
.capability-matrix {
  padding: 24px;
}

.matrix-header {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 16px;
  margin-bottom: 20px;
}

.matrix-header h3 {
  margin: 10px 0 0;
  font-size: 24px;
  color: var(--cc-text-primary);
}

.matrix-header p {
  max-width: 440px;
  color: var(--cc-text-secondary);
  line-height: 1.7;
  text-align: right;
}

.matrix-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.matrix-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  padding: 18px;
  border-radius: var(--cc-radius-md);
  border: 1px solid rgba(0, 212, 255, 0.12);
  background: rgba(255, 255, 255, 0.03);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02);
  transition: transform 0.24s ease, border-color 0.24s ease, box-shadow 0.24s ease;
}

.matrix-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 212, 255, 0.28);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.24);
}

.matrix-card__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.matrix-icon {
  display: inline-grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.18);
  font-size: 22px;
}

.matrix-card h4 {
  margin: 0;
  font-size: 18px;
  color: var(--cc-text-primary);
}

.matrix-card p {
  margin: 0;
  color: var(--cc-text-secondary);
  line-height: 1.7;
}

.matrix-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.matrix-metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.matrix-metric small {
  color: var(--cc-text-muted);
}

.matrix-metric strong {
  color: var(--cc-text-primary);
}

@media (max-width: 1200px) {
  .matrix-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .matrix-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .matrix-header p {
    text-align: left;
  }
}

@media (max-width: 768px) {
  .capability-matrix {
    padding: 18px;
  }

  .matrix-grid {
    grid-template-columns: 1fr;
  }
}
</style>
