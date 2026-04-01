<template>
  <div class="skeleton-wrapper">
    <!-- 表格骨架 -->
    <div v-if="type === 'table'" class="skeleton-table">
      <div class="skeleton-header">
        <div v-for="i in columns" :key="i" class="skeleton-cell"></div>
      </div>
      <div v-for="row in rows" :key="row" class="skeleton-row">
        <div v-for="col in columns" :key="col" class="skeleton-cell"></div>
      </div>
    </div>

    <!-- 卡片骨架 -->
    <div v-else-if="type === 'card'" class="skeleton-card">
      <div class="skeleton-card-header"></div>
      <div class="skeleton-card-body">
        <div class="skeleton-line" style="width: 80%"></div>
        <div class="skeleton-line" style="width: 60%"></div>
        <div class="skeleton-line" style="width: 90%"></div>
      </div>
    </div>

    <!-- 图表骨架 -->
    <div v-else-if="type === 'chart'" class="skeleton-chart">
      <div class="skeleton-chart-header"></div>
      <div class="skeleton-chart-body">
        <div class="skeleton-chart-bars">
          <div v-for="i in 5" :key="i" class="skeleton-bar" :style="{ height: Math.random() * 60 + 40 + '%' }"></div>
        </div>
      </div>
    </div>

    <!-- 统计卡片骨架 -->
    <div v-else-if="type === 'stat'" class="skeleton-stat">
      <div class="skeleton-stat-icon"></div>
      <div class="skeleton-stat-content">
        <div class="skeleton-stat-value"></div>
        <div class="skeleton-stat-label"></div>
      </div>
    </div>

    <!-- 默认骨架 -->
    <div v-else class="skeleton-default">
      <div class="skeleton-line"></div>
      <div class="skeleton-line" style="width: 80%"></div>
      <div class="skeleton-line" style="width: 60%"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  type: {
    type: String,
    default: 'default',
    validator: (val) => ['default', 'table', 'card', 'chart', 'stat'].includes(val)
  },
  rows: {
    type: Number,
    default: 5
  },
  columns: {
    type: Number,
    default: 4
  }
})
</script>

<style scoped>
.skeleton-wrapper {
  width: 100%;
}

/* 闪烁动画 */
@keyframes skeleton-loading {
  0% {
    background-position: -200px 0;
  }
  100% {
    background-position: calc(200px + 100%) 0;
  }
}

.skeleton-line,
.skeleton-cell,
.skeleton-bar {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200px 100%;
  animation: skeleton-loading 1.5s ease-in-out infinite;
  border-radius: 4px;
}

/* 表格骨架 */
.skeleton-table {
  width: 100%;
}

.skeleton-header {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.skeleton-row {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
}

.skeleton-cell {
  flex: 1;
  height: 20px;
}

/* 卡片骨架 */
.skeleton-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
}

.skeleton-card-header {
  height: 24px;
  width: 40%;
  margin-bottom: 16px;
}

.skeleton-card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-line {
  height: 16px;
}

/* 图表骨架 */
.skeleton-chart {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
}

.skeleton-chart-header {
  height: 20px;
  width: 30%;
  margin-bottom: 16px;
}

.skeleton-chart-body {
  height: 200px;
}

.skeleton-chart-bars {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 100%;
  padding: 0 20px;
}

.skeleton-bar {
  width: 30px;
  border-radius: 4px 4px 0 0;
}

/* 统计卡片骨架 */
.skeleton-stat {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.skeleton-stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
}

.skeleton-stat-content {
  flex: 1;
}

.skeleton-stat-value {
  height: 28px;
  width: 60%;
  margin-bottom: 8px;
}

.skeleton-stat-label {
  height: 16px;
  width: 40%;
}

/* 默认骨架 */
.skeleton-default {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
