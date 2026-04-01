<template>
  <div class="risk-page">
    <!-- 背景动效 -->
    <div class="bg-effects">
      <div class="grid-lines"></div>
      <div class="scan-line"></div>
    </div>

    <!-- 顶部标题栏 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="glow-title">🛡️ 供应链风险管理中心</h1>
        <span class="subtitle">SUPPLY CHAIN RISK MANAGEMENT</span>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="refreshData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card" v-for="(stat, idx) in statsCards" :key="idx" :style="{borderLeftColor: stat.color}">
        <div class="stat-icon">{{ stat.icon }}</div>
        <div class="stat-content">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：卡拉杰克矩阵 -->
      <div class="left-panel">
        <div class="panel-card">
          <div class="card-header">
            <span class="header-icon">📊</span>
            <span class="header-title">卡拉杰克矩阵</span>
          </div>
          
          <!-- 矩阵图 -->
          <div class="kraljic-matrix">
            <div class="matrix-y-axis">
              <span>供应风险</span>
              <span class="arrow">↑</span>
            </div>
            <div class="matrix-container">
              <div class="matrix-grid">
                <!-- 战略项目 -->
                <div class="matrix-cell strategic" @click="showCategoryDetail('strategic')">
                  <div class="cell-title">战略项目</div>
                  <div class="cell-count">{{ kraljicStats.strategic || 0 }}</div>
                  <div class="cell-desc">高利润影响·高供应风险</div>
                </div>
                <!-- 杠杆项目 -->
                <div class="matrix-cell leverage" @click="showCategoryDetail('leverage')">
                  <div class="cell-title">杠杆项目</div>
                  <div class="cell-count">{{ kraljicStats.leverage || 0 }}</div>
                  <div class="cell-desc">高利润影响·低供应风险</div>
                </div>
                <!-- 瓶颈项目 -->
                <div class="matrix-cell bottleneck" @click="showCategoryDetail('bottleneck')">
                  <div class="cell-title">瓶颈项目</div>
                  <div class="cell-count">{{ kraljicStats.bottleneck || 0 }}</div>
                  <div class="cell-desc">低利润影响·高供应风险</div>
                </div>
                <!-- 常规项目 -->
                <div class="matrix-cell routine" @click="showCategoryDetail('routine')">
                  <div class="cell-title">常规项目</div>
                  <div class="cell-count">{{ kraljicStats.routine || 0 }}</div>
                  <div class="cell-desc">低利润影响·低供应风险</div>
                </div>
              </div>
              <div class="matrix-x-axis">
                <span class="arrow">←</span>
                <span>利润影响</span>
                <span class="arrow">→</span>
              </div>
            </div>
          </div>

          <!-- 分类列表 -->
          <div class="category-list">
            <div class="list-header">
              <span>订单分类详情</span>
              <el-tag size="small" type="danger" v-if="kraljicStats.high_risk_count > 0">
                {{ kraljicStats.high_risk_count }} 个高风险
              </el-tag>
            </div>
            <div class="list-content">
              <div 
                v-for="item in kraljicItems.slice(0, 10)" 
                :key="item.item_id" 
                class="list-item"
                :style="{borderLeftColor: item.color}"
              >
                <div class="item-name">{{ item.item_name }}</div>
                <div class="item-scores">
                  <span>利润: {{ item.profit_impact }}%</span>
                  <span>风险: {{ item.supply_risk }}%</span>
                </div>
                <el-tag size="small" :style="{background: item.color, color: '#000'}">
                  {{ getCategoryName(item.category) }}
                </el-tag>
              </div>
              <el-empty v-if="kraljicItems.length === 0" description="暂无数据" :image-size="60" />
            </div>
          </div>
        </div>
      </div>

      <!-- 中间：风险评估矩阵 -->
      <div class="center-panel">
        <div class="panel-card">
          <div class="card-header">
            <span class="header-icon">🎯</span>
            <span class="header-title">风险评估矩阵</span>
          </div>
          
          <!-- 矩阵可视化 -->
          <div class="risk-matrix">
            <div class="matrix-y-axis">
              <span>影响程度</span>
              <span class="arrow">↑</span>
            </div>
            <div class="risk-matrix-container">
              <div class="risk-grid">
                <div 
                  v-for="(row, rowIdx) in riskMatrixData" 
                  :key="rowIdx" 
                  class="risk-row"
                >
                  <div 
                    v-for="(count, colIdx) in row" 
                    :key="colIdx"
                    class="risk-cell"
                    :class="getRiskCellClass(rowIdx, colIdx)"
                  >
                    <span v-if="count > 0" class="cell-count">{{ count }}</span>
                  </div>
                </div>
              </div>
              <div class="matrix-x-axis">
                <span>概率</span>
                <span class="arrow">→</span>
              </div>
            </div>
          </div>

          <!-- 图例 -->
          <div class="risk-legend">
            <div class="legend-item" v-for="(level, idx) in riskLevels" :key="idx">
              <span class="legend-color" :style="{background: level.color}"></span>
              <span class="legend-name">{{ level.name }}</span>
            </div>
          </div>

          <!-- 风险项目列表 -->
          <div class="risk-items">
            <div class="list-header">
              <span>风险项目分布</span>
            </div>
            <div class="risk-item-list">
              <div 
                v-for="item in riskItems.slice(0, 8)" 
                :key="item.id" 
                class="risk-item"
                :class="item.level"
              >
                <span class="item-name">{{ item.name }}</span>
                <span class="item-score">得分: {{ (item.score * 100).toFixed(0) }}</span>
                <el-tag size="small" :type="getRiskTagType(item.level)">
                  {{ getRiskLevelName(item.level) }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：决策工具 -->
      <div class="right-panel">
        <!-- CBA决策计算器 -->
        <div class="panel-card">
          <div class="card-header">
            <span class="header-icon">⚖️</span>
            <span class="header-title">应急决策计算器</span>
            <span class="header-badge">CBA模型</span>
          </div>
          
          <div class="cba-calculator">
            <el-form label-position="top" size="small">
              <el-form-item label="货物价值 (元)">
                <el-input-number v-model="cbaForm.cargo_value" :min="0" :step="10000" style="width: 100%" />
              </el-form-item>
              <el-form-item label="固定损失 (元)">
                <el-input-number v-model="cbaForm.fixed_loss" :min="0" :step="5000" style="width: 100%" />
              </el-form-item>
              <el-form-item label="每日损失 (元/天)">
                <el-input-number v-model="cbaForm.daily_loss" :min="0" :step="1000" style="width: 100%" />
              </el-form-item>
              <el-form-item label="转运成本 (元)">
                <el-input-number v-model="cbaForm.transfer_cost" :min="0" :step="10000" style="width: 100%" />
              </el-form-item>
              <el-form-item label="已等待天数">
                <el-input-number v-model="cbaForm.waiting_days" :min="0" :max="365" style="width: 100%" />
              </el-form-item>
            </el-form>
            
            <el-button type="primary" style="width: 100%" @click="calculateCBADecision" :loading="cbaLoading">
              计算决策
            </el-button>
            
            <!-- 计算结果 -->
            <div class="cba-result" v-if="cbaResult">
              <div class="result-header">
                <el-icon :size="24"><WarningFilled v-if="cbaResult.scenario === 'transfer'" /><CircleCheckFilled v-else /></el-icon>
                <span>{{ cbaResult.scenario === 'transfer' ? '建议转运' : '可继续等待' }}</span>
              </div>
              <div class="result-detail">
                <div class="detail-row">
                  <span>等待成本</span>
                  <span class="value">¥{{ cbaResult.wait_cost.toLocaleString() }}</span>
                </div>
                <div class="detail-row">
                  <span>转运成本</span>
                  <span class="value">¥{{ cbaResult.transfer_cost.toLocaleString() }}</span>
                </div>
                <div class="detail-row highlight">
                  <span>临界天数</span>
                  <span class="value">{{ cbaResult.critical_days }} 天</span>
                </div>
              </div>
              <div class="result-recommendation">
                {{ cbaResult.recommendation }}
              </div>
            </div>
          </div>
        </div>

        <!-- AWRP成本估算器 -->
        <div class="panel-card">
          <div class="card-header">
            <span class="header-icon">💰</span>
            <span class="header-title">AWRP成本估算器</span>
            <span class="header-badge">战争附加费</span>
          </div>
          
          <div class="awrp-calculator">
            <el-form label-position="top" size="small">
              <el-form-item label="货物价值 (美元)">
                <el-input-number v-model="awrpForm.cargo_value" :min="0" :step="100000" style="width: 100%" />
              </el-form-item>
              <el-form-item label="危机区域">
                <el-select v-model="awrpForm.zone" style="width: 100%">
                  <el-option 
                    v-for="zone in crisisZones" 
                    :key="zone.code" 
                    :label="zone.name" 
                    :value="zone.code"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="危机状态">
                <el-switch v-model="awrpForm.is_crisis" active-text="危机中" inactive-text="正常" />
              </el-form-item>
            </el-form>
            
            <el-button type="primary" style="width: 100%" @click="estimateAWRPCost" :loading="awrpLoading">
              估算成本
            </el-button>
            
            <!-- 估算结果 -->
            <div class="awrp-result" v-if="awrpResult">
              <div class="result-row">
                <span>基础费率</span>
                <span class="value">{{ (awrpResult.base_awrp_rate * 100).toFixed(2) }}%</span>
              </div>
              <div class="result-row">
                <span>当前费率</span>
                <span class="value danger">{{ (awrpResult.current_awrp_rate * 100).toFixed(2) }}%</span>
              </div>
              <div class="result-row">
                <span>危机前保险费</span>
                <span class="value">${{ awrpResult.insurance_cost_before.toLocaleString() }}</span>
              </div>
              <div class="result-row highlight">
                <span>危机后保险费</span>
                <span class="value danger">${{ awrpResult.insurance_cost_after.toLocaleString() }}</span>
              </div>
              <div class="result-row">
                <span>成本增长倍数</span>
                <span class="value danger">×{{ awrpResult.cost_increase_ratio }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 路线对比 -->
        <div class="panel-card">
          <div class="card-header">
            <span class="header-icon">🔄</span>
            <span class="header-title">路线成本对比</span>
          </div>
          
          <div class="route-compare">
            <el-form label-position="top" size="small">
              <el-form-item label="货物价值 (美元)">
                <el-input-number v-model="compareForm.cargo_value" :min="0" :step="100000" style="width: 100%" />
              </el-form-item>
              <div class="compare-routes">
                <div class="route-input">
                  <div class="route-label">路线A：穿越风险区域</div>
                  <el-input-number v-model="compareForm.route_a.base_cost" placeholder="基础运费" size="small" style="width: 100%; margin-bottom: 8px" />
                  <el-input-number v-model="compareForm.route_a.extra_days" placeholder="额外天数" size="small" style="width: 100%" />
                </div>
                <div class="route-input">
                  <div class="route-label">路线B：绕行方案</div>
                  <el-input-number v-model="compareForm.route_b.base_cost" placeholder="基础运费" size="small" style="width: 100%; margin-bottom: 8px" />
                  <el-input-number v-model="compareForm.route_b.extra_fuel" placeholder="额外燃油" size="small" style="width: 100%; margin-bottom: 8px" />
                  <el-input-number v-model="compareForm.route_b.extra_days" placeholder="额外天数" size="small" style="width: 100%" />
                </div>
              </div>
            </el-form>
            
            <el-button type="success" style="width: 100%" @click="compareRoutes" :loading="compareLoading">
              对比计算
            </el-button>
            
            <!-- 对比结果 -->
            <div class="compare-result" v-if="compareResult">
              <div class="result-route" :class="{ recommended: compareResult.route_a.total_cost < compareResult.route_b.total_cost }">
                <div class="route-name">{{ compareResult.route_a.name }}</div>
                <div class="route-cost">${{ compareResult.route_a.total_cost.toLocaleString() }}</div>
                <el-tag v-if="compareResult.route_a.total_cost < compareResult.route_b.total_cost" type="success" size="small">推荐</el-tag>
              </div>
              <div class="result-route" :class="{ recommended: compareResult.route_b.total_cost < compareResult.route_a.total_cost }">
                <div class="route-name">{{ compareResult.route_b.name }}</div>
                <div class="route-cost">${{ compareResult.route_b.total_cost.toLocaleString() }}</div>
                <el-tag v-if="compareResult.route_b.total_cost < compareResult.route_a.total_cost" type="success" size="small">推荐</el-tag>
              </div>
              <div class="compare-recommendation">
                {{ compareResult.recommendation }}
                <br>节省: ${{ compareResult.saving.toLocaleString() }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Refresh, WarningFilled, CircleCheckFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  getRiskDashboard,
  getClassifiedOrders,
  getRiskMatrix,
  calculateCBA,
  estimateAWRP,
  compareAWRPRoutes,
  getCrisisZones
} from '@/api/risk'

// 状态
const loading = ref(false)

// 卡拉杰克矩阵
const kraljicItems = ref([])
const kraljicStats = ref({})
const categoryNames = {
  strategic: '战略项目',
  leverage: '杠杆项目',
  bottleneck: '瓶颈项目',
  routine: '常规项目'
}

// 风险矩阵
const riskMatrixData = ref([[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0],[0,0,0,0,0]])
const riskItems = ref([])
const riskLevels = ref([
  { id: 'critical', name: '关键风险', color: '#FF0000' },
  { id: 'high', name: '重大风险', color: '#FF6B6B' },
  { id: 'medium', name: '一般风险', color: '#FFE66D' },
  { id: 'low', name: '可接受风险', color: '#95E1D3' }
])
const crisisZones = ref([])

// 统计卡片
const statsCards = computed(() => [
  { icon: '📦', label: '总订单', value: kraljicStats.value.total || 0, color: '#00d4ff' },
  { icon: '⚠️', label: '高风险', value: kraljicStats.value.high_risk_count || 0, color: '#ff6b6b' },
  { icon: '📊', label: '平均利润影响', value: `${kraljicStats.value.avg_profit_impact || 0}%`, color: '#00ff88' },
  { icon: '🎯', label: '平均供应风险', value: `${kraljicStats.value.avg_supply_risk || 0}%`, color: '#ffd93d' }
])

// CBA表单
const cbaForm = reactive({
  cargo_value: 5000000,
  fixed_loss: 200000,
  daily_loss: 50000,
  transfer_cost: 1200000,
  waiting_days: 0
})
const cbaLoading = ref(false)
const cbaResult = ref(null)

// AWRP表单
const awrpForm = reactive({
  cargo_value: 10000000,
  zone: 'hormuz',
  is_crisis: true
})
const awrpLoading = ref(false)
const awrpResult = ref(null)

// 路线对比表单
const compareForm = reactive({
  cargo_value: 20000000,
  route_a: {
    base_cost: 500000,
    zone: 'hormuz',
    is_crisis: true,
    extra_days: 0,
    daily_time_cost: 5000
  },
  route_b: {
    base_cost: 800000,
    extra_fuel: 200000,
    extra_days: 20,
    daily_time_cost: 5000
  }
})
const compareLoading = ref(false)
const compareResult = ref(null)

// 获取数据
const refreshData = async () => {
  loading.value = true
  try {
    const [dashboardRes, ordersRes, matrixRes, zonesRes] = await Promise.all([
      getRiskDashboard(),
      getClassifiedOrders(),
      getRiskMatrix(),
      getCrisisZones()
    ])
    
    if (dashboardRes.success) {
      kraljicStats.value = dashboardRes.kraljic_matrix?.statistics || {}
    }
    
    if (ordersRes.success) {
      kraljicItems.value = ordersRes.items || []
    }
    
    if (matrixRes.success) {
      riskMatrixData.value = matrixRes.matrix || riskMatrixData.value
      riskItems.value = matrixRes.items || []
    }
    
    if (zonesRes.success) {
      crisisZones.value = zonesRes.zones || []
    }
    
    ElMessage.success('数据已刷新')
  } catch (e) {
    ElMessage.error('数据加载失败')
  } finally {
    loading.value = false
  }
}

// 计算CBA
const calculateCBADecision = async () => {
  cbaLoading.value = true
  try {
    const res = await calculateCBA(cbaForm)
    if (res.success) {
      cbaResult.value = res.decision
    }
  } catch (e) {
    ElMessage.error('计算失败')
  } finally {
    cbaLoading.value = false
  }
}

// 估算AWRP
const estimateAWRPCost = async () => {
  awrpLoading.value = true
  try {
    const res = await estimateAWRP(awrpForm)
    if (res.success) {
      awrpResult.value = res.estimate
    }
  } catch (e) {
    ElMessage.error('估算失败')
  } finally {
    awrpLoading.value = false
  }
}

// 对比路线
const compareRoutes = async () => {
  compareLoading.value = true
  try {
    const res = await compareAWRPRoutes(compareForm)
    if (res.success) {
      compareResult.value = res
    }
  } catch (e) {
    ElMessage.error('对比失败')
  } finally {
    compareLoading.value = false
  }
}

// 辅助方法
const getCategoryName = (category) => categoryNames[category] || category

const getRiskCellClass = (row, col) => {
  const score = row * 0.2 + col * 0.2
  if (score >= 0.64) return 'critical'
  if (score >= 0.36) return 'high'
  if (score >= 0.16) return 'medium'
  return 'low'
}

const getRiskTagType = (level) => {
  const types = { critical: 'danger', high: 'warning', medium: 'info', low: 'success' }
  return types[level] || 'info'
}

const getRiskLevelName = (level) => {
  const names = { critical: '关键', high: '重大', medium: '一般', low: '低' }
  return names[level] || level
}

const showCategoryDetail = (category) => {
  const count = kraljicStats.value[category] || 0
  const name = categoryNames[category]
  ElMessage.info(`${name}: ${count} 个订单`)
}

onMounted(() => {
  refreshData()
})
</script>

<style scoped>
.risk-page {
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
  border-left-width: 4px;
  border-radius: 8px;
}

.stat-icon {
  font-size: 28px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
}

.stat-label {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
}

/* 主内容 */
.main-content {
  display: grid;
  grid-template-columns: 320px 1fr 340px;
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
  font-size: 18px;
}

.header-title {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
}

.header-badge {
  font-size: 10px;
  padding: 2px 8px;
  background: rgba(255, 217, 61, 0.2);
  border-radius: 10px;
  color: #ffd93d;
}

/* 卡拉杰克矩阵 */
.kraljic-matrix {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.matrix-y-axis {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  width: 20px;
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

.matrix-container {
  flex: 1;
}

.matrix-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 4px;
  height: 200px;
}

.matrix-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.matrix-cell:hover {
  transform: scale(1.02);
}

.matrix-cell.strategic { background: rgba(255, 107, 107, 0.3); }
.matrix-cell.leverage { background: rgba(78, 205, 196, 0.3); }
.matrix-cell.bottleneck { background: rgba(255, 230, 109, 0.3); }
.matrix-cell.routine { background: rgba(149, 225, 211, 0.3); }

.cell-title {
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 4px;
}

.cell-count {
  font-size: 24px;
  font-weight: 700;
}

.cell-desc {
  font-size: 9px;
  color: rgba(255,255,255,0.6);
  text-align: center;
  margin-top: 4px;
}

.matrix-x-axis {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

.arrow {
  font-size: 12px;
}

/* 分类列表 */
.category-list {
  margin-top: 16px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 13px;
  font-weight: 600;
}

.list-content {
  max-height: 200px;
  overflow-y: auto;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  margin-bottom: 4px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 6px;
  border-left-width: 3px;
  border-left-style: solid;
}

.item-name {
  flex: 1;
  font-size: 12px;
}

.item-scores {
  display: flex;
  flex-direction: column;
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

/* 风险矩阵 */
.risk-matrix {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.risk-matrix-container {
  flex: 1;
}

.risk-grid {
  display: flex;
  flex-direction: column;
  gap: 2px;
  height: 180px;
}

.risk-row {
  display: flex;
  gap: 2px;
  flex: 1;
}

.risk-cell {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.3s;
}

.risk-cell.critical { background: rgba(255, 0, 0, 0.4); }
.risk-cell.high { background: rgba(255, 107, 107, 0.3); }
.risk-cell.medium { background: rgba(255, 230, 109, 0.2); }
.risk-cell.low { background: rgba(149, 225, 211, 0.15); }

.cell-count {
  font-size: 14px;
  font-weight: 700;
}

/* 图例 */
.risk-legend {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

/* 风险项目 */
.risk-items {
  margin-top: 16px;
}

.risk-item-list {
  max-height: 150px;
  overflow-y: auto;
}

.risk-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  margin-bottom: 4px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 6px;
}

.risk-item.critical { border-left: 3px solid #FF0000; }
.risk-item.high { border-left: 3px solid #FF6B6B; }
.risk-item.medium { border-left: 3px solid #FFE66D; }
.risk-item.low { border-left: 3px solid #95E1D3; }

.risk-item .item-name {
  flex: 1;
  font-size: 12px;
}

.risk-item .item-score {
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

/* CBA计算器 */
.cba-calculator, .awrp-calculator, .route-compare {
  padding: 8px 0;
}

.cba-result, .awrp-result, .compare-result {
  margin-top: 16px;
  padding: 16px;
  background: rgba(0, 212, 255, 0.1);
  border-radius: 8px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #ffd93d;
}

.result-detail {
  margin-bottom: 12px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
}

.detail-row.highlight {
  background: rgba(255, 217, 61, 0.1);
  border-radius: 4px;
  padding: 8px;
  margin: 4px -8px;
}

.detail-row .value {
  font-weight: 600;
}

.result-recommendation {
  font-size: 12px;
  color: rgba(255,255,255,0.7);
  line-height: 1.5;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 212, 255, 0.2);
}

/* AWRP结果 */
.awrp-result .result-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.awrp-result .result-row:last-child {
  border-bottom: none;
}

.awrp-result .value {
  font-weight: 600;
}

.awrp-result .value.danger {
  color: #ff6b6b;
}

/* 路线对比 */
.compare-routes {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
}

.route-input {
  padding: 12px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
}

.route-label {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
  margin-bottom: 8px;
}

.compare-result .result-route {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
  margin-bottom: 8px;
}

.compare-result .result-route.recommended {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.compare-result .route-name {
  flex: 1;
  font-size: 12px;
}

.compare-result .route-cost {
  font-size: 16px;
  font-weight: 700;
}

.compare-recommendation {
  margin-top: 12px;
  padding: 12px;
  background: rgba(0, 255, 136, 0.1);
  border-radius: 8px;
  font-size: 12px;
  color: #00ff88;
  text-align: center;
}

/* Element Plus 覆盖 */
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

:deep(.el-select .el-input__wrapper) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
}

:deep(.el-select .el-input__inner) {
  color: #fff;
}

:deep(.el-switch.is-checked .el-switch__core) {
  background: #ff6b6b;
  border-color: #ff6b6b;
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
</style>