<template>
  <div class="ml-prediction-page">
    <!-- 背景动效 -->
    <div class="bg-effects">
      <div class="grid-lines"></div>
      <div class="neural-pattern"></div>
    </div>

    <!-- 顶部标题 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="glow-title">🧠 机器学习预测中心</h1>
        <span class="subtitle">MACHINE LEARNING PREDICTION CENTER</span>
      </div>
      <div class="header-right">
        <div class="model-status" :class="modelTrained ? 'trained' : 'untrained'">
          <span class="status-dot"></span>
          <span>{{ modelTrained ? '模型已训练' : '模型未训练' }}</span>
        </div>
        <el-button type="primary" size="small" @click="handleTrain" :loading="training">
          <el-icon><Cpu /></el-icon> 训练模型
        </el-button>
        <el-button type="success" size="small" @click="handleModelPredict" :loading="predictingModel" :disabled="!modelTrained">
          <el-icon><Cpu /></el-icon> 模型预测
        </el-button>
        <el-button type="warning" size="small" @click="handleDeepTrainingJob" :loading="deepJobLoading">
          <el-icon><Cpu /></el-icon> 深度 Shadow
        </el-button>
      </div>
    </div>

    <!-- 预测配置 -->
    <div class="config-section">
      <el-card class="config-card">
        <div class="config-header">
          <span class="config-title">⚙️ 预测配置</span>
        </div>
        <div class="config-form">
          <el-form :inline="true">
            <el-form-item label="预测天数">
              <el-select v-model="predictDays" style="width: 100px">
                <el-option :value="7" label="7天" />
                <el-option :value="14" label="14天" />
                <el-option :value="30" label="30天" />
              </el-select>
            </el-form-item>
            <el-form-item label="区域">
              <el-select v-model="selectedRegion" style="width: 120px" clearable placeholder="全部区域">
                <el-option v-for="r in regions" :key="r" :value="r" :label="r" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="success" @click="loadPredictions" :loading="loading">
                🔮 开始预测
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-card>
    </div>

    <div class="truth-strip">
      <div class="truth-item">
        <span>Forecast</span>
        <strong>{{ forecastMeta.forecast_status || forecastMeta.provider_status || 'unknown' }}</strong>
      </div>
      <div class="truth-item">
        <span>时间粒度</span>
        <strong>{{ forecastMeta.time_granularity || timelineAudit.recommended?.time_granularity || '-' }}</strong>
      </div>
      <div class="truth-item">
        <span>历史桶数</span>
        <strong>{{ forecastMeta.series_summary?.time_bucket_points ?? timelineAudit.fields?.shipped_at?.distinct_dates ?? 0 }}</strong>
      </div>
      <div class="truth-item">
        <span>深度窗口</span>
        <strong>{{ timelineAudit.recommended?.training_windows ?? 0 }}/32</strong>
      </div>
      <div class="truth-item truth-item--wide">
        <span>Job</span>
        <strong>{{ deepJobStatusText }}</strong>
      </div>
    </div>

    <el-alert
      v-if="forecastWarning"
      class="forecast-alert"
      type="warning"
      :closable="false"
      show-icon
    >
      <template #title>{{ forecastWarning }}</template>
    </el-alert>

    <!-- 核心指标 -->
    <div class="metrics-row">
      <div class="metric-card gradient-cyan">
        <div class="metric-icon">📦</div>
        <div class="metric-content">
          <div class="metric-value">{{ summary.totalPredicted ?? '—' }}</div>
          <div class="metric-label">预测总订单</div>
        </div>
        <div class="metric-trend up">缺口 {{ summary.growthRate }}天</div>
      </div>
      <div class="metric-card gradient-green">
        <div class="metric-icon">🚛</div>
        <div class="metric-content">
          <div class="metric-value">{{ summary.vehiclesNeeded }}</div>
          <div class="metric-label">建议车辆数</div>
        </div>
      </div>
      <div class="metric-card gradient-orange">
        <div class="metric-icon">⚖️</div>
        <div class="metric-content">
          <div class="metric-value">{{ formatNumber(summary.savedCost, 0) }}kg</div>
          <div class="metric-label">最大重量缺口</div>
        </div>
      </div>
      <div class="metric-card gradient-purple">
        <div class="metric-icon">🎯</div>
        <div class="metric-content">
          <div class="metric-value">{{ summary.confidence }}%</div>
          <div class="metric-label">预测置信度</div>
        </div>
      </div>
    </div>

    <!-- 主图表区域 -->
    <div class="main-grid">
      <!-- 预测趋势图 -->
      <div class="panel-card large">
        <div class="card-header">
          <div class="header-deco"><span class="deco-line"></span><span class="deco-dot"></span></div>
          <span class="card-title">📈 需求预测趋势</span>
          <el-tag size="small" effect="dark">{{ forecastMeta.model || 'Baseline' }}</el-tag>
        </div>
        <div class="chart-shell">
          <div ref="trendChart" class="chart-area large"></div>
          <div v-if="!predictions.length" class="chart-empty">
            <strong>历史时间跨度不足</strong>
            <span>{{ forecastWarning || '暂无可展示预测曲线' }}</span>
          </div>
        </div>
      </div>

      <!-- 区域分布 -->
      <div class="panel-card">
        <div class="card-header">
          <div class="header-deco"><span class="deco-line"></span><span class="deco-dot"></span></div>
          <span class="card-title">🗺️ 区域需求分布</span>
        </div>
        <div ref="regionChart" class="chart-area"></div>
      </div>

      <!-- 合并配送建议 -->
      <div class="panel-card">
        <div class="card-header">
          <div class="header-deco"><span class="deco-line"></span><span class="deco-dot"></span></div>
          <span class="card-title">AI 预测建议</span>
          <el-badge :value="predictionRecommendations.length" type="success" />
        </div>
        <div class="suggestions-list">
          <div v-for="(item, i) in predictionRecommendations" :key="i" class="suggestion-item suggestion-item--text">
            <div class="suggestion-region">建议 {{ i + 1 }}</div>
            <p class="suggestion-text">{{ item }}</p>
          </div>
          <div v-if="!predictionRecommendations.length" class="empty-hint">暂无预测建议或后端处于降级状态</div>
        </div>
      </div>
    </div>

    <!-- 车辆调配建议 -->
    <div class="panel-card full-width">
      <div class="card-header">
        <div class="header-deco"><span class="deco-line"></span><span class="deco-dot"></span></div>
        <span class="card-title">预测运力缺口</span>
      </div>
      <div class="allocation-grid">
        <div v-for="(item, i) in capacityForecast" :key="item.date || i" class="allocation-item">
          <div class="region-name">{{ item.date || `D+${i + 1}` }}</div>
          <div class="allocation-bar">
            <div class="bar-fill" :class="{ warning: item.status === 'shortage' }" :style="{ width: utilizationWidth(item) }"></div>
          </div>
          <div class="allocation-info">
            <span class="vehicles">{{ formatNumber(item.predicted_shipments, 0) }}单</span>
            <span class="orders">{{ item.status === 'shortage' ? '缺口' : '覆盖' }}</span>
          </div>
        </div>
      </div>
      <div class="allocation-summary">
        <span class="summary-text">可用车辆 <strong>{{ totalVehicles }}</strong> 辆 · 缺口天数 <strong>{{ capacitySummary.shortage_days || 0 }}</strong></span>
        <el-button type="primary" size="small" @click="applyAllocation">进入智能调度</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { Cpu } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'
import * as echarts from 'echarts'
import {
  createPredictionJob,
  forecastCapacityGap,
  getDemandForecast,
  getPredictionJob,
  getPredictionModelStatus,
  getPredictionScorecard,
  getPredictionTimelineAudit,
  predictWithPredictionModel,
  trainPredictionModel
} from '@/api/aiPrediction'
import { useRouter } from 'vue-router'

// 状态
const loading = ref(false)
const training = ref(false)
const predictingModel = ref(false)
const deepJobLoading = ref(false)
const modelTrained = ref(false)
const trainedModelId = ref(null)
const activeDeepJobId = ref(null)
const deepJob = ref(null)
const predictDays = ref(7)
const selectedRegion = ref(null)
const regions = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '西安']
const router = useRouter()

// 数据
const predictions = ref([])
const predictionRecommendations = ref([])
const capacityForecast = ref([])
const capacitySummary = ref({})
const fleetCapacity = ref({})
const forecastMeta = ref({})
const timelineAudit = ref({})

// 汇总
const summary = ref({
  totalPredicted: 0,
  vehiclesNeeded: 0,
  savedCost: 0,
  confidence: 92,
  growthRate: 15
})

// 图表引用
const trendChart = ref(null)
const regionChart = ref(null)

let charts = []

// 计算总车辆数
const totalVehicles = computed(() => {
  return fleetCapacity.value?.available_vehicles || 0
})

const forecastWarning = computed(() => {
  const status = forecastMeta.value?.forecast_status || forecastMeta.value?.provider_status
  const reason = forecastMeta.value?.fallback_reason
  const points = forecastMeta.value?.series_summary?.time_bucket_points
  if (reason) {
    return `需求预测已降级：${reason}，当前可用时间桶 ${points ?? 0} 个`
  }
  if (status === 'degraded') return '需求预测处于降级状态，请先检查真实历史时间轴'
  if (predictions.value.length) return ''
  return status === 'degraded' ? '需求预测处于降级状态，请先检查真实历史时间轴' : ''
})

const deepJobStatusText = computed(() => {
  if (!deepJob.value) return '未创建'
  const job = deepJob.value.job || deepJob.value
  return `${job.model_family || job.policy_family || 'shadow'} · ${job.status || 'unknown'}`
})

// 安全初始化图表
const initChart = (domRef) => {
  if (!domRef) return null
  const existingInstance = echarts.getInstanceByDom(domRef)
  if (existingInstance) existingInstance.dispose()
  const chart = echarts.init(domRef)
  charts.push(chart)
  return chart
}

// 训练模型
const handleTrain = async () => {
  training.value = true
  try {
    const res = await trainPredictionModel({
      task: 'eta',
      runtime_profile: 'full',
      limit: 10000
    })
    if (res.success) {
      modelTrained.value = true
      trainedModelId.value = res.model?.model_id || trainedModelId.value
      const trainingSummary = res.model?.training_summary || {}
      ElNotification({
        title: '模型训练完成',
        message: `使用 ${trainingSummary.row_count || 0} 条真实 shipment_facts 特征训练 ETA baseline`,
        type: 'success',
        duration: 5000
      })
      await handleModelPredict(false)
    }
  } catch (e) {
    ElMessage.error(friendlyError(e, '训练失败：请稍后重试或降低训练样本数'))
  } finally {
    training.value = false
  }
}

const handleModelPredict = async (notify = true) => {
  predictingModel.value = true
  try {
    const res = await predictWithPredictionModel({
      task: 'eta',
      model_id: trainedModelId.value,
      runtime_profile: 'full',
      limit: 10000,
      row_limit: 12
    })
    if (!res.success) {
      ElMessage.warning(res.fallback_reason || res.error || '模型预测暂不可用，请先完成训练')
      return
    }
    const rows = res.prediction?.rows || []
    const avgPrediction = rows.length
      ? rows.reduce((sum, row) => sum + Number(row.predicted_value ?? row.prediction ?? 0), 0) / rows.length
      : 0
    predictionRecommendations.value = [
      `ETA 模型已返回 ${rows.length} 条预测样本，平均预测值 ${formatNumber(avgPrediction, 2)}`,
      ...predictionRecommendations.value
    ].slice(0, 8)
    if (notify) {
      ElNotification({
        title: '模型预测完成',
        message: `已使用模型 ${res.model?.model_id || trainedModelId.value || 'latest'} 返回 ${rows.length} 条 shadow 预测`,
        type: 'success'
      })
    }
  } catch (e) {
    ElMessage.error(friendlyError(e, '模型预测失败：请确认后端 AI prediction 服务可用'))
  } finally {
    predictingModel.value = false
  }
}

const handleDeepTrainingJob = async () => {
  deepJobLoading.value = true
  try {
    const res = await createPredictionJob({
      task: 'demand',
      model_family: 'lstm',
      runtime_profile: 'full',
      limit: 50000,
      horizon_days: predictDays.value,
      sequence_length: 14,
      city: selectedRegion.value
    })
    if (res.success) {
      activeDeepJobId.value = res.job?.job_id
      deepJob.value = res.job
      ElNotification({
        title: '深度 Shadow 任务已创建',
        message: '任务将在后台审计 LSTM/GRU/Transformer readiness，不阻塞页面。',
        type: 'success'
      })
      setTimeout(() => pollDeepJob(), 1200)
    } else {
      ElMessage.warning(res.fallback_reason || '深度 Shadow 任务创建失败')
    }
  } catch (e) {
    ElMessage.error(friendlyError(e, '深度 Shadow 任务创建失败'))
  } finally {
    deepJobLoading.value = false
  }
}

const pollDeepJob = async () => {
  if (!activeDeepJobId.value) return
  try {
    const res = await getPredictionJob(activeDeepJobId.value)
    if (res.success) {
      deepJob.value = res.job
      const status = res.job?.status
      if (status && !['completed', 'failed'].includes(status)) {
        setTimeout(() => pollDeepJob(), 1600)
      } else if (status === 'completed') {
        const readiness = res.job?.result?.deep_learning_readiness
        predictionRecommendations.value = [
          readiness?.ready
            ? '深度模型 readiness 已通过，可进入离线回测对比。'
            : `深度模型仍处 shadow：${res.job?.fallback_reason || readiness?.status || '训练窗口不足'}`,
          ...predictionRecommendations.value
        ].slice(0, 8)
      }
    }
  } catch (e) {
    console.warn('轮询深度 Shadow 任务失败:', e)
  }
}

// 加载预测数据
const loadPredictions = async () => {
  loading.value = true
  try {
    const [auditRes, forecastRes, capacityRes] = await Promise.all([
      getPredictionTimelineAudit({
        city: selectedRegion.value,
        sequence_length: 14
      }),
      getDemandForecast(predictDays.value, selectedRegion.value, 5000, {
        runtime_profile: 'interactive',
        time_granularity: 'auto',
        series_source: 'shipped_at'
      }),
      forecastCapacityGap({
        horizon_days: predictDays.value,
        city: selectedRegion.value,
        runtime_profile: 'interactive',
        limit: 5000
      })
    ])
    timelineAudit.value = auditRes || {}
    const scorecardRes = await getPredictionScorecard({
      horizon_days: predictDays.value,
      city: selectedRegion.value,
      runtime_profile: 'interactive',
      limit: 5000
    })
    
    forecastMeta.value = {
      forecast_status: forecastRes.forecast_status,
      provider_status: forecastRes.provider_status,
      fallback_reason: forecastRes.fallback_reason,
      time_granularity: forecastRes.time_granularity,
      series_source: forecastRes.series_source,
      series_summary: forecastRes.series_summary,
      model: forecastRes.model
    }

    if (forecastRes.success) {
      const forecast = forecastRes.forecast || []
      predictions.value = forecast.map((item) => ({
        date: item.date,
        predicted_orders: item.predicted_orders ?? item.predicted_value ?? 0,
        confidence_upper: item.confidence_upper ?? item.upper_bound ?? item.upper ?? item.predicted_orders ?? item.predicted_value ?? 0,
        confidence: 90
      }))
      const totalPredicted = predictions.value.reduce((sum, item) => sum + Number(item.predicted_orders || 0), 0)
      const readinessScore = scorecardRes.summary?.readiness_score
      summary.value = {
        totalPredicted: Math.round(totalPredicted),
        vehiclesNeeded: capacityRes.fleet_capacity?.available_vehicles || 0,
        savedCost: capacityRes.summary?.max_weight_gap_kg || 0,
        confidence: Math.round(readinessScore || 0),
        growthRate: capacityRes.summary?.shortage_days || 0
      }
      const regionName = selectedRegion.value || '全部区域'
      if (predictions.value.length) {
        initTrendChart(predictions.value, { [regionName]: summary.value.totalPredicted })
        initRegionChart({ [regionName]: summary.value.totalPredicted })
      } else {
        summary.value.totalPredicted = null
        initEmptyChart(trendChart.value, forecastRes.fallback_reason || '历史时间桶不足')
        initRegionChart({})
      }
    }

    capacityForecast.value = capacityRes.forecast || []
    capacitySummary.value = capacityRes.summary || {}
    fleetCapacity.value = capacityRes.fleet_capacity || {}
    predictionRecommendations.value = [
      forecastRes.fallback_reason ? `需求预测降级：${forecastRes.fallback_reason}` : null,
      `时间轴：shipped_at 日 ${auditRes.fields?.shipped_at?.distinct_dates || 0} 天 / 小时 ${auditRes.fields?.shipped_at?.distinct_hours || 0} 桶`,
      ...(scorecardRes.recommendations || []),
      ...(capacityRes.recommendations || [])
    ].filter(Boolean).slice(0, 8)
  } catch (e) {
    console.error('加载预测失败:', e)
    ElMessage.error(friendlyError(e, 'AI 预测接口加载失败，请检查 /api/ai-prediction 后端链路'))
  } finally {
    loading.value = false
  }
}

const friendlyError = (error, fallback) => {
  if (error?.code === 'ECONNABORTED' || String(error?.message || '').includes('timeout')) {
    return 'AI 请求超时：首屏已使用轻量模式，训练/全量分析请稍后手动重试'
  }
  if (!error?.response) return '后端不可达：请确认 Flask 服务已启动'
  return error.response.data?.fallback_reason || error.response.data?.error || fallback
}

const formatNumber = (value, digits = 0) => {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return '-'
  return new Intl.NumberFormat('zh-CN', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits
  }).format(numberValue)
}

const utilizationWidth = (item) => {
  const utilization = Number(item.weight_utilization || item.volume_utilization || 0)
  const percent = Number.isFinite(utilization) ? Math.max(3, Math.min(100, utilization * 100)) : 3
  return `${percent}%`
}

// 初始化趋势图
const initTrendChart = (data, regionDist) => {
  const chart = initChart(trendChart.value)
  if (!chart) return
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(0,0,0,0.8)', borderColor: '#00d4ff', textStyle: { color: '#fff' } },
    legend: { data: ['预测订单', '置信区间'], textStyle: { color: 'rgba(255,255,255,0.7)' }, bottom: 0 },
    grid: { left: '5%', right: '5%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map(d => d.date?.slice(5) || ''),
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
        name: '预测订单',
        type: 'line',
        data: data.map(d => d.predicted_orders),
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { color: '#00ff88', width: 3 },
        itemStyle: { color: '#00ff88' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 255, 136, 0.3)' },
            { offset: 1, color: 'rgba(0, 255, 136, 0.02)' }
          ])
        }
      },
      {
        name: '置信区间',
        type: 'line',
        data: data.map(d => d.confidence_upper),
        lineStyle: { type: 'dashed', color: 'rgba(0, 212, 255, 0.5)' },
        itemStyle: { color: '#00d4ff' },
        symbol: 'none'
      }
    ]
  })
}

const initEmptyChart = (domRef, reason = '历史时间桶不足') => {
  const chart = initChart(domRef)
  if (!chart) return
  chart.setOption({
    backgroundColor: 'transparent',
    title: {
      text: '暂无可预测趋势',
      subtext: reason,
      left: 'center',
      top: 'middle',
      textStyle: { color: 'rgba(255,255,255,0.82)', fontSize: 16 },
      subtextStyle: { color: 'rgba(255,255,255,0.48)', fontSize: 12 }
    },
    xAxis: { show: false },
    yAxis: { show: false },
    series: []
  })
}

// 初始化区域分布图
const initRegionChart = (regionDist) => {
  const chart = initChart(regionChart.value)
  if (!chart) return
  
  const data = Object.entries(regionDist).map(([name, value]) => ({ name, value }))
  if (!data.length) {
    chart.setOption({
      backgroundColor: 'transparent',
      title: {
        text: '暂无区域预测',
        left: 'center',
        top: 'middle',
        textStyle: { color: 'rgba(255,255,255,0.72)', fontSize: 14 }
      },
      series: []
    })
    return
  }
  
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', backgroundColor: 'rgba(0,0,0,0.8)', borderColor: '#00d4ff', textStyle: { color: '#fff' } },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '50%'],
      data: data.map((d, i) => ({
        name: d.name,
        value: d.value,
        itemStyle: { color: ['#00d4ff', '#00ff88', '#ffd93d', '#ff6b6b', '#a855f7', '#06b6d4'][i % 6] }
      })),
      label: { show: true, formatter: '{b}\n{c}单', color: '#fff', fontSize: 11 },
      itemStyle: { borderRadius: 6, borderColor: 'rgba(0,0,0,0.3)', borderWidth: 2 }
    }]
  })
}

// 应用调配方案
const applyAllocation = () => {
  router.push('/dispatch')
  ElNotification({
    title: '已进入智能调度',
    message: '预测结果仅做 shadow planning，实际派车由调度求解器校验。',
    type: 'info'
  })
}

// 窗口调整
const handleResize = () => charts.forEach(c => c.resize())

onMounted(async () => {
  // 检查模型状态
  try {
    const status = await getPredictionModelStatus()
    modelTrained.value = Number(status.model_count || 0) > 0
    trainedModelId.value = status.latest_by_task?.eta?.model_id || null
  } catch (e) {}
  
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
.ml-prediction-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #0d1033 100%);
  padding: 16px;
  color: #fff;
  position: relative;
  overflow: hidden;
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

.neural-pattern {
  position: absolute;
  inset: 0;
  opacity: 0.05;
  background: radial-gradient(circle at 20% 30%, rgba(0, 255, 136, 0.3) 0%, transparent 50%),
              radial-gradient(circle at 80% 70%, rgba(0, 212, 255, 0.3) 0%, transparent 50%);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px 20px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
}

.glow-title {
  margin: 0;
  font-size: 22px;
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
  text-transform: uppercase;
  margin-top: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.model-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
}

.model-status.trained {
  background: rgba(0, 255, 136, 0.15);
  border: 1px solid rgba(0, 255, 136, 0.3);
  color: #00ff88;
}

.model-status.untrained {
  background: rgba(255, 217, 61, 0.15);
  border: 1px solid rgba(255, 217, 61, 0.3);
  color: #ffd93d;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.model-status.trained .status-dot {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 currentColor; }
  50% { box-shadow: 0 0 0 6px transparent; }
}

/* 配置卡片 */
.config-section { margin-bottom: 16px; }
.config-card {
  background: rgba(0, 212, 255, 0.05) !important;
  border: 1px solid rgba(0, 212, 255, 0.15) !important;
  border-radius: 12px !important;
}
.config-header { margin-bottom: 12px; }
.config-title { font-size: 14px; font-weight: 600; color: #fff; }
.config-form { padding: 8px 0; }

.truth-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.truth-item {
  padding: 10px 12px;
  border: 1px solid rgba(0, 212, 255, 0.14);
  border-radius: 10px;
  background: rgba(255,255,255,0.04);
}

.truth-item span {
  display: block;
  font-size: 11px;
  color: rgba(255,255,255,0.48);
  margin-bottom: 4px;
}

.truth-item strong {
  display: block;
  font-size: 13px;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.forecast-alert {
  margin-bottom: 16px;
}

/* 指标卡片 */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  display: flex;
  align-items: center;
  padding: 16px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.15);
  border-radius: 12px;
  gap: 12px;
}

.metric-card.gradient-cyan { border-left: 3px solid #00d4ff; }
.metric-card.gradient-green { border-left: 3px solid #00ff88; }
.metric-card.gradient-orange { border-left: 3px solid #ff9500; }
.metric-card.gradient-purple { border-left: 3px solid #a855f7; }

.metric-icon { font-size: 28px; }
.metric-content { flex: 1; }
.metric-value { font-size: 24px; font-weight: 700; color: #fff; }
.metric-label { font-size: 12px; color: rgba(255,255,255,0.6); margin-top: 4px; }
.metric-trend { font-size: 12px; padding: 4px 8px; border-radius: 10px; }
.metric-trend.up { background: rgba(0, 255, 136, 0.2); color: #00ff88; }

/* 面板卡片 */
.main-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.panel-card {
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 12px;
  padding: 12px;
}

.panel-card.large { grid-row: span 2; }
.panel-card.full-width { width: 100%; }

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.header-deco { display: flex; align-items: center; gap: 4px; }
.deco-line { width: 16px; height: 2px; background: linear-gradient(90deg, #00ff88, transparent); }
.deco-dot { width: 5px; height: 5px; background: #00ff88; border-radius: 50%; }
.card-title { flex: 1; font-size: 13px; font-weight: 600; color: #fff; }

.chart-area { height: 200px; }
.chart-area.large { height: 320px; }

.chart-shell {
  position: relative;
}

.chart-empty {
  position: absolute;
  inset: auto 18px 18px 18px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(255, 217, 61, 0.1);
  border: 1px solid rgba(255, 217, 61, 0.22);
  color: rgba(255,255,255,0.72);
  display: flex;
  flex-direction: column;
  gap: 4px;
  pointer-events: none;
}

.chart-empty strong {
  color: #ffd93d;
}

/* 建议列表 */
.suggestions-list {
  max-height: 280px;
  overflow-y: auto;
}

.suggestion-item {
  display: flex;
  align-items: center;
  padding: 10px;
  margin-bottom: 8px;
  background: rgba(0, 255, 136, 0.05);
  border-radius: 8px;
  border-left: 3px solid #00ff88;
}

.suggestion-item--text {
  align-items: flex-start;
}

.suggestion-region {
  font-weight: 600;
  color: #fff;
  width: 60px;
  flex: 0 0 auto;
}

.suggestion-text {
  margin: 0;
  color: rgba(255,255,255,0.76);
  font-size: 12px;
  line-height: 1.5;
}

.empty-hint {
  padding: 18px;
  color: rgba(255,255,255,0.5);
  text-align: center;
  border-radius: 8px;
  background: rgba(255,255,255,0.04);
}

.suggestion-stats {
  flex: 1;
  display: flex;
  gap: 12px;
  font-size: 12px;
}

.suggestion-stats .orders { color: rgba(255,255,255,0.7); }
.suggestion-stats .save { color: #00ff88; }

/* 调配网格 */
.allocation-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.allocation-item {
  padding: 12px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
}

.region-name { font-size: 14px; font-weight: 600; color: #fff; margin-bottom: 8px; }

.allocation-bar {
  height: 6px;
  background: rgba(0, 212, 255, 0.1);
  border-radius: 3px;
  margin-bottom: 8px;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00d4ff, #00ff88);
  border-radius: 3px;
}

.bar-fill.warning {
  background: linear-gradient(90deg, #ffd93d, #ff6b6b);
}

.allocation-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: rgba(255,255,255,0.6);
}

.allocation-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.summary-text { color: rgba(255,255,255,0.7); }
.summary-text strong { color: #00ff88; font-size: 18px; }

/* Element Plus 覆盖 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #00ff88, #00d4ff);
  border: none;
  color: #000;
}

:deep(.el-tag) {
  background: rgba(0, 255, 136, 0.2);
  border-color: rgba(0, 255, 136, 0.3);
  color: #00ff88;
}

:deep(.el-card) {
  background: transparent;
}

:deep(.el-input__wrapper) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.2);
  box-shadow: none;
}

:deep(.el-input__inner) { color: #fff; }
</style>
