<template>
  <section class="command-overview cc-panel cc-panel--strong">
    <div class="overview-top">
      <div>
        <span class="cc-kicker">Decision Layer</span>
        <h3>决策建议总览</h3>
      </div>
      <div class="overview-alert">
        <small>风险提示</small>
        <strong>{{ alertCount }}</strong>
      </div>
    </div>

    <div class="overview-lead">
      <span class="lead-label">推荐策略</span>
      <h4>{{ solverLabel }}</h4>
      <p>当前系统建议优先以高及时率与较优成本平衡模式推进当班调度。</p>
    </div>

    <div class="overview-stats">
      <div class="overview-stat">
        <small>履约率</small>
        <strong>{{ deliveryRate }}%</strong>
      </div>
      <div class="overview-stat">
        <small>待调度订单</small>
        <strong>{{ pendingOrders }}</strong>
      </div>
      <div class="overview-stat">
        <small>可视运力</small>
        <strong>{{ vehicleCount }}</strong>
      </div>
    </div>

    <div class="overview-actions">
      <el-button type="primary" @click="router.push('/optimization-engine')">
        进入优化引擎
      </el-button>
      <el-button @click="router.push('/dispatch')">
        查看调度执行
      </el-button>
    </div>
  </section>
</template>

<script setup>
import { useRouter } from 'vue-router'

defineProps({
  deliveryRate: {
    type: Number,
    default: 0
  },
  solverLabel: {
    type: String,
    default: '多目标平衡策略'
  },
  alertCount: {
    type: Number,
    default: 0
  },
  pendingOrders: {
    type: Number,
    default: 0
  },
  vehicleCount: {
    type: Number,
    default: 0
  }
})

const router = useRouter()
</script>

<style scoped>
.command-overview {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: 100%;
  padding: 22px;
}

.overview-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.overview-top h3 {
  margin: 10px 0 0;
  font-size: 24px;
  color: var(--cc-text-primary);
}

.overview-alert {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 91, 110, 0.1);
  border: 1px solid rgba(255, 91, 110, 0.18);
}

.overview-alert small {
  color: var(--cc-text-muted);
}

.overview-alert strong {
  font-size: 24px;
  color: #ffd2d8;
}

.overview-lead {
  padding: 18px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.12), rgba(17, 224, 183, 0.08));
  border: 1px solid rgba(0, 212, 255, 0.2);
}

.lead-label {
  color: var(--cc-text-muted);
  font-size: 12px;
  letter-spacing: 0.1em;
}

.overview-lead h4 {
  margin: 10px 0 8px;
  font-size: 26px;
  color: var(--cc-text-primary);
}

.overview-lead p {
  margin: 0;
  color: var(--cc-text-secondary);
  line-height: 1.7;
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.overview-stat {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.overview-stat small {
  color: var(--cc-text-muted);
}

.overview-stat strong {
  font-size: 24px;
  color: var(--cc-text-primary);
}

.overview-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

@media (max-width: 768px) {
  .command-overview {
    padding: 18px;
  }

  .overview-top {
    flex-direction: column;
  }

  .overview-alert {
    width: 100%;
    align-items: flex-start;
  }

  .overview-stats {
    grid-template-columns: 1fr;
  }
}
</style>
