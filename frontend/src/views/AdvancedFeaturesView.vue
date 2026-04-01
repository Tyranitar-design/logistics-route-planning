<template>
  <div class="advanced-features-page">
    <!-- 背景动效 -->
    <div class="bg-effects">
      <div class="grid-lines"></div>
      <div class="particles"></div>
    </div>

    <!-- 顶部标题 -->
    <div class="page-header">
      <h1 class="glow-title">⚡ 高级功能中心</h1>
      <span class="subtitle">ADVANCED FEATURES CENTER</span>
    </div>

    <!-- 功能标签页 -->
    <el-tabs v-model="activeTab" class="feature-tabs">
      
      <!-- ========== 高级预测 ========== -->
      <el-tab-pane label="🧠 高级预测" name="prediction">
        <div class="tab-content">
          <!-- 模型状态 -->
          <div class="status-bar">
            <div class="status-item" :class="modelTrained ? 'trained' : 'untrained'">
              <span class="status-dot"></span>
              <span>{{ modelTrained ? 'LSTM/Prophet 已训练' : '模型未训练' }}</span>
            </div>
            <el-button type="primary" size="small" @click="handleTrainModels" :loading="training">
              <el-icon><Cpu /></el-icon> 训练模型
            </el-button>
          </div>

          <!-- 预测配置 -->
          <div class="config-row">
            <el-select v-model="predictionDays" style="width: 100px" size="small">
              <el-option :value="7" label="7天" />
              <el-option :value="14" label="14天" />
              <el-option :value="30" label="30天" />
            </el-select>
            <el-button type="success" size="small" @click="loadPredictions" :loading="loadingPred">
              🔮 开始预测
            </el-button>
          </div>

          <!-- 预测结果图表 -->
          <div class="charts-grid">
            <div class="chart-card large">
              <div class="card-title">📈 融合预测趋势</div>
              <div ref="predictionChart" class="chart-area"></div>
            </div>
            <div class="chart-card">
              <div class="card-title">🎯 模型对比</div>
              <div ref="modelCompareChart" class="chart-area"></div>
            </div>
          </div>

          <!-- 异常预警 -->
          <div class="alert-section" v-if="anomalies.length > 0">
            <div class="section-title">⚠️ 异常检测预警</div>
            <div class="alert-list">
              <div v-for="(a, i) in anomalies" :key="i" class="alert-item" :class="a.level">
                <span class="alert-icon">{{ a.level === 'critical' ? '🔴' : a.level === 'warning' ? '🟡' : '🔵' }}</span>
                <span class="alert-text">{{ a.message }}</span>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ========== 动态定价 ========== -->
      <el-tab-pane label="💰 动态定价" name="pricing">
        <div class="tab-content">
          <!-- 定价计算器 -->
          <div class="pricing-calculator">
            <div class="calc-title">📊 实时定价计算</div>
            <div class="calc-form">
              <div class="form-row">
                <label>距离 (km)</label>
                <el-input-number v-model="pricingParams.distance" :min="1" :max="5000" size="small" />
              </div>
              <div class="form-row">
                <label>重量 (吨)</label>
                <el-input-number v-model="pricingParams.weight" :min="0.1" :max="100" :step="0.1" size="small" />
              </div>
              <div class="form-row">
                <label>区域</label>
                <el-select v-model="pricingParams.region" size="small" style="width: 120px">
                  <el-option v-for="r in regions" :key="r" :value="r" :label="r" />
                </el-select>
              </div>
              <div class="form-row">
                <label>紧急程度</label>
                <el-select v-model="pricingParams.urgency" size="small" style="width: 100px">
                  <el-option value="normal" label="普通" />
                  <el-option value="urgent" label="加急" />
                  <el-option value="scheduled" label="预约" />
                </el-select>
              </div>
              <el-button type="primary" @click="calculatePricing" :loading="loadingPrice">
                计算价格
              </el-button>
            </div>
          </div>

          <!-- 定价结果 -->
          <div class="pricing-result" v-if="priceResult">
            <div class="price-display">
              <div class="base-price">
                <span class="label">基础价格</span>
                <span class="value">¥{{ priceResult.base_price }}</span>
              </div>
              <div class="final-price">
                <span class="label">最终价格</span>
                <span class="value highlight">¥{{ priceResult.final_price }}</span>
                <span class="multiplier">×{{ priceResult.multiplier }}</span>
              </div>
            </div>
            
            <!-- 价格组成 -->
            <div class="price-breakdown">
              <div class="breakdown-title">价格组成</div>
              <div class="breakdown-item" v-for="(v, k) in priceResult.price_components" :key="k">
                <span class="name">{{ getComponentName(k) }}</span>
                <span class="value" :class="{ negative: v < 0 }">{{ v > 0 ? '+' : '' }}¥{{ v }}</span>
              </div>
            </div>

            <!-- 建议 -->
            <div class="suggestions" v-if="priceResult.suggestions">
              <div class="suggestion" v-for="(s, i) in priceResult.suggestions" :key="i">
                💡 {{ s }}
              </div>
            </div>
          </div>

          <!-- 价格预测图 -->
          <div class="chart-card">
            <div class="card-title">📅 24小时价格预测</div>
            <div ref="priceForecastChart" class="chart-area"></div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ========== 库存优化 ========== -->
      <el-tab-pane label="📦 库存优化" name="inventory">
        <div class="tab-content">
          <!-- EOQ 计算器 -->
          <div class="inventory-calculator">
            <div class="calc-title">📐 EOQ 经济订货量计算</div>
            <div class="calc-form">
              <div class="form-row">
                <label>年需求量</label>
                <el-input-number v-model="eoqParams.annual_demand" :min="1" size="small" />
              </div>
              <div class="form-row">
                <label>订货成本</label>
                <el-input-number v-model="eoqParams.ordering_cost" :min="1" size="small" />
              </div>
              <div class="form-row">
                <label>持有成本率</label>
                <el-input-number v-model="eoqParams.holding_cost_rate" :min="0.01" :max="1" :step="0.01" size="small" />
              </div>
              <div class="form-row">
                <label>单价</label>
                <el-input-number v-model="eoqParams.unit_price" :min="1" size="small" />
              </div>
              <el-button type="primary" @click="calculateEOQ" :loading="loadingEOQ">
                计算 EOQ
              </el-button>
            </div>
          </div>

          <!-- EOQ 结果 -->
          <div class="eoq-result" v-if="eoqResult">
            <div class="result-cards">
              <div class="result-card">
                <div class="value">{{ eoqResult.eoq }}</div>
                <div class="label">经济订货量</div>
              </div>
              <div class="result-card">
                <div class="value">{{ eoqResult.order_cycle_days }} 天</div>
                <div class="label">订货周期</div>
              </div>
              <div class="result-card">
                <div class="value">¥{{ eoqResult.costs?.total_inventory_cost }}</div>
                <div class="label">总库存成本</div>
              </div>
            </div>
            
            <div class="policy-suggestion">
              <div class="policy-title">📋 订货策略</div>
              <div class="policy-item" v-for="(v, k) in eoqResult.policy" :key="k">
                {{ v }}
              </div>
            </div>
          </div>

          <!-- 安全库存计算 -->
          <div class="safety-stock-calc">
            <div class="calc-title">🛡️ 安全库存计算</div>
            <div class="calc-form">
              <div class="form-row">
                <label>平均日需求</label>
                <el-input-number v-model="ssParams.avg_demand" :min="1" size="small" />
              </div>
              <div class="form-row">
                <label>需求标准差</label>
                <el-input-number v-model="ssParams.demand_std" :min="0" size="small" />
              </div>
              <div class="form-row">
                <label>提前期 (天)</label>
                <el-input-number v-model="ssParams.lead_time" :min="1" size="small" />
              </div>
              <div class="form-row">
                <label>服务水平</label>
                <el-select v-model="ssParams.service_level" size="small" style="width: 100px">
                  <el-option :value="0.9" label="90%" />
                  <el-option :value="0.95" label="95%" />
                  <el-option :value="0.99" label="99%" />
                </el-select>
              </div>
              <el-button type="success" @click="calculateSafetyStock" :loading="loadingSS">
                计算安全库存
              </el-button>
            </div>
          </div>

          <!-- 安全库存结果 -->
          <div class="ss-result" v-if="ssResult">
            <div class="result-cards">
              <div class="result-card highlight">
                <div class="value">{{ ssResult.safety_stock }}</div>
                <div class="label">安全库存</div>
              </div>
              <div class="result-card">
                <div class="value">{{ ssResult.reorder_point }}</div>
                <div class="label">再订货点</div>
              </div>
              <div class="result-card">
                <div class="value">{{ ssResult.service_level * 100 }}%</div>
                <div class="label">服务水平</div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- ========== 多式联运 ========== -->
      <el-tab-pane label="🚚 多式联运" name="multimodal">
        <div class="tab-content">
          <!-- 运输方式对比 -->
          <div class="modes-comparison">
            <div class="section-title">🚆 运输方式对比</div>
            <div class="modes-grid">
              <div class="mode-card" v-for="mode in transportModes" :key="mode.id" @click="selectMode(mode.id)">
                <div class="mode-icon">{{ getModeIcon(mode.id) }}</div>
                <div class="mode-name">{{ mode.name }}</div>
                <div class="mode-stats">
                  <span>{{ mode.speed_km_h }} km/h</span>
                  <span>¥{{ mode.cost_per_km }}/km</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 路线优化 -->
          <div class="route-optimizer">
            <div class="calc-title">🗺️ 路线优化</div>
            <div class="calc-form">
              <div class="form-row">
                <label>起点</label>
                <el-input v-model="routeParams.origin" size="small" placeholder="如：北京" />
              </div>
              <div class="form-row">
                <label>终点</label>
                <el-input v-model="routeParams.destination" size="small" placeholder="如：上海" />
              </div>
              <div class="form-row">
                <label>距离 (km)</label>
                <el-input-number v-model="routeParams.distance" :min="1" size="small" />
              </div>
              <div class="form-row">
                <label>重量 (吨)</label>
                <el-input-number v-model="routeParams.weight" :min="0.1" size="small" />
              </div>
              <div class="form-row">
                <label>优先级</label>
                <el-select v-model="routeParams.priority" size="small" style="width: 100px">
                  <el-option value="fast" label="最快" />
                  <el-option value="cheap" label="最便宜" />
                  <el-option value="balanced" label="平衡" />
                  <el-option value="green" label="环保" />
                </el-select>
              </div>
              <el-button type="primary" @click="optimizeRoute" :loading="loadingRoute">
                优化路线
              </el-button>
            </div>
          </div>

          <!-- 路线结果 -->
          <div class="route-result" v-if="routeResult">
            <div class="best-route">
              <div class="route-header">🏆 推荐方案</div>
              <div class="route-info">
                <div class="route-modes">
                  <span v-for="(m, i) in routeResult.best_option?.modes" :key="i" class="mode-tag">
                    {{ getModeName(m) }}
                    <span v-if="i < routeResult.best_option?.modes?.length - 1"> → </span>
                  </span>
                </div>
                <div class="route-details">
                  <div class="detail">
                    <span class="label">总成本</span>
                    <span class="value">¥{{ routeResult.best_option?.total_cost }}</span>
                  </div>
                  <div class="detail">
                    <span class="label">总时间</span>
                    <span class="value">{{ routeResult.best_option?.total_time?.toFixed(1) }} 小时</span>
                  </div>
                  <div class="detail">
                    <span class="label">碳排放</span>
                    <span class="value">{{ routeResult.best_option?.total_co2?.toFixed(1) }} kg</span>
                  </div>
                </div>
              </div>
              <div class="recommendation">{{ routeResult.recommendation }}</div>
            </div>

            <!-- 其他方案 -->
            <div class="other-options" v-if="routeResult.all_options?.length > 1">
              <div class="section-title">📊 其他方案</div>
              <div class="option-list">
                <div class="option-item" v-for="(opt, i) in routeResult.all_options?.slice(1, 4)" :key="i">
                  <div class="option-modes">{{ opt.modes?.map(m => getModeName(m)).join(' → ') }}</div>
                  <div class="option-stats">
                    <span>¥{{ opt.total_cost }}</span>
                    <span>{{ opt.total_time?.toFixed(1) }}h</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 最后一公里 -->
          <div class="last-mile-section">
            <div class="section-title">🏁 最后一公里配送</div>
            <div class="last-mile-config">
              <el-button type="success" size="small" @click="optimizeLastMile">
                优化配送路线
              </el-button>
            </div>
            <div ref="lastMileChart" class="chart-area" style="height: 250px;"></div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { Cpu } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'
import * as echarts from 'echarts'
import {
  trainAdvancedModels,
  getEnsemblePrediction,
  getPredictionWithAnomaly,
  getAdvancedMLStatus
} from '@/api/advancedMl'
import { calculatePrice, getPriceForecast } from '@/api/pricing'
import { calculateEOQ as calculateEOQApi, calculateSafetyStock as calculateSafetyStockApi } from '@/api/inventory'
import { getTransportModes, estimateTransport, optimizeRoute as optimizeRouteApi } from '@/api/multimodal'

// Tab 状态
const activeTab = ref('prediction')

// ========== 高级预测 ==========
const training = ref(false)
const loadingPred = ref(false)
const modelTrained = ref(false)
const predictionDays = ref(7)
const predictions = ref([])
const anomalies = ref([])
const predictionChart = ref(null)
const modelCompareChart = ref(null)

// ========== 动态定价 ==========
const loadingPrice = ref(false)
const regions = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安']
const pricingParams = ref({
  distance: 100,
  weight: 1,
  region: '北京',
  urgency: 'normal'
})
const priceResult = ref(null)
const priceForecastChart = ref(null)

// ========== 库存优化 ==========
const loadingEOQ = ref(false)
const loadingSS = ref(false)
const eoqParams = ref({
  annual_demand: 1000,
  ordering_cost: 100,
  holding_cost_rate: 0.2,
  unit_price: 50
})
const eoqResult = ref(null)
const ssParams = ref({
  avg_demand: 10,
  demand_std: 3,
  lead_time: 5,
  service_level: 0.95
})
const ssResult = ref(null)

// ========== 多式联运 ==========
const loadingRoute = ref(false)
const transportModes = ref([])
const routeParams = ref({
  origin: '北京',
  destination: '上海',
  distance: 1200,
  weight: 5,
  priority: 'balanced'
})
const routeResult = ref(null)
const lastMileChart = ref(null)

let charts = []

// 图表初始化
const initChart = (domRef) => {
  if (!domRef) return null
  const existing = echarts.getInstanceByDom(domRef)
  if (existing) existing.dispose()
  const chart = echarts.init(domRef)
  charts.push(chart)
  return chart
}

// ========== 预测功能 ==========
const handleTrainModels = async () => {
  training.value = true
  try {
    const res = await trainAdvancedModels(180)
    if (res.success) {
      modelTrained.value = true
      ElNotification({
        title: '🎉 模型训练完成',
        message: `LSTM + Prophet 模型已训练，使用 ${res.stats?.total_records} 条数据`,
        type: 'success'
      })
    }
  } catch (e) {
    ElMessage.error('训练失败')
  } finally {
    training.value = false
  }
}

const loadPredictions = async () => {
  loadingPred.value = true
  try {
    const res = await getPredictionWithAnomaly(predictionDays.value)
    if (res.success) {
      predictions.value = res.data?.prediction?.predictions || []
      anomalies.value = res.data?.alerts || []
      initPredictionCharts(res.data?.prediction)
    }
  } catch (e) {
    // 模拟数据
    loadMockPredictions()
  } finally {
    loadingPred.value = false
  }
}

const loadMockPredictions = () => {
  predictions.value = Array.from({ length: predictionDays.value }, (_, i) => ({
    value: 200 + Math.random() * 100 + i * 5,
    lower: 180 + Math.random() * 50,
    upper: 250 + Math.random() * 80
  }))
  anomalies.value = [
    { level: 'info', message: '预测显示需求将增长，建议提前调度车辆' }
  ]
  initPredictionCharts({ predictions: predictions.value })
}

const initPredictionCharts = (data) => {
  // 趋势图
  const chart1 = initChart(predictionChart.value)
  if (chart1 && data?.predictions) {
    chart1.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      grid: { left: '5%', right: '5%', bottom: '10%', top: '10%', containLabel: true },
      xAxis: {
        type: 'category',
        data: data.predictions.map((_, i) => `Day ${i + 1}`),
        axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
        axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 10 }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
        axisLabel: { color: 'rgba(255,255,255,0.6)' }
      },
      series: [
        {
          name: '预测值',
          type: 'line',
          data: data.predictions.map(p => p.value || p),
          smooth: true,
          lineStyle: { color: '#00ff88', width: 3 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(0, 255, 136, 0.3)' },
              { offset: 1, color: 'rgba(0, 255, 136, 0.02)' }
            ])
          }
        }
      ]
    })
  }

  // 模型对比图
  const chart2 = initChart(modelCompareChart.value)
  if (chart2) {
    chart2.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: [
          { name: 'LSTM', value: 40, itemStyle: { color: '#00d4ff' } },
          { name: 'Prophet', value: 60, itemStyle: { color: '#00ff88' } }
        ],
        label: { color: '#fff', fontSize: 11 }
      }]
    })
  }
}

// ========== 定价功能 ==========
const calculatePricing = async () => {
  loadingPrice.value = true
  try {
    const res = await calculatePrice(pricingParams.value)
    if (res.success) {
      priceResult.value = res.data
      loadPriceForecast()
    }
  } catch (e) {
    // 模拟
    priceResult.value = {
      base_price: pricingParams.value.distance * 2,
      final_price: pricingParams.value.distance * 2.5,
      multiplier: 1.25,
      price_components: {
        time_adjustment: 15,
        supply_demand_adjustment: 10,
        urgency_adjustment: pricingParams.value.urgency === 'urgent' ? 50 : 0,
        weight_discount: -5
      },
      suggestions: ['当前定价合理，建议下单']
    }
    initPriceForecastChart()
  } finally {
    loadingPrice.value = false
  }
}

const loadPriceForecast = async () => {
  try {
    const res = await getPriceForecast(pricingParams.value.distance, pricingParams.value.region, 24)
    if (res.success) {
      initPriceForecastChart(res.data?.forecasts)
    }
  } catch (e) {
    initPriceForecastChart()
  }
}

const initPriceForecastChart = (forecasts) => {
  const chart = initChart(priceForecastChart.value)
  if (!chart) return

  const data = forecasts || Array.from({ length: 24 }, (_, i) => ({
    hour: i,
    price: 100 + Math.sin(i / 4) * 20 + Math.random() * 10
  }))

  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: '5%', right: '5%', bottom: '10%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map(d => `${d.hour}:00`),
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 9 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
      axisLabel: { color: 'rgba(255,255,255,0.6)' }
    },
    series: [{
      type: 'line',
      data: data.map(d => d.price),
      smooth: true,
      lineStyle: { color: '#ffd93d', width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(255, 217, 61, 0.3)' },
          { offset: 1, color: 'rgba(255, 217, 61, 0.02)' }
        ])
      }
    }]
  })
}

const getComponentName = (key) => {
  const names = {
    time_adjustment: '时间调整',
    supply_demand_adjustment: '供需调整',
    urgency_adjustment: '紧急加价',
    weight_discount: '大货折扣'
  }
  return names[key] || key
}

// ========== 库存功能 ==========
const calculateEOQ = async () => {
  loadingEOQ.value = true
  try {
    const res = await calculateEOQApi({
      annual_demand: eoqParams.value.annual_demand,
      ordering_cost: eoqParams.value.ordering_cost,
      holding_cost_per_unit: eoqParams.value.unit_price * eoqParams.value.holding_cost_rate,
      unit_price: eoqParams.value.unit_price
    })
    if (res.success) {
      eoqResult.value = res.data
    }
  } catch (e) {
    // 模拟计算
    const eoq = Math.sqrt(2 * eoqParams.value.annual_demand * eoqParams.value.ordering_cost / 
      (eoqParams.value.unit_price * eoqParams.value.holding_cost_rate))
    eoqResult.value = {
      eoq: Math.round(eoq),
      order_cycle_days: Math.round(365 / (eoqParams.value.annual_demand / eoq)),
      costs: {
        total_inventory_cost: Math.round(eoqParams.value.ordering_cost * (eoqParams.value.annual_demand / eoq) / 2)
      },
      policy: {
        order_when: `库存降至 ${Math.round(eoq * 0.3)} 单位时订货`,
        order_qty: `每次订货 ${Math.round(eoq)} 单位`,
        order_frequency: `每 ${Math.round(365 / (eoqParams.value.annual_demand / eoq))} 天订货一次`
      }
    }
  } finally {
    loadingEOQ.value = false
  }
}

const calculateSafetyStock = async () => {
  loadingSS.value = true
  try {
    const res = await calculateSafetyStockApi(ssParams.value)
    if (res.success) {
      ssResult.value = res.data
    }
  } catch (e) {
    // 模拟计算
    const z = ssParams.value.service_level === 0.95 ? 1.65 : ssParams.value.service_level === 0.99 ? 2.33 : 1.28
    const ss = z * ssParams.value.demand_std * Math.sqrt(ssParams.value.lead_time)
    ssResult.value = {
      safety_stock: Math.round(ss),
      reorder_point: Math.round(ssParams.value.avg_demand * ssParams.value.lead_time + ss),
      service_level: ssParams.value.service_level
    }
  } finally {
    loadingSS.value = false
  }
}

// ========== 多式联运功能 ==========
const loadTransportModes = async () => {
  try {
    const res = await getTransportModes()
    if (res.success) {
      transportModes.value = res.data
    }
  } catch (e) {
    transportModes.value = [
      { id: 'road', name: '公路运输', speed_km_h: 60, cost_per_km: 3.5 },
      { id: 'rail', name: '铁路运输', speed_km_h: 80, cost_per_km: 1.5 },
      { id: 'water', name: '水路运输', speed_km_h: 20, cost_per_km: 0.8 },
      { id: 'air', name: '航空运输', speed_km_h: 600, cost_per_km: 15 }
    ]
  }
}

const optimizeRoute = async () => {
  loadingRoute.value = true
  try {
    const res = await optimizeRouteApi(routeParams.value)
    if (res.success) {
      routeResult.value = res.data?.route_plan
    }
  } catch (e) {
    // 模拟
    routeResult.value = {
      best_option: {
        modes: ['road'],
        total_cost: routeParams.value.distance * 3,
        total_time: routeParams.value.distance / 60,
        total_co2: routeParams.value.distance * 0.12
      },
      all_options: [
        { modes: ['road'], total_cost: routeParams.value.distance * 3, total_time: routeParams.value.distance / 60 },
        { modes: ['road', 'rail', 'road'], total_cost: routeParams.value.distance * 2, total_time: routeParams.value.distance / 50 }
      ],
      recommendation: `推荐使用公路运输，预计 ${(routeParams.value.distance / 60).toFixed(1)} 小时到达`
    }
  } finally {
    loadingRoute.value = false
  }
}

const getModeIcon = (id) => {
  const icons = { road: '🚚', rail: '🚂', water: '🚢', air: '✈️' }
  return icons[id] || '🚛'
}

const getModeName = (id) => {
  const names = { road: '公路', rail: '铁路', water: '水路', air: '航空' }
  return names[id] || id
}

const optimizeLastMile = () => {
  initLastMileChart()
}

const initLastMileChart = () => {
  const chart = initChart(lastMileChart.value)
  if (!chart) return

  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['35%', '65%'],
      data: [
        { name: '货车', value: 45, itemStyle: { color: '#00d4ff' } },
        { name: '摩托车', value: 30, itemStyle: { color: '#00ff88' } },
        { name: '电动车', value: 20, itemStyle: { color: '#ffd93d' } },
        { name: '无人机', value: 5, itemStyle: { color: '#a855f7' } }
      ],
      label: { color: '#fff', fontSize: 11 }
    }]
  })
}

// 窗口调整
const handleResize = () => charts.forEach(c => c.resize())

onMounted(async () => {
  // 检查模型状态
  try {
    const status = await getAdvancedMLStatus()
    modelTrained.value = status.is_trained
  } catch (e) {}

  // 加载运输方式
  await loadTransportModes()

  // 加载预测数据
  await loadPredictions()

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  charts.forEach(c => c.dispose())
})
</script>

<style scoped>
.advanced-features-page {
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
.feature-tabs {
  background: rgba(0, 212, 255, 0.05);
  border-radius: 12px;
  padding: 12px;
}

:deep(.el-tabs__item) {
  color: rgba(255,255,255,0.6);
}

:deep(.el-tabs__item.is-active) {
  color: #00ff88;
}

:deep(.el-tabs__nav-wrap::after) {
  background-color: rgba(0, 212, 255, 0.2);
}

.tab-content {
  padding: 12px 0;
}

/* Status Bar */
.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.status-item.trained { color: #00ff88; }
.status-item.untrained { color: #ffd93d; }

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.config-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

/* Charts */
.charts-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.chart-card {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 12px;
  padding: 12px;
}

.chart-card.large {
  grid-row: span 1;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 8px;
}

.chart-area {
  height: 200px;
}

/* Alert Section */
.alert-section {
  background: rgba(255, 107, 107, 0.1);
  border: 1px solid rgba(255, 107, 107, 0.2);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  font-size: 12px;
}

.alert-item.critical { border-left: 3px solid #ff6b6b; }
.alert-item.warning { border-left: 3px solid #ffd93d; }
.alert-item.info { border-left: 3px solid #00d4ff; }

/* Pricing Calculator */
.pricing-calculator,
.inventory-calculator,
.safety-stock-calc,
.route-optimizer {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.calc-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 12px;
}

.calc-form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-row label {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
}

/* Price Result */
.pricing-result {
  background: rgba(0, 255, 136, 0.05);
  border: 1px solid rgba(0, 255, 136, 0.15);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.price-display {
  display: flex;
  justify-content: space-around;
  margin-bottom: 16px;
}

.base-price, .final-price {
  text-align: center;
}

.base-price .value,
.final-price .value {
  font-size: 28px;
  font-weight: 700;
}

.final-price .value.highlight {
  color: #00ff88;
}

.multiplier {
  display: block;
  font-size: 12px;
  color: rgba(255,255,255,0.5);
}

.price-breakdown {
  margin-bottom: 12px;
}

.breakdown-title {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}

.breakdown-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  font-size: 12px;
}

.breakdown-item .value.negative {
  color: #00ff88;
}

.suggestions {
  margin-top: 12px;
}

.suggestion {
  padding: 8px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  font-size: 12px;
  margin-bottom: 6px;
}

/* EOQ Result */
.result-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.result-card {
  text-align: center;
  padding: 16px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
}

.result-card.highlight {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.2);
}

.result-card .value {
  font-size: 24px;
  font-weight: 700;
  color: #00ff88;
}

.result-card .label {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
  margin-top: 4px;
}

.policy-suggestion {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  padding: 12px;
}

.policy-title {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}

.policy-item {
  font-size: 12px;
  padding: 4px 0;
  color: rgba(255,255,255,0.8);
}

/* Multimodal */
.modes-comparison {
  margin-bottom: 16px;
}

.modes-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.mode-card {
  text-align: center;
  padding: 16px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.mode-card:hover {
  background: rgba(0, 212, 255, 0.1);
  border-color: #00d4ff;
}

.mode-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.mode-name {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 4px;
}

.mode-stats {
  font-size: 10px;
  color: rgba(255,255,255,0.5);
  display: flex;
  justify-content: center;
  gap: 8px;
}

/* Route Result */
.route-result {
  margin-top: 16px;
}

.best-route {
  background: rgba(0, 255, 136, 0.05);
  border: 1px solid rgba(0, 255, 136, 0.15);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.route-header {
  font-size: 14px;
  font-weight: 600;
  color: #00ff88;
  margin-bottom: 12px;
}

.route-modes {
  font-size: 16px;
  margin-bottom: 12px;
}

.mode-tag {
  display: inline-block;
  padding: 4px 8px;
  background: rgba(0, 212, 255, 0.1);
  border-radius: 4px;
  margin-right: 4px;
}

.route-details {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.detail {
  text-align: center;
}

.detail .label {
  display: block;
  font-size: 10px;
  color: rgba(255,255,255,0.5);
}

.detail .value {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.recommendation {
  padding: 10px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  font-size: 12px;
}

.other-options {
  margin-top: 16px;
}

.option-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.option-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 6px;
  font-size: 12px;
}

.option-stats {
  display: flex;
  gap: 12px;
  color: rgba(255,255,255,0.7);
}

.last-mile-section {
  margin-top: 16px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 12px;
  padding: 16px;
}

.last-mile-config {
  margin-bottom: 12px;
}

/* Element Plus Override */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #00ff88, #00d4ff);
  border: none;
  color: #000;
}

:deep(.el-input__wrapper),
:deep(.el-input-number) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
}

:deep(.el-input__inner) {
  color: #fff;
}

:deep(.el-select .el-input__wrapper) {
  background: rgba(0, 212, 255, 0.1);
}
</style>