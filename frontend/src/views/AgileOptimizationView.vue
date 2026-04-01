<template>
  <div class="agile-page">
    <!-- 背景动效 -->
    <div class="bg-effects">
      <div class="grid-lines"></div>
      <div class="scan-line"></div>
      <div class="pulse-ring"></div>
    </div>

    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="glow-title">⚡ 敏捷路径优化中心</h1>
        <span class="subtitle">AGILE ROUTE OPTIMIZATION</span>
      </div>
      <div class="header-right">
        <div class="status-badge">
          <span class="status-dot"></span>
          <span>智能优化引擎就绪</span>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：参数配置 -->
      <div class="config-panel">
        <div class="panel-card">
          <div class="card-header">
            <span class="header-icon">🎯</span>
            <span class="header-title">优化目标</span>
          </div>
          
          <!-- 算法选择 -->
          <div class="config-section">
            <label class="section-label">优化算法</label>
            <el-select v-model="config.algorithm" style="width: 100%">
              <el-option 
                v-for="algo in algorithms" 
                :key="algo.id" 
                :label="algo.name" 
                :value="algo.id"
              >
                <div class="algo-option">
                  <span class="algo-name">{{ algo.name }}</span>
                  <span class="algo-desc">{{ algo.description }}</span>
                </div>
              </el-option>
            </el-select>
            <div class="algo-info" v-if="currentAlgorithm">
              <el-tag size="small" effect="dark">{{ currentAlgorithm.best_for }}</el-tag>
              <span class="algo-performance">{{ currentAlgorithm.performance }}</span>
            </div>
          </div>

          <!-- 权重调节 -->
          <div class="config-section">
            <label class="section-label">优化权重</label>
            <div class="weight-slider">
              <div class="weight-item">
                <span class="weight-label">💰 成本优先</span>
                <el-slider v-model="config.weights.cost" :max="100" :format-tooltip="v => `${v}%`" />
              </div>
              <div class="weight-item">
                <span class="weight-label">⏰ 时效优先</span>
                <el-slider v-model="config.weights.time" :max="100" :format-tooltip="v => `${v}%`" />
              </div>
              <div class="weight-item">
                <span class="weight-label">📊 满载率优先</span>
                <el-slider v-model="config.weights.loadRate" :max="100" :format-tooltip="v => `${v}%`" />
              </div>
            </div>
          </div>

          <!-- 约束条件 -->
          <div class="config-section">
            <label class="section-label">约束条件</label>
            <div class="constraint-grid">
              <div class="constraint-item">
                <span class="constraint-label">最大距离(km)</span>
                <el-input-number v-model="config.constraints.maxDistance" :min="50" :max="1000" :step="50" size="small" />
              </div>
              <div class="constraint-item">
                <span class="constraint-label">最大时长(min)</span>
                <el-input-number v-model="config.constraints.maxDuration" :min="60" :max="720" :step="30" size="small" />
              </div>
              <div class="constraint-item">
                <span class="constraint-label">最小满载率(%)</span>
                <el-input-number v-model="config.constraints.minLoadRate" :min="0" :max="100" :step="10" size="small" />
              </div>
              <div class="constraint-item">
                <span class="constraint-label">时间窗约束</span>
                <el-switch v-model="config.constraints.timeWindowStrict" />
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="action-buttons">
            <el-button type="primary" size="large" :loading="optimizing" @click="handleOptimize">
              <el-icon><Cpu /></el-icon>
              开始优化
            </el-button>
            <el-button size="large" @click="handleCompare" :loading="comparing">
              <el-icon><DataAnalysis /></el-icon>
              算法对比
            </el-button>
          </div>
        </div>

        <!-- 智能拼单 -->
        <div class="panel-card">
          <div class="card-header">
            <span class="header-icon">🧩</span>
            <span class="header-title">智能拼单建议</span>
            <el-badge :value="mergeClusters.length" type="primary" />
          </div>
          <div class="merge-list">
            <div 
              v-for="(cluster, idx) in mergeClusters" 
              :key="idx" 
              class="merge-item"
              @click="showMergeDetail(cluster)"
            >
              <div class="merge-header">
                <span class="merge-badge">合并方案 {{ idx + 1 }}</span>
                <span class="merge-benefit">节省 ¥{{ cluster.merge_benefit }}</span>
              </div>
              <div class="merge-info">
                <span class="merge-orders">{{ cluster.order_ids.length }} 单合并</span>
                <span class="merge-weight">总重 {{ cluster.total_weight }}t</span>
              </div>
              <div class="merge-route">
                {{ cluster.pickup_area }} → {{ cluster.delivery_area }}
              </div>
            </div>
            <el-empty v-if="mergeClusters.length === 0" description="暂无拼单建议" :image-size="60" />
          </div>
          <el-button type="success" size="small" style="width: 100%; margin-top: 12px" @click="loadMergeSuggestions">
            刷新拼单建议
          </el-button>
        </div>
      </div>

      <!-- 中间：优化结果 -->
      <div class="result-panel">
        <!-- 优化统计 -->
        <div class="stats-row">
          <div class="stat-card" v-for="(stat, idx) in statsCards" :key="idx">
            <div class="stat-icon">{{ stat.icon }}</div>
            <div class="stat-content">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
            <div class="stat-trend" :class="stat.trend > 0 ? 'up' : 'down'" v-if="stat.trend">
              {{ stat.trend > 0 ? '+' : '' }}{{ stat.trend }}%
            </div>
          </div>
        </div>

        <!-- 路线结果 -->
        <div class="routes-container">
          <div class="container-header">
            <span class="header-title">优化路线方案</span>
            <div class="header-actions">
              <el-button type="success" size="small" :disabled="routes.length === 0" @click="handleApply">
                应用方案
              </el-button>
            </div>
          </div>
          
          <div class="routes-list" v-if="routes.length > 0">
            <div v-for="(route, idx) in routes" :key="idx" class="route-card">
              <div class="route-header">
                <span class="route-index">{{ idx + 1 }}</span>
                <span class="route-vehicle">{{ route.vehicle_info.plate_number }}</span>
                <el-tag :type="route.load_rate > 80 ? 'success' : 'warning'" size="small">
                  满载率 {{ route.load_rate }}%
                </el-tag>
                <span class="route-score">评分 {{ route.score }}</span>
              </div>
              
              <div class="route-stats">
                <div class="route-stat">
                  <span class="stat-label">距离</span>
                  <span class="stat-value">{{ route.total_distance }} km</span>
                </div>
                <div class="route-stat">
                  <span class="stat-label">时长</span>
                  <span class="stat-value">{{ route.total_duration }} min</span>
                </div>
                <div class="route-stat">
                  <span class="stat-label">成本</span>
                  <span class="stat-value">¥{{ route.total_cost.total }}</span>
                </div>
                <div class="route-stat">
                  <span class="stat-label">左转</span>
                  <span class="stat-value">{{ route.left_turns }} 次</span>
                </div>
              </div>

              <div class="route-nodes">
                <div class="node-sequence">
                  <div v-for="(node, nIdx) in route.nodes" :key="nIdx" class="node-item">
                    <span class="node-type" :class="node.type">{{ node.type === 'pickup' ? '取' : '送' }}</span>
                    <span class="node-address">{{ node.address || '未知地址' }}</span>
                  </div>
                </div>
              </div>

              <div class="route-tips">
                <div v-for="(tip, tIdx) in route.optimization_tips" :key="tIdx" class="tip-item">
                  {{ tip }}
                </div>
              </div>

              <div class="cost-breakdown">
                <div class="cost-item">
                  <span class="cost-label">燃油</span>
                  <span class="cost-value">¥{{ route.total_cost.fuel }}</span>
                </div>
                <div class="cost-item">
                  <span class="cost-label">路桥</span>
                  <span class="cost-value">¥{{ route.total_cost.toll }}</span>
                </div>
                <div class="cost-item">
                  <span class="cost-label">人工</span>
                  <span class="cost-value">¥{{ route.total_cost.labor }}</span>
                </div>
                <div class="cost-item">
                  <span class="cost-label">其他</span>
                  <span class="cost-value">¥{{ route.total_cost.depreciation + route.total_cost.time_cost }}</span>
                </div>
              </div>
            </div>
          </div>
          
          <el-empty v-else description="请点击【开始优化】生成方案" :image-size="120" />
        </div>
      </div>

      <!-- 右侧：算法对比与实时建议 -->
      <div class="side-panel">
        <!-- 算法对比结果 -->
        <div class="panel-card" v-if="comparisonResults.length > 0">
          <div class="card-header">
            <span class="header-icon">📊</span>
            <span class="header-title">算法对比</span>
          </div>
          <div class="comparison-list">
            <div 
              v-for="(result, idx) in comparisonResults" 
              :key="idx" 
              class="comparison-item"
              :class="{ best: idx === 0 }"
            >
              <div class="comparison-rank">{{ idx + 1 }}</div>
              <div class="comparison-content">
                <div class="comparison-name">{{ getAlgorithmName(result.algorithm) }}</div>
                <div class="comparison-stats">
                  <span>成本: ¥{{ result.total_cost }}</span>
                  <span>距离: {{ result.total_distance }}km</span>
                  <span>满载率: {{ result.avg_load_rate }}%</span>
                </div>
                <div class="comparison-meta">
                  耗时 {{ result.execution_time.toFixed(2) }}s | 改进 {{ result.improvement_rate.toFixed(1) }}%
                </div>
              </div>
              <el-tag v-if="idx === 0" type="success" size="small">推荐</el-tag>
            </div>
          </div>
        </div>

        <!-- 成本估算 -->
        <div class="panel-card">
          <div class="card-header">
            <span class="header-icon">💰</span>
            <span class="header-title">成本估算器</span>
          </div>
          <div class="cost-estimator">
            <el-form label-position="top" size="small">
              <el-form-item label="行驶距离(km)">
                <el-input-number v-model="costEstimate.distance" :min="1" :max="2000" style="width: 100%" />
              </el-form-item>
              <el-form-item label="行驶时长(min)">
                <el-input-number v-model="costEstimate.duration" :min="1" :max="1440" style="width: 100%" />
              </el-form-item>
              <el-form-item label="车辆类型">
                <el-select v-model="costEstimate.vehicleType" style="width: 100%">
                  <el-option label="小型货车 (3t)" value="truck_small" />
                  <el-option label="中型货车 (8t)" value="truck_medium" />
                  <el-option label="大型货车 (15t)" value="truck_large" />
                  <el-option label="厢式货车 (1.5t)" value="van" />
                </el-select>
              </el-form-item>
              <el-form-item label="载重(t)">
                <el-input-number v-model="costEstimate.loadWeight" :min="0" :max="20" :precision="1" style="width: 100%" />
              </el-form-item>
            </el-form>
            <el-button type="primary" size="small" style="width: 100%" @click="handleEstimateCost">
              计算成本
            </el-button>
            
            <div class="estimated-cost" v-if="estimatedCost">
              <div class="cost-total">¥{{ estimatedCost.total }}</div>
              <div class="cost-detail">
                <span>燃油: ¥{{ estimatedCost.fuel }}</span>
                <span>路桥: ¥{{ estimatedCost.toll }}</span>
                <span>人工: ¥{{ estimatedCost.labor }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 优化历史 -->
        <div class="panel-card">
          <div class="card-header">
            <span class="header-icon">📜</span>
            <span class="header-title">优化历史</span>
          </div>
          <div class="history-list">
            <div v-for="(item, idx) in optimizationHistory" :key="idx" class="history-item">
              <div class="history-time">{{ item.time }}</div>
              <div class="history-info">
                <span class="history-algo">{{ item.algorithm }}</span>
                <span class="history-result">节省 {{ item.improvement }}%</span>
              </div>
            </div>
            <el-empty v-if="optimizationHistory.length === 0" description="暂无历史记录" :image-size="40" />
          </div>
        </div>
      </div>
    </div>

    <!-- 合并详情弹窗 -->
    <el-dialog v-model="mergeDialogVisible" title="拼单详情" width="500px">
      <div v-if="selectedMerge" class="merge-detail">
        <div class="detail-row">
          <span class="detail-label">订单数量</span>
          <span class="detail-value">{{ selectedMerge.order_ids.length }} 单</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">总重量</span>
          <span class="detail-value">{{ selectedMerge.total_weight }} 吨</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">总体积</span>
          <span class="detail-value">{{ selectedMerge.total_volume }} m³</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">预计节省</span>
          <span class="detail-value highlight">¥{{ selectedMerge.merge_benefit }}</span>
        </div>
        <div class="detail-section">
          <div class="section-title">包含订单</div>
          <div class="order-list">
            <div v-for="order in selectedMerge.order_details" :key="order.id" class="order-item">
              <span class="order-number">{{ order.order_number }}</span>
              <span class="order-customer">{{ order.customer }}</span>
              <span class="order-weight">{{ order.weight }}t</span>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Cpu, DataAnalysis } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  optimizeRoutes,
  getMergeSuggestions,
  getAlgorithms,
  estimateCost,
  applyOptimization,
  compareAlgorithms
} from '@/api/agile'

// 配置
const config = reactive({
  algorithm: 'simulated_annealing',
  weights: {
    cost: 50,
    time: 30,
    loadRate: 20
  },
  constraints: {
    maxDistance: 500,
    maxDuration: 480,
    minLoadRate: 50,
    timeWindowStrict: false
  }
})

// 算法列表
const algorithms = ref([])
const currentAlgorithm = computed(() => 
  algorithms.value.find(a => a.id === config.algorithm)
)

// 状态
const optimizing = ref(false)
const comparing = ref(false)

// 结果
const routes = ref([])
const summary = ref({})
const mergeClusters = ref([])
const comparisonResults = ref([])
const optimizationHistory = ref([])

// 统计卡片
const statsCards = computed(() => [
  {
    icon: '📦',
    label: '已分配订单',
    value: summary.value.assigned_orders || 0,
    trend: null
  },
  {
    icon: '🚛',
    label: '使用车辆',
    value: summary.value.vehicles_used || 0,
    trend: null
  },
  {
    icon: '💰',
    label: '总成本',
    value: `¥${summary.value.total_cost_yuan || 0}`,
    trend: summary.value.improvement_rate || 0
  },
  {
    icon: '📊',
    label: '平均满载率',
    value: `${summary.value.avg_load_rate || 0}%`,
    trend: null
  }
])

// 成本估算
const costEstimate = reactive({
  distance: 100,
  duration: 120,
  vehicleType: 'truck_medium',
  loadWeight: 5
})
const estimatedCost = ref(null)

// 合并详情
const mergeDialogVisible = ref(false)
const selectedMerge = ref(null)

// 加载算法列表
const loadAlgorithms = async () => {
  try {
    const res = await getAlgorithms()
    if (res.success) {
      algorithms.value = res.algorithms
    }
  } catch (e) {
    console.error('加载算法列表失败:', e)
  }
}

// 加载拼单建议
const loadMergeSuggestions = async () => {
  try {
    const res = await getMergeSuggestions()
    if (res.success) {
      mergeClusters.value = res.clusters
    }
  } catch (e) {
    console.error('加载拼单建议失败:', e)
  }
}

// 执行优化
const handleOptimize = async () => {
  optimizing.value = true
  try {
    const res = await optimizeRoutes({
      algorithm: config.algorithm,
      weights: {
        cost: config.weights.cost / 100,
        time: config.weights.time / 100,
        load_rate: config.weights.loadRate / 100
      },
      constraints: config.constraints
    })
    
    if (res.success) {
      routes.value = res.routes
      summary.value = res.summary
      
      // 添加到历史
      optimizationHistory.value.unshift({
        time: new Date().toLocaleTimeString(),
        algorithm: getAlgorithmName(res.algorithm),
        improvement: res.improvement_rate.toFixed(1)
      })
      
      // 只保留最近10条
      if (optimizationHistory.value.length > 10) {
        optimizationHistory.value.pop()
      }
      
      ElMessage.success(`优化完成！改进 ${res.improvement_rate.toFixed(1)}%`)
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
    const res = await compareAlgorithms({
      algorithms: ['simulated_annealing', 'tabu_search', 'hybrid']
    })
    
    if (res.success) {
      comparisonResults.value = res.comparison
      ElMessage.success(`推荐使用: ${getAlgorithmName(res.best_algorithm)}`)
    }
  } catch (e) {
    ElMessage.error('对比失败')
  } finally {
    comparing.value = false
  }
}

// 应用方案
const handleApply = async () => {
  try {
    await ElMessageBox.confirm('确定应用当前优化方案吗？这将更新订单和车辆状态。', '确认应用')
    
    const routeData = routes.value.map(r => ({
      vehicle_id: r.vehicle_id,
      order_ids: r.nodes.map(n => n.order_id).filter(Boolean)
    }))
    
    const res = await applyOptimization(routeData)
    if (res.success) {
      ElMessage.success(res.message)
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('应用失败')
    }
  }
}

// 成本估算
const handleEstimateCost = async () => {
  try {
    const res = await estimateCost({
      distance: costEstimate.distance,
      duration: costEstimate.duration,
      vehicle_type: costEstimate.vehicleType,
      load_weight: costEstimate.loadWeight
    })
    
    if (res.success) {
      estimatedCost.value = res.cost_breakdown
    }
  } catch (e) {
    ElMessage.error('估算失败')
  }
}

// 显示合并详情
const showMergeDetail = (cluster) => {
  selectedMerge.value = cluster
  mergeDialogVisible.value = true
}

// 获取算法名称
const getAlgorithmName = (id) => {
  const algo = algorithms.value.find(a => a.id === id)
  return algo ? algo.name : id
}

onMounted(() => {
  loadAlgorithms()
  loadMergeSuggestions()
})
</script>

<style scoped>
.agile-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #0d1033 100%);
  padding: 16px;
  color: #fff;
  position: relative;
  overflow: hidden;
}

/* 背景效果 */
.bg-effects {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.grid-lines {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
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

.pulse-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 600px;
  height: 600px;
  transform: translate(-50%, -50%);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 50%;
  animation: pulse-ring 4s ease-out infinite;
}

@keyframes pulse-ring {
  0% { transform: translate(-50%, -50%) scale(0.8); opacity: 0.5; }
  100% { transform: translate(-50%, -50%) scale(1.5); opacity: 0; }
}

/* 顶部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px 24px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
}

.glow-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(90deg, #00d4ff, #00ff88, #ffd93d);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  display: block;
  font-size: 10px;
  color: rgba(255,255,255,0.4);
  letter-spacing: 3px;
  margin-top: 4px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(0, 255, 136, 0.1);
  border-radius: 20px;
  border: 1px solid rgba(0, 255, 136, 0.3);
  font-size: 13px;
  color: #00ff88;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #00ff88;
  border-radius: 50%;
  animation: status-pulse 2s infinite;
}

@keyframes status-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.5); }
  50% { box-shadow: 0 0 0 8px rgba(0, 255, 136, 0); }
}

/* 主内容 */
.main-content {
  display: grid;
  grid-template-columns: 320px 1fr 300px;
  gap: 16px;
}

/* 面板卡片 */
.panel-card {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.header-icon {
  font-size: 20px;
}

.header-title {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
}

/* 配置区 */
.config-section {
  margin-bottom: 20px;
}

.section-label {
  display: block;
  font-size: 12px;
  color: rgba(255,255,255,0.6);
  margin-bottom: 10px;
}

.algo-option {
  display: flex;
  flex-direction: column;
}

.algo-name {
  font-size: 14px;
}

.algo-desc {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
}

.algo-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.algo-performance {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
}

.weight-slider {
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
  padding: 12px;
}

.weight-item {
  margin-bottom: 16px;
}

.weight-item:last-child {
  margin-bottom: 0;
}

.weight-label {
  display: block;
  font-size: 12px;
  margin-bottom: 8px;
}

.constraint-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.constraint-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.constraint-label {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.action-buttons .el-button {
  flex: 1;
}

/* 拼单列表 */
.merge-list {
  max-height: 300px;
  overflow-y: auto;
}

.merge-item {
  padding: 12px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.merge-item:hover {
  background: rgba(0, 212, 255, 0.1);
}

.merge-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.merge-badge {
  font-size: 12px;
  color: #00d4ff;
}

.merge-benefit {
  font-size: 12px;
  color: #00ff88;
  font-weight: 600;
}

.merge-info {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: rgba(255,255,255,0.6);
  margin-bottom: 4px;
}

.merge-route {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
}

/* 统计卡片 */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
}

.stat-icon {
  font-size: 28px;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
}

.stat-label {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
}

.stat-trend {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}

.stat-trend.up {
  background: rgba(0, 255, 136, 0.2);
  color: #00ff88;
}

.stat-trend.down {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
}

/* 路线容器 */
.routes-container {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 12px;
  padding: 16px;
  min-height: 400px;
}

.container-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.routes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 600px;
  overflow-y: auto;
}

.route-card {
  padding: 16px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 10px;
}

.route-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.route-index {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #00d4ff;
  color: #000;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
}

.route-vehicle {
  font-size: 14px;
  font-weight: 600;
}

.route-score {
  margin-left: auto;
  font-size: 12px;
  color: #ffd93d;
}

.route-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.route-stat {
  display: flex;
  flex-direction: column;
}

.route-stat .stat-label {
  font-size: 10px;
  color: rgba(255,255,255,0.4);
}

.route-stat .stat-value {
  font-size: 13px;
  font-weight: 600;
}

.route-nodes {
  margin-bottom: 12px;
}

.node-sequence {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: rgba(0, 212, 255, 0.1);
  border-radius: 4px;
  font-size: 11px;
}

.node-type {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
}

.node-type.pickup {
  background: #00ff88;
  color: #000;
}

.node-type.delivery {
  background: #00d4ff;
  color: #000;
}

.node-address {
  color: rgba(255,255,255,0.7);
}

.route-tips {
  margin-bottom: 12px;
}

.tip-item {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
  padding: 4px 0;
}

.cost-breakdown {
  display: flex;
  gap: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.cost-item {
  display: flex;
  flex-direction: column;
}

.cost-label {
  font-size: 10px;
  color: rgba(255,255,255,0.4);
}

.cost-value {
  font-size: 12px;
  font-weight: 500;
}

/* 对比列表 */
.comparison-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.comparison-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
}

.comparison-item.best {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.comparison-rank {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.1);
  border-radius: 6px;
  font-size: 12px;
}

.comparison-content {
  flex: 1;
}

.comparison-name {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
}

.comparison-stats {
  display: flex;
  gap: 12px;
  font-size: 10px;
  color: rgba(255,255,255,0.6);
  margin-bottom: 2px;
}

.comparison-meta {
  font-size: 10px;
  color: rgba(255,255,255,0.4);
}

/* 成本估算器 */
.cost-estimator {
  padding: 8px 0;
}

.estimated-cost {
  margin-top: 16px;
  padding: 16px;
  background: rgba(0, 255, 136, 0.1);
  border-radius: 8px;
  text-align: center;
}

.cost-total {
  font-size: 28px;
  font-weight: 700;
  color: #00ff88;
  margin-bottom: 8px;
}

.cost-detail {
  display: flex;
  justify-content: center;
  gap: 16px;
  font-size: 11px;
  color: rgba(255,255,255,0.6);
}

/* 历史列表 */
.history-list {
  max-height: 200px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.history-time {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
}

.history-info {
  display: flex;
  gap: 12px;
  font-size: 11px;
}

.history-algo {
  color: #00d4ff;
}

.history-result {
  color: #00ff88;
}

/* 合并详情 */
.merge-detail {
  padding: 8px 0;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.detail-label {
  color: rgba(255,255,255,0.6);
}

.detail-value {
  font-weight: 600;
}

.detail-value.highlight {
  color: #00ff88;
  font-size: 18px;
}

.detail-section {
  margin-top: 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
}

.order-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.order-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 6px;
  font-size: 12px;
}

.order-number {
  color: #00d4ff;
}

.order-customer {
  color: rgba(255,255,255,0.7);
}

.order-weight {
  color: rgba(255,255,255,0.5);
}

/* Element Plus 覆盖 */
:deep(.el-select .el-input__wrapper) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
}

:deep(.el-select .el-input__inner) {
  color: #fff;
}

:deep(.el-slider__runway) {
  background: rgba(0, 212, 255, 0.2);
}

:deep(.el-slider__bar) {
  background: linear-gradient(90deg, #00d4ff, #00ff88);
}

:deep(.el-slider__button) {
  border-color: #00ff88;
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-input-number .el-input__wrapper) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
}

:deep(.el-input-number .el-input__inner) {
  color: #fff;
}

:deep(.el-switch.is-checked .el-switch__core) {
  background: #00ff88;
  border-color: #00ff88;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #00d4ff, #00ff88);
  border: none;
  color: #000;
}

:deep(.el-button--success) {
  background: linear-gradient(135deg, #00ff88, #00d4ff);
  border: none;
  color: #000;
}

:deep(.el-tag) {
  background: rgba(0, 212, 255, 0.2);
  border-color: rgba(0, 212, 255, 0.3);
  color: #00d4ff;
}

:deep(.el-empty__description p) {
  color: rgba(255,255,255,0.4);
}
</style>