<template>
  <div class="weight-slider">
    <div class="weight-header">
      <span class="weight-title">{{ title }}</span>
      <el-tag size="small" type="info">{{ totalWeightPercent }}%</el-tag>
    </div>
    
    <div class="weight-content">
      <el-slider
        v-model="localValue"
        :min="0"
        :max="100"
        :step="5"
        :format-tooltip="(val) => `${val}%`"
        @input="handleInput"
        @change="handleChange"
      />
      
      <div class="weight-labels">
        <span class="label-low">不重要</span>
        <span class="label-high">非常重要</span>
      </div>
    </div>
    
    <div class="weight-icon">
      <el-icon :size="20" :color="iconColor">
        <component :is="icon" />
      </el-icon>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { 
  Location, 
  Timer, 
  Money, 
  TrendCharts, 
  Cloudy 
} from '@element-plus/icons-vue'

const props = defineProps({
  objective: {
    type: String,
    required: true
  },
  title: {
    type: String,
    required: true
  },
  modelValue: {
    type: Number,
    default: 25
  },
  unit: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localValue = ref(props.modelValue)

// 图标映射
const iconMap = {
  distance: Location,
  time: Timer,
  cost: Money,
  traffic: TrendCharts,
  weather_risk: Cloudy
}

const icon = computed(() => iconMap[props.objective] || Location)

// 图标颜色
const iconColor = computed(() => {
  if (localValue.value >= 40) return '#67C23A'
  if (localValue.value >= 20) return '#409EFF'
  return '#909399'
})

const totalWeightPercent = computed(() => localValue.value)

watch(() => props.modelValue, (val) => {
  localValue.value = val
})

function handleInput(val) {
  emit('update:modelValue', val)
}

function handleChange(val) {
  emit('change', { objective: props.objective, value: val })
}
</script>

<style scoped>
.weight-slider {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  transition: all 0.3s ease;
}

.weight-slider:hover {
  border-color: #409EFF;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.15);
}

.weight-header {
  min-width: 100px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.weight-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.weight-content {
  flex: 1;
  padding: 0 8px;
}

.weight-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
}

.label-low,
.label-high {
  font-size: 12px;
  color: #909399;
}

.weight-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border-radius: 10px;
}

:deep(.el-slider__runway) {
  height: 8px;
  background: linear-gradient(90deg, #e4e7ed 0%, #c0c4cc 100%);
  border-radius: 4px;
}

:deep(.el-slider__bar) {
  height: 8px;
  background: linear-gradient(90deg, #409EFF 0%, #67C23A 100%);
  border-radius: 4px;
}

:deep(.el-slider__button) {
  width: 18px;
  height: 18px;
  border: 3px solid #409EFF;
  background: #fff;
}
</style>
