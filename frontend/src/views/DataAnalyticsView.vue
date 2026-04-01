<template>
  <div class="data-analytics-page">
    <!-- 背景动效 -->
    <div class="bg-effects">
      <div class="grid-lines"></div>
    </div>

    <!-- 顶部标题 -->
    <div class="page-header">
      <h1 class="glow-title">📊 数据分析中心</h1>
      <span class="subtitle">DATA ANALYTICS CENTER</span>
    </div>

    <!-- 功能标签页 -->
    <el-tabs v-model="activeTab" class="analytics-tabs">
      
      <!-- ========== 综合仪表盘 ========== -->
      <el-tab-pane label="📈 综合仪表盘" name="dashboard">
        <div class="dashboard-grid">
          <!-- 预测性维护卡片 -->
          <div class="dash-card">
            <div class="card-header">
              <span class="card-icon">🔧</span>
              <span class="card-title">预测性维护</span>
            </div>
            <div class="card-metric">
              <span class="metric-value">{{ dashboard.predictive_maintenance?.high_risk_count || 0 }}</span>
              <span class="metric-label">高风险路线</span>
            </div>
            <div class="card-list">
              <div v-for="p in dashboard.predictive_maintenance?.predictions?.slice(0,3)" :key="p.route_id" class="list-item">
                <span>{{ p.route_name }}</span>
                <el-tag size="small" :type="p.congestion_probability > 0.6 ? 'danger' : 'success'">
                  {{ (p.congestion_probability * 100).toFixed(0) }}%
                </el-tag>
              </div>
            </div>
          </div>

          <!-- 客户画像卡片 -->
          <div class="dash-card">
            <div class="card-header">
              <span class="card-icon">👥</span>
              <span class="card-title">客户画像</span>
            </div>
            <div class="card-metric">
              <span class="metric-value">{{ dashboard.customer_analysis?.high_value_count || 0 }}</span>
              <span class="metric-label">高价值客户</span>
            </div>
            <div class="card-stats">
              <div class="stat-item">
                <span class="stat-label">总数</span>
                <span class="stat-value">{{ dashboard.customer_analysis?.total_customers || 0 }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">满意度</span>
                <span class="stat-value">{{ (dashboard.customer_analysis?.avg_satisfaction * 100 || 0).toFixed(0) }}%</span>
              </div>
            </div>
          </div>

          <!-- 供应链卡片 -->
          <div class="dash-card">
            <div class="card-header">
              <span class="card-icon">🔗</span>
              <span class="card-title">供应链</span>
            </div>
            <div class="card-metric">
              <span class="metric-value">{{ dashboard.supply_chain?.fulfillment_rate || 0 }}%</span>
              <span class="metric-label">履约率</span>
            </div>
            <div class="card-stats">
              <div class="stat-item">
                <span class="stat-label">准时交付</span>
                <span class="stat-value">{{ ((dashboard.supply_chain?.on_time_delivery || 0) * 100).toFixed(0) }}%</span>
              </div>
            </div>
            <div class="bottleneck-warning" v-if="dashboard.supply_chain?.bottleneck_nodes?.length">
              ⚠️ 瓶颈: {{ dashboard.supply_chain.bottleneck_nodes.join(', ') }}
            </div>
          </div>

          <!-- 碳足迹卡片 -->
          <div class="dash-card green">
            <div class="card-header">
              <span class="card-icon">🌱</span>
              <span class="card-title">碳足迹</span>
            </div>
            <div class="card-metric">
              <span class="metric-value">{{ dashboard.carbon_footprint?.total_emission_kg || 0 }}</span>
              <span class="metric-label">总排放 (kg CO2)</span>
            </div>
            <div class="saving-info">
              💡 可减排 {{ dashboard.carbon_footprint?.potential_saving_kg || 0 }} kg
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ========== 预测性维护 ========== -->
      <el-tab-pane label="🔧 预测性维护" name="predictive">
        <div class="tab-content">
          <div class="section-header">
            <span>路线拥堵预测</span>
            <el-button type="primary" size="small" @click="loadPredictiveData" :loading="loadingPredictive">
              刷新预测
            </el-button>
          </div>

          <div class="prediction-list">
            <div v-for="pred in trafficPredictions" :key="pred.route_id" class="prediction-item">
              <div class="pred-header">
                <span class="route-name">{{ pred.route_name }}</span>
                <el-tag :type="getStatusType(pred.current_status)">
                  {{ getStatusText(pred.current_status) }}
                </el-tag>
              </div>
              <div class="pred-body">
                <div class="prob-bar">
                  <div class="prob-fill" :style="{ width: (pred.congestion_probability * 100) + '%' }"></div>
                </div>
                <span class="prob-text">拥堵概率: {{ (pred.congestion_probability * 100).toFixed(0) }}%</span>
              </div>
              <div class="pred-footer">
                <span class="recommendation">{{ pred.recommendation }}</span>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ========== 客户画像 ========== -->
      <el-tab-pane label="👥 客户画像" name="customers">
        <div class="tab-content">
          <div class="section-header">
            <span>客户价值分析</span>
          </div>

          <!-- 价值分布 -->
          <div class="value-distribution">
            <div class="dist-item high">
              <span class="dist-count">{{ customerData.value_distribution?.high || 0 }}</span>
              <span class="dist-label">高价值</span>
            </div>
            <div class="dist-item medium">
              <span class="dist-count">{{ customerData.value_distribution?.medium || 0 }}</span>
              <span class="dist-label">中价值</span>
            </div>
            <div class="dist-item low">
              <span class="dist-count">{{ customerData.value_distribution?.low || 0 }}</span>
              <span class="dist-label">低价值</span>
            </div>
          </div>

          <!-- 客户列表 -->
          <div class="customer-list">
            <div v-for="profile in customerData.profiles?.slice(0, 10)" :key="profile.customer_id" class="customer-item">
              <div class="customer-header">
                <span class="customer-name">{{ profile.customer_name }}</span>
                <el-tag size="small" :type="getValueType(profile.value_level)">
                  {{ getValueText(profile.value_level) }}
                </el-tag>
              </div>
              <div class="customer-metrics">
                <div class="cm-item">
                  <span class="cm-label">订单数</span>
                  <span class="cm-value">{{ profile.total_orders }}</span>
                </div>
                <div class="cm-item">
                  <span class="cm-label">总收入</span>
                  <span class="cm-value">¥{{ profile.total_revenue }}</span>
                </div>
                <div class="cm-item">
                  <span class="cm-label">满意度</span>
                  <span class="cm-value">{{ (profile.satisfaction_score * 100).toFixed(0) }}%</span>
                </div>
              </div>
              <div class="customer-recs" v-if="profile.recommendations?.length">
                <span v-for="rec in profile.recommendations.slice(0, 2)" :key="rec" class="rec-tag">
                  {{ rec }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ========== 供应链可视化 ========== -->
      <el-tab-pane label="🔗 供应链" name="supply-chain">
        <div class="tab-content">
          <div class="section-header">
            <span>供应链网络</span>
          </div>

          <!-- 指标卡片 -->
          <div class="sc-metrics">
            <div class="sc-metric-card">
              <span class="sc-value">{{ supplyChainData.metrics?.fulfillment_rate || 0 }}%</span>
              <span class="sc-label">履约率</span>
            </div>
            <div class="sc-metric-card">
              <span class="sc-value">{{ ((supplyChainData.metrics?.on_time_delivery || 0) * 100).toFixed(0) }}%</span>
              <span class="sc-label">准时交付</span>
            </div>
            <div class="sc-metric-card">
              <span class="sc-value">{{ supplyChainData.metrics?.avg_lead_time || '-' }} 天</span>
              <span class="sc-label">平均提前期</span>
            </div>
            <div class="sc-metric-card">
              <span class="sc-value">{{ supplyChainData.metrics?.total_nodes || 0 }}</span>
              <span class="sc-label">节点数</span>
            </div>
          </div>

          <!-- 节点列表 -->
          <div class="sc-nodes">
            <div class="node-header">
              <span>节点状态</span>
            </div>
            <div class="node-grid">
              <div v-for="node in supplyChainData.chain?.nodes?.slice(0, 8)" :key="node.id" class="node-card">
                <div class="node-type">{{ node.type }}</div>
                <div class="node-name">{{ node.name }}</div>
                <div class="node-status" :class="node.status">{{ node.status }}</div>
                <div class="node-perf">绩效: {{ (node.performance * 100).toFixed(0) }}%</div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ========== 碳足迹 ========== -->
      <el-tab-pane label="🌱 碳足迹" name="carbon">
        <div class="tab-content">
          <div class="section-header">
            <span>碳排放计算器</span>
          </div>

          <!-- 计算器 -->
          <div class="carbon-calculator">
            <div class="calc-row">
              <div class="calc-field">
                <label>距离 (km)</label>
                <el-input-number v-model="carbonParams.distance" :min="1" :max="5000" />
              </div>
              <div class="calc-field">
                <label>车辆类型</label>
                <el-select v-model="carbonParams.vehicle_type">
                  <el-option value="small" label="小型车" />
                  <el-option value="medium" label="中型车" />
                  <el-option value="large" label="大型车" />
                  <el-option value="heavy" label="重型车" />
                </el-select>
              </div>
              <div class="calc-field">
                <label>燃料类型</label>
                <el-select v-model="carbonParams.fuel_type">
                  <el-option value="diesel" label="柴油" />
                  <el-option value="gasoline" label="汽油" />
                  <el-option value="electric" label="电动" />
                  <el-option value="hybrid" label="混合动力" />
                </el-select>
              </div>
              <el-button type="success" @click="calculateCarbonFootprint">计算</el-button>
            </div>
          </div>

          <!-- 计算结果 -->
          <div class="carbon-result" v-if="carbonResult">
            <div class="result-main">
              <div class="emission-display">
                <span class="emission-value">{{ carbonResult.co2_emission_kg }}</span>
                <span class="emission-unit">kg CO2</span>
              </div>
              <div class="emission-rate">{{ carbonResult.emission_per_km }} kg/km</div>
            </div>
            <div class="green-alt" v-if="carbonResult.green_alternative">
              <div class="alt-header">💡 绿色替代方案</div>
              <div class="alt-info">
                改用 <strong>{{ getFuelName(carbonResult.green_alternative.fuel_type) }}</strong>
                可减少 <span class="saving">{{ carbonResult.green_alternative.saving_percent }}%</span> 排放
              </div>
            </div>
          </div>

          <!-- 碳足迹报告 -->
          <div class="carbon-report">
            <div class="report-header">📊 碳足迹总览</div>
            <div class="report-stats">
              <div class="report-stat">
                <span class="stat-value">{{ carbonReport.summary?.total_emission_kg || 0 }} kg</span>
                <span class="stat-label">总排放</span>
              </div>
              <div class="report-stat">
                <span class="stat-value">{{ carbonReport.summary?.potential_saving_kg || 0 }} kg</span>
                <span class="stat-label">可减排</span>
              </div>
              <div class="report-stat">
                <span class="stat-value">{{ carbonReport.summary?.avg_emission_per_order || 0 }} kg</span>
                <span class="stat-label">平均每单</span>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getAnalyticsDashboard,
  getPredictiveMaintenance,
  getCustomerProfiles,
  getSupplyChain,
  getCarbonFootprint,
  calculateCarbon
} from '@/api/dataAnalytics'

// Tab 状态
const activeTab = ref('dashboard')

// 仪表盘数据
const dashboard = ref({
  predictive_maintenance: {},
  customer_analysis: {},
  supply_chain: {},
  carbon_footprint: {}
})

// 预测性维护
const loadingPredictive = ref(false)
const trafficPredictions = ref([])

// 客户画像
const customerData = ref({
  profiles: [],
  value_distribution: {},
  summary: {}
})

// 供应链
const supplyChainData = ref({
  chain: { nodes: [], connections: [] },
  metrics: {}
})

// 碳足迹
const carbonParams = ref({
  distance: 100,
  vehicle_type: 'medium',
  fuel_type: 'diesel'
})
const carbonResult = ref(null)
const carbonReport = ref({ summary: {} })

// 加载仪表盘
const loadDashboard = async () => {
  try {
    const res = await getAnalyticsDashboard()
    if (res.success) {
      dashboard.value = res.dashboard
    }
  } catch (e) {
    // 使用模拟数据
    dashboard.value = {
      predictive_maintenance: { high_risk_count: 2, predictions: [] },
      customer_analysis: { high_value_count: 5, total_customers: 50, avg_satisfaction: 0.85 },
      supply_chain: { fulfillment_rate: 92, on_time_delivery: 0.88, bottleneck_nodes: ['北京仓库'] },
      carbon_footprint: { total_emission_kg: 1250, potential_saving_kg: 350 }
    }
  }
}

// 加载预测数据
const loadPredictiveData = async () => {
  loadingPredictive.value = true
  try {
    const res = await getPredictiveMaintenance()
    if (res.success) {
      trafficPredictions.value = res.data.traffic_predictions
    }
  } catch (e) {
    trafficPredictions.value = [
      { route_id: 1, route_name: '北京-上海', current_status: 'moderate', congestion_probability: 0.45, recommendation: '路况一般，建议预留额外时间' },
      { route_id: 2, route_name: '上海-广州', current_status: 'heavy', congestion_probability: 0.72, recommendation: '建议避开该路段' },
      { route_id: 3, route_name: '广州-深圳', current_status: 'light', congestion_probability: 0.18, recommendation: '路况良好，适合通行' }
    ]
  } finally {
    loadingPredictive.value = false
  }
}

// 加载客户数据
const loadCustomerData = async () => {
  try {
    const res = await getCustomerProfiles()
    if (res.success) {
      customerData.value = res.data
    }
  } catch (e) {
    customerData.value = {
      profiles: [
        { customer_id: 1, customer_name: '客户A', value_level: 'high', total_orders: 25, total_revenue: 15000, satisfaction_score: 0.92 },
        { customer_id: 2, customer_name: '客户B', value_level: 'medium', total_orders: 12, total_revenue: 6500, satisfaction_score: 0.78 }
      ],
      value_distribution: { high: 5, medium: 15, low: 30 },
      summary: { total_customers: 50, high_value_count: 5, avg_satisfaction: 0.82 }
    }
  }
}

// 加载供应链数据
const loadSupplyChainData = async () => {
  try {
    const res = await getSupplyChain()
    if (res.success) {
      supplyChainData.value = res.data
    }
  } catch (e) {
    supplyChainData.value = {
      chain: {
        nodes: [
          { id: 1, name: '北京仓库', type: 'warehouse', status: 'active', performance: 0.92 },
          { id: 2, name: '上海仓库', type: 'warehouse', status: 'active', performance: 0.88 },
          { id: 3, name: '广州配送站', type: 'distribution', status: 'active', performance: 0.95 }
        ]
      },
      metrics: { fulfillment_rate: 92, on_time_delivery: 0.88, avg_lead_time: 2.5, total_nodes: 5 }
    }
  }
}

// 加载碳足迹
const loadCarbonReport = async () => {
  try {
    const res = await getCarbonFootprint()
    if (res.success) {
      carbonReport.value = res.data
    }
  } catch (e) {
    carbonReport.value = {
      summary: { total_emission_kg: 1250, potential_saving_kg: 350, avg_emission_per_order: 25 }
    }
  }
}

// 计算碳足迹
const calculateCarbonFootprint = async () => {
  try {
    const res = await calculateCarbon(carbonParams.value)
    if (res.success) {
      carbonResult.value = res.footprint
    }
  } catch (e) {
    // 模拟计算
    const emission = carbonParams.value.distance * 0.12 * 
      { small: 0.7, medium: 1.0, large: 1.3, heavy: 1.8 }[carbonParams.value.vehicle_type]
    carbonResult.value = {
      co2_emission_kg: Math.round(emission * 100) / 100,
      emission_per_km: 0.12,
      green_alternative: { fuel_type: 'electric', saving_percent: 58 }
    }
  }
}

// 辅助函数
const getStatusType = (status) => {
  const types = { light: 'success', moderate: 'warning', heavy: 'danger', severe: 'danger' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = { light: '畅通', moderate: '一般', heavy: '拥堵', severe: '严重拥堵' }
  return texts[status] || status
}

const getValueType = (level) => {
  const types = { high: 'danger', medium: 'warning', low: 'info' }
  return types[level] || 'info'
}

const getValueText = (level) => {
  const texts = { high: '高价值', medium: '中价值', low: '低价值' }
  return texts[level] || level
}

const getFuelName = (type) => {
  const names = { electric: '电动车', hybrid: '混合动力', diesel: '柴油车', gasoline: '汽油车' }
  return names[type] || type
}

onMounted(async () => {
  await loadDashboard()
  await loadPredictiveData()
  await loadCustomerData()
  await loadSupplyChainData()
  await loadCarbonReport()
  await calculateCarbonFootprint()
})
</script>

<style scoped>
.data-analytics-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #0d1033 100%);
  padding: 16px;
  color: #fff;
  position: relative;
}

.bg-effects {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.grid-lines {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
}

.page-header {
  text-align: center;
  margin-bottom: 16px;
  padding: 16px;
}

.glow-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(90deg, #00ff88, #00d4ff, #a855f7);
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

/* Tabs */
.analytics-tabs {
  background: rgba(0, 212, 255, 0.05);
  border-radius: 12px;
  padding: 12px;
}

:deep(.el-tabs__item.is-active) {
  color: #00ff88;
}

.tab-content {
  padding: 12px 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-size: 14px;
  font-weight: 600;
}

/* Dashboard Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.dash-card {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 12px;
  padding: 16px;
}

.dash-card.green {
  background: rgba(0, 255, 136, 0.05);
  border-color: rgba(0, 255, 136, 0.15);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.card-icon {
  font-size: 20px;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
}

.card-metric {
  text-align: center;
  margin-bottom: 12px;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #00ff88;
}

.metric-label {
  display: block;
  font-size: 11px;
  color: rgba(255,255,255,0.5);
}

.card-stats {
  display: flex;
  justify-content: space-around;
  margin-top: 8px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
}

.card-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.bottleneck-warning {
  margin-top: 8px;
  padding: 8px;
  background: rgba(255, 217, 61, 0.1);
  border-radius: 6px;
  font-size: 11px;
  color: #ffd93d;
}

.saving-info {
  text-align: center;
  font-size: 12px;
  color: #00ff88;
}

/* Prediction List */
.prediction-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.prediction-item {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  padding: 12px;
}

.pred-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.route-name {
  font-weight: 600;
}

.prob-bar {
  height: 8px;
  background: rgba(255,255,255,0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 4px;
}

.prob-fill {
  height: 100%;
  background: linear-gradient(90deg, #00ff88, #ffd93d, #ff6b6b);
  transition: width 0.3s;
}

.prob-text {
  font-size: 12px;
  color: rgba(255,255,255,0.7);
}

.pred-footer {
  margin-top: 8px;
  font-size: 11px;
  color: rgba(255,255,255,0.6);
}

/* Value Distribution */
.value-distribution {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.dist-item {
  flex: 1;
  text-align: center;
  padding: 16px;
  border-radius: 8px;
}

.dist-item.high { background: rgba(255, 107, 107, 0.2); }
.dist-item.medium { background: rgba(255, 217, 61, 0.2); }
.dist-item.low { background: rgba(0, 212, 255, 0.2); }

.dist-count {
  display: block;
  font-size: 24px;
  font-weight: 700;
}

.dist-label {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
}

/* Customer List */
.customer-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.customer-item {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  padding: 12px;
}

.customer-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.customer-name {
  font-weight: 600;
}

.customer-metrics {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
}

.cm-item {
  display: flex;
  flex-direction: column;
}

.cm-label {
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

.cm-value {
  font-size: 13px;
  font-weight: 600;
}

.customer-recs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.rec-tag {
  font-size: 10px;
  padding: 4px 8px;
  background: rgba(0, 212, 255, 0.1);
  border-radius: 4px;
  color: #00d4ff;
}

/* Supply Chain */
.sc-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.sc-metric-card {
  text-align: center;
  padding: 12px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
}

.sc-value {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #00ff88;
}

.sc-label {
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

.node-header {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
}

.node-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.node-card {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}

.node-type {
  font-size: 10px;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
}

.node-name {
  font-size: 12px;
  font-weight: 600;
  margin: 4px 0;
}

.node-status {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
}

.node-status.active {
  background: rgba(0, 255, 136, 0.2);
  color: #00ff88;
}

.node-perf {
  font-size: 10px;
  color: rgba(255,255,255,0.6);
  margin-top: 4px;
}

/* Carbon Calculator */
.carbon-calculator {
  background: rgba(0, 255, 136, 0.05);
  border: 1px solid rgba(0, 255, 136, 0.15);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.calc-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.calc-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.calc-field label {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
}

.carbon-result {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.result-main {
  text-align: center;
  margin-bottom: 16px;
}

.emission-value {
  font-size: 48px;
  font-weight: 700;
  color: #ff6b6b;
}

.emission-unit {
  font-size: 14px;
  color: rgba(255,255,255,0.6);
}

.emission-rate {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
}

.green-alt {
  background: rgba(0, 255, 136, 0.1);
  border-radius: 8px;
  padding: 12px;
}

.alt-header {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}

.alt-info {
  font-size: 12px;
}

.saving {
  color: #00ff88;
  font-weight: 700;
}

.carbon-report {
  background: rgba(0, 212, 255, 0.05);
  border-radius: 12px;
  padding: 16px;
}

.report-header {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.report-stats {
  display: flex;
  justify-content: space-around;
}

.report-stat {
  text-align: center;
}

.report-stat .stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #00d4ff;
}

.report-stat .stat-label {
  display: block;
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

/* Element Plus Overrides */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #00ff88, #00d4ff);
  border: none;
  color: #000;
}

:deep(.el-button--success) {
  background: linear-gradient(135deg, #00ff88, #00d4ff);
  border: none;
  color: #000;
}

:deep(.el-input__wrapper),
:deep(.el-input-number),
:deep(.el-select) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
}

:deep(.el-input__inner) {
  color: #fff;
}
</style>