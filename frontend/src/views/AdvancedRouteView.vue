<template>
  <div class="advanced-route-page">
    <!-- 背景动效 -->
    <div class="bg-effects">
      <div class="grid-lines"></div>
      <div class="scan-line"></div>
    </div>

    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="glow-title">🧠 高级路径优化</h1>
        <span class="subtitle">ADVANCED ROUTE OPTIMIZATION</span>
      </div>
    </div>

    <!-- 算法选择卡片 -->
    <div class="algorithm-cards">
      <div 
        v-for="algo in algorithms" 
        :key="algo.id"
        class="algo-card"
        :class="{ active: selectedAlgorithm === algo.id }"
        @click="selectedAlgorithm = algo.id"
      >
        <div class="algo-icon">{{ getAlgoIcon(algo.id) }}</div>
        <div class="algo-name">{{ algo.name }}</div>
        <div class="algo-desc">{{ algo.description.slice(0, 30) }}...</div>
        <div class="algo-badge">{{ algo.convergence }}</div>
      </div>
    </div>

    <!-- 当前算法详情 -->
    <div class="algo-detail" v-if="currentAlgo">
      <div class="detail-header">
        <span class="detail-icon">{{ getAlgoIcon(currentAlgo.id) }}</span>
        <span class="detail-name">{{ currentAlgo.name }}</span>
        <span class="detail-en">{{ currentAlgo.name_en }}</span>
      </div>
      <div class="detail-content">
        <p>{{ currentAlgo.description }}</p>
        <div class="detail-tags">
          <el-tag size="small" type="success">{{ currentAlgo.best_for }}</el-tag>
          <el-tag size="small" type="info">{{ currentAlgo.performance }}</el-tag>
        </div>
      </div>
    </div>

    <!-- 参数配置 -->
    <div class="config-panel" v-if="currentAlgo && currentAlgo.parameters">
      <div class="panel-title">参数配置</div>
      <div class="param-grid">
        <div class="param-item" v-for="(param, key) in currentAlgo.parameters" :key="key">
          <span class="param-label">{{ param.description }}</span>
          <el-input-number 
            v-model="params[key]" 
            :min="1" 
            :max="1000" 
            size="small"
            style="width: 100%"
          />
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-buttons">
      <el-button type="primary" size="large" :loading="optimizing" @click="handleOptimize">
        <el-icon><Cpu /></el-icon>
        开始优化
      </el-button>
      <el-button size="large" :loading="comparing" @click="handleCompare">
        <el-icon><DataAnalysis /></el-icon>
        算法对比
      </el-button>
    </div>

    <!-- 优化结果 -->
    <div class="result-panel" v-if="result">
      <div class="result-header">
        <span class="result-title">优化结果</span>
        <el-tag :type="result.success ? 'success' : 'danger'">
          {{ result.success ? '成功' : '失败' }}
        </el-tag>
      </div>
      
      <div class="result-stats">
        <div class="stat-item">
          <span class="stat-label">最优成本</span>
          <span class="stat-value">{{ result.best_cost }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">总距离</span>
          <span class="stat-value">{{ result.best_distance }} km</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">迭代次数</span>
          <span class="stat-value">{{ result.iterations }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">执行时间</span>
          <span class="stat-value">{{ result.execution_time }}s</span>
        </div>
      </div>

      <!-- 收敛曲线 -->
      <div class="convergence-chart" v-if="result.convergence_history && result.convergence_history.length > 0">
        <div class="chart-title">收敛曲线</div>
        <div class="chart-container">
          <div 
            v-for="(value, idx) in result.convergence_history.slice(0, 20)" 
            :key="idx"
            class="chart-bar"
            :style="{ height: getBarHeight(value) + '%' }"
          >
            <span class="bar-value">{{ value }}</span>
          </div>
        </div>
      </div>

      <!-- 最优路线 -->
      <div class="route-display" v-if="result.best_route && result.best_route.length > 0">
        <div class="route-title">最优路线 ({{ result.best_route.length }} 个节点)</div>
        <div class="route-nodes">
          <div 
            v-for="(nodeId, idx) in result.best_route.slice(0, 15)" 
            :key="idx"
            class="route-node"
          >
            <span class="node-index">{{ idx + 1 }}</span>
            <span class="node-id">节点{{ nodeId }}</span>
            <span class="node-arrow" v-if="idx < Math.min(14, result.best_route.length - 1)">→</span>
          </div>
          <span v-if="result.best_route.length > 15" class="more-nodes">
            ... 还有 {{ result.best_route.length - 15 }} 个节点
          </span>
        </div>
      </div>
    </div>

    <!-- 算法对比结果 -->
    <div class="compare-panel" v-if="compareResults">
      <div class="compare-header">算法对比结果</div>
      <div class="compare-list">
        <div 
          v-for="(res, algoId) in compareResults" 
          :key="algoId"
          class="compare-item"
          :class="{ best: bestAlgorithm === algoId }"
        >
          <div class="compare-rank">
            {{ bestAlgorithm === algoId ? '🏆' : getAlgoIcon(algoId) }}
          </div>
          <div class="compare-info">
            <div class="compare-name">{{ getAlgoName(algoId) }}</div>
            <div class="compare-stats">
              <span>成本: {{ res.best_cost }}</span>
              <span>时间: {{ res.execution_time }}s</span>
            </div>
          </div>
          <el-tag v-if="bestAlgorithm === algoId" type="success" size="small">最优</el-tag>
        </div>
      </div>
      <div class="compare-recommendation" v-if="recommendation">
        {{ recommendation }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Cpu, DataAnalysis } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { optimizeRoute, compareAlgorithms, getAlgorithms } from '@/api/advancedRoute'

// 状态
const algorithms = ref([])
const selectedAlgorithm = ref('hybrid')
const optimizing = ref(false)
const comparing = ref(false)
const result = ref(null)
const compareResults = ref(null)
const bestAlgorithm = ref(null)
const recommendation = ref('')

// 参数
const params = reactive({
  ant_count: 30,
  max_iterations: 100,
  alpha: 1.0,
  beta: 2.0,
  rho: 0.5,
  particle_count: 30,
  w: 0.729,
  c1: 1.494,
  c2: 1.494,
  learning_rate: 0.1,
  discount_factor: 0.95,
  epsilon: 0.3,
  episodes: 500
})

// 当前选中算法
const currentAlgo = computed(() => 
  algorithms.value.find(a => a.id === selectedAlgorithm.value)
)

// 获取算法列表
const loadAlgorithms = async () => {
  try {
    const res = await getAlgorithms()
    if (res.success) {
      algorithms.value = res.algorithms
    }
  } catch (e) {
    console.error('获取算法列表失败:', e)
  }
}

// 执行优化
const handleOptimize = async () => {
  optimizing.value = true
  try {
    const res = await optimizeRoute({
      algorithm: selectedAlgorithm.value,
      params: params
    })
    
    if (res.success) {
      result.value = res
      compareResults.value = null
      ElMessage.success(`优化完成！成本: ${res.best_cost}`)
    } else {
      ElMessage.error(res.error || '优化失败')
    }
  } catch (e) {
    ElMessage.error('优化失败: ' + e.message)
  } finally {
    optimizing.value = false
  }
}

// 算法对比
const handleCompare = async () => {
  comparing.value = true
  try {
    const res = await compareAlgorithms()
    
    if (res.success) {
      compareResults.value = res.results
      bestAlgorithm.value = res.best_algorithm
      recommendation.value = res.recommendation
      result.value = null
      ElMessage.success('对比完成！')
    }
  } catch (e) {
    ElMessage.error('对比失败')
  } finally {
    comparing.value = false
  }
}

// 辅助方法
const getAlgoIcon = (id) => {
  const icons = { aco: '🐜', pso: '🐦', drl: '🧠', hybrid: '🔄' }
  return icons[id] || '⚙️'
}

const getAlgoName = (id) => {
  const algo = algorithms.value.find(a => a.id === id)
  return algo ? algo.name : id
}

const getBarHeight = (value) => {
  if (!result.value || !result.value.convergence_history) return 0
  const max = Math.max(...result.value.convergence_history)
  const min = Math.min(...result.value.convergence_history)
  if (max === min) return 50
  return 100 - ((value - min) / (max - min)) * 100
}

onMounted(() => {
  loadAlgorithms()
})
</script>

<style scoped>
/* 移动端优先设计 */
.advanced-route-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #0d1033 100%);
  padding: 12px;
  color: #fff;
  position: relative;
  overflow-x: hidden;
}

/* 背景效果 */
.bg-effects {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.grid-lines {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 30px 30px;
}

.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.5), transparent);
  animation: scan 4s linear infinite;
}

@keyframes scan {
  0% { top: 0; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { top: 100%; opacity: 0; }
}

/* 顶部 */
.page-header {
  position: relative;
  z-index: 1;
  margin-bottom: 16px;
  padding: 16px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
}

.glow-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(90deg, #00d4ff, #00ff88, #ffd93d);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  display: block;
  font-size: 10px;
  color: rgba(255,255,255,0.4);
  letter-spacing: 2px;
  margin-top: 4px;
}

/* 算法卡片 */
.algorithm-cards {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.algo-card {
  padding: 12px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s;
}

.algo-card.active {
  background: rgba(0, 212, 255, 0.15);
  border-color: #00d4ff;
}

.algo-card:hover {
  transform: translateY(-2px);
}

.algo-icon {
  font-size: 24px;
  margin-bottom: 6px;
}

.algo-name {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}

.algo-desc {
  font-size: 10px;
  color: rgba(255,255,255,0.6);
  margin-bottom: 6px;
}

.algo-badge {
  font-size: 9px;
  padding: 2px 6px;
  background: rgba(0, 255, 136, 0.2);
  border-radius: 8px;
  color: #00ff88;
  display: inline-block;
}

/* 算法详情 */
.algo-detail {
  position: relative;
  z-index: 1;
  padding: 14px;
  background: rgba(0, 212, 255, 0.08);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 10px;
  margin-bottom: 16px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.detail-icon {
  font-size: 20px;
}

.detail-name {
  font-size: 15px;
  font-weight: 600;
}

.detail-en {
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

.detail-content p {
  font-size: 12px;
  color: rgba(255,255,255,0.8);
  line-height: 1.5;
  margin-bottom: 10px;
}

.detail-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* 参数配置 */
.config-panel {
  position: relative;
  z-index: 1;
  padding: 14px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 10px;
  margin-bottom: 16px;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
}

.param-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.param-label {
  font-size: 10px;
  color: rgba(255,255,255,0.6);
}

/* 操作按钮 */
.action-buttons {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.action-buttons .el-button {
  flex: 1;
}

/* 结果面板 */
.result-panel, .compare-panel {
  position: relative;
  z-index: 1;
  padding: 14px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 10px;
  margin-bottom: 16px;
}

.result-header, .compare-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.result-title, .compare-header {
  font-size: 14px;
  font-weight: 600;
}

.result-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  padding: 10px;
  background: rgba(0, 212, 255, 0.08);
  border-radius: 8px;
}

.stat-label {
  font-size: 10px;
  color: rgba(255,255,255,0.5);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 16px;
  font-weight: 700;
  color: #00ff88;
}

/* 收敛曲线 */
.convergence-chart {
  margin-bottom: 14px;
}

.chart-title, .route-title {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 10px;
}

.chart-container {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 100px;
  padding: 10px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
}

.chart-bar {
  flex: 1;
  background: linear-gradient(to top, #00d4ff, #00ff88);
  border-radius: 2px 2px 0 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  min-height: 5px;
}

.bar-value {
  font-size: 7px;
  color: #fff;
  padding-top: 2px;
}

/* 路线展示 */
.route-nodes {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.route-node {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: rgba(0, 212, 255, 0.1);
  border-radius: 6px;
  font-size: 11px;
}

.node-index {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #00d4ff;
  color: #000;
  border-radius: 50%;
  font-size: 9px;
  font-weight: 600;
}

.node-arrow {
  color: rgba(255,255,255,0.4);
}

.more-nodes {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
  padding: 4px 8px;
}

/* 对比列表 */
.compare-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.compare-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
}

.compare-item.best {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.compare-rank {
  font-size: 20px;
}

.compare-info {
  flex: 1;
}

.compare-name {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}

.compare-stats {
  display: flex;
  gap: 12px;
  font-size: 10px;
  color: rgba(255,255,255,0.6);
}

.compare-recommendation {
  margin-top: 12px;
  padding: 10px;
  background: rgba(0, 255, 136, 0.1);
  border-radius: 8px;
  font-size: 12px;
  color: #00ff88;
  text-align: center;
}

/* Element Plus 覆盖 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #00d4ff, #00ff88);
  border: none;
  color: #000;
}

:deep(.el-input-number .el-input__wrapper) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
}

:deep(.el-input-number .el-input__inner) {
  color: #fff;
}

:deep(.el-tag) {
  background: rgba(0, 212, 255, 0.2);
  border-color: rgba(0, 212, 255, 0.3);
  color: #00d4ff;
}

/* 平板适配 */
@media (min-width: 768px) {
  .advanced-route-page {
    padding: 16px;
  }
  
  .algorithm-cards {
    grid-template-columns: repeat(4, 1fr);
  }
  
  .param-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  
  .result-stats {
    grid-template-columns: repeat(4, 1fr);
  }
}

/* 大屏幕 */
@media (min-width: 1024px) {
  .advanced-route-page {
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
  }
  
  .glow-title {
    font-size: 24px;
  }
}
</style>