<template>
  <div class="multi-objective-panel">
    <!-- 权重调节区 -->
    <div class="weights-section">
      <div class="section-header">
        <h3>🎯 优化目标权重</h3>
        <el-button 
          type="primary" 
          size="small" 
          text
          @click="resetWeights"
        >
          重置
        </el-button>
      </div>
      
      <div class="weights-grid">
        <WeightSlider
          v-for="obj in objectives"
          :key="obj.name"
          :objective="obj.name"
          :title="obj.display_name"
          :unit="obj.unit"
          v-model="weights[obj.name]"
          @change="handleWeightChange"
        />
      </div>
      
      <div class="weights-summary">
        <span>权重总计: </span>
        <el-tag :type="totalWeightValid ? 'success' : 'danger'">
          {{ totalWeight }}%
        </el-tag>
        <span v-if="!totalWeightValid" class="weight-warning">
          (请调整至100%)
        </span>
      </div>
    </div>
    
    <!-- 优化算法选择 -->
    <div class="algorithm-section">
      <h3>⚙️ 优化算法</h3>
      <el-radio-group v-model="algorithm" size="small">
        <el-radio-button value="all" label="all">智能推荐</el-radio-button>
        <el-radio-button value="weighted_sum" label="weighted_sum">加权最优</el-radio-button>
        <el-radio-button value="pareto" label="pareto">Pareto前沿</el-radio-button>
      </el-radio-group>
    </div>
    
    <!-- 开始优化按钮 -->
    <div class="action-section">
      <el-button
        type="primary"
        size="large"
        :loading="loading"
        :disabled="!canOptimize"
        @click="startOptimize"
      >
        <el-icon><Promotion /></el-icon>
        开始优化
      </el-button>
    </div>
    
    <!-- 优化结果 -->
    <div v-if="result" class="result-section">
      <h3>📊 优化结果</h3>
      
      <!-- 推荐方案列表 -->
      <div class="recommendations">
        <div
          v-for="(rec, index) in result.recommendations"
          :key="index"
          class="recommendation-card"
          :class="{ active: selectedRecommendation === index }"
          @click="selectRecommendation(index)"
        >
          <div class="rec-header">
            <span class="rec-type">{{ getTypeLabel(rec.type) }}</span>
            <span class="rec-title">{{ rec.title }}</span>
          </div>
          <div class="rec-desc">{{ rec.description }}</div>
          <div class="rec-objectives">
            <span
              v-for="(value, key) in rec.objectives"
              :key="key"
              class="obj-tag"
            >
              {{ getObjectiveLabel(key) }}: {{ formatValue(key, value) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'
import WeightSlider from './WeightSlider.vue'
import { getObjectives, optimizeRoute } from '../api/multiObjective'

const props = defineProps({
  originId: {
    type: [Number, String],
    default: null
  },
  destinationId: {
    type: [Number, String],
    default: null
  }
})

const emit = defineEmits(['result', 'select'])

// 状态
const loading = ref(false)
const objectives = ref([])
const weights = ref({})
const algorithm = ref('all')
const result = ref(null)
const selectedRecommendation = ref(0)

// 默认权重
const defaultWeights = {
  distance: 25,
  time: 30,
  cost: 20,
  traffic: 15,
  weather_risk: 10
}

// 权重总计
const totalWeight = computed(() => {
  return Object.values(weights.value).reduce((sum, w) => sum + w, 0)
})

const totalWeightValid = computed(() => {
  return totalWeight.value === 100
})

const canOptimize = computed(() => {
  return props.originId && props.destinationId && totalWeightValid.value
})

// 获取优化目标列表
async function fetchObjectives() {
  try {
    const res = await getObjectives()
    if (res.success) {
      objectives.value = res.objectives
      
      // 初始化权重
      res.objectives.forEach(obj => {
        weights.value[obj.name] = obj.default_weight * 100
      })
    }
  } catch (error) {
    console.error('获取优化目标失败:', error)
    // 使用默认值
    weights.value = { ...defaultWeights }
  }
}

// 重置权重
function resetWeights() {
  weights.value = { ...defaultWeights }
  ElMessage.success('权重已重置')
}

// 权重变化处理
function handleWeightChange({ objective, value }) {
  // 可以在这里添加权重自动调整逻辑
  // 例如：当总权重超过100%时自动调整其他权重
}

// 开始优化
async function startOptimize() {
  if (!canOptimize.value) {
    ElMessage.warning('请先选择起点和终点')
    return
  }
  
  loading.value = true
  
  try {
    // 转换权重为小数
    const normalizedWeights = {}
    Object.entries(weights.value).forEach(([key, value]) => {
      normalizedWeights[key] = value / 100
    })
    
    const requestData = {
      origin_id: Number(props.originId),
      destination_id: Number(props.destinationId),
      weights: normalizedWeights,
      algorithm: algorithm.value
    }
    
    console.log('优化请求:', JSON.stringify(requestData, null, 2))
    
    const res = await optimizeRoute(requestData)
    
    console.log('优化响应:', res)
    
    if (res.success) {
      result.value = res
      selectedRecommendation.value = 0
      emit('result', res)
      console.log('优化成功，推荐方案数:', res.recommendations?.length, '算法:', algorithm.value)
      ElMessage.success(`优化完成！找到 ${res.recommendations?.length || 0} 个方案`)
    } else {
      ElMessage.error(res.error || '优化失败')
    }
  } catch (error) {
    console.error('优化失败:', error)
    // 显示后端返回的错误信息
    const errorMsg = error.response?.data?.error || error.response?.data?.message || error.message || '优化失败，请稍后重试'
    ElMessage.error(errorMsg)
  } finally {
    loading.value = false
  }
}

// 选择推荐方案
function selectRecommendation(index) {
  selectedRecommendation.value = index
  const rec = result.value?.recommendations?.[index]
  if (rec) {
    emit('select', rec)
  }
}

// 获取类型标签
function getTypeLabel(type) {
  const labels = {
    weighted_best: '🏆 综合',
    pareto: '⚖️ 均衡',
    single_objective: '📌 单项'
  }
  return labels[type] || type
}

// 获取目标标签
function getObjectiveLabel(key) {
  const labels = {
    distance: '距离',
    time: '时间',
    cost: '成本',
    traffic: '路况',
    weather_risk: '天气风险'
  }
  return labels[key] || key
}

// 格式化数值
function formatValue(key, value) {
  const units = {
    distance: 'km',
    time: 'min',
    cost: '元',
    traffic: '分',
    weather_risk: '%'
  }
  return `${value.toFixed(1)}${units[key] || ''}`
}

onMounted(() => {
  fetchObjectives()
})

// 监听起终点变化
watch([() => props.originId, () => props.destinationId], () => {
  result.value = null
  selectedRecommendation.value = 0
})
</script>

<style scoped>
.multi-objective-panel {
  padding: 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h3,
.algorithm-section h3,
.result-section h3 {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.weights-section {
  margin-bottom: 20px;
}

.weights-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.weights-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e4e7ed;
  font-size: 14px;
  color: #606266;
}

.weight-warning {
  color: #F56C6C;
  font-size: 12px;
}

.algorithm-section {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.algorithm-section h3 {
  margin-bottom: 12px;
}

.action-section {
  margin-bottom: 20px;
  text-align: center;
}

.action-section .el-button {
  width: 100%;
}

.result-section {
  border-top: 1px solid #e4e7ed;
  padding-top: 16px;
}

.result-section h3 {
  margin-bottom: 12px;
}

.recommendations {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recommendation-card {
  padding: 12px 16px;
  background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%);
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.recommendation-card:hover {
  border-color: #409EFF;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.15);
}

.recommendation-card.active {
  border-color: #409EFF;
  background: linear-gradient(135deg, #ecf5ff 0%, #fff 100%);
}

.rec-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.rec-type {
  font-size: 12px;
  color: #409EFF;
  font-weight: 500;
}

.rec-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.rec-desc {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.rec-objectives {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.obj-tag {
  font-size: 12px;
  padding: 2px 8px;
  background: #f0f2f5;
  border-radius: 4px;
  color: #606266;
}
</style>
