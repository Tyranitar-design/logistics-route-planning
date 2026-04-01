<template>
  <span class="count-up">{{ displayValue }}</span>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  endValue: {
    type: Number,
    required: true
  },
  duration: {
    type: Number,
    default: 2000
  },
  decimals: {
    type: Number,
    default: 0
  },
  prefix: {
    type: String,
    default: ''
  },
  suffix: {
    type: String,
    default: ''
  },
  separator: {
    type: String,
    default: ','
  }
})

const displayValue = ref('0')

// 格式化数字
const formatNumber = (num) => {
  const fixed = num.toFixed(props.decimals)
  const parts = fixed.split('.')
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, props.separator)
  return props.prefix + parts.join('.') + props.suffix
}

// 动画函数
const animate = () => {
  const startTime = performance.now()
  const startValue = 0
  const endValue = props.endValue
  
  const step = (currentTime) => {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / props.duration, 1)
    
    // 使用 easeOutExpo 缓动函数
    const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
    
    const currentValue = startValue + (endValue - startValue) * easeProgress
    displayValue.value = formatNumber(currentValue)
    
    if (progress < 1) {
      requestAnimationFrame(step)
    }
  }
  
  requestAnimationFrame(step)
}

// 监听值变化
watch(() => props.endValue, () => {
  animate()
})

onMounted(() => {
  animate()
})
</script>

<style scoped>
.count-up {
  font-variant-numeric: tabular-nums;
}
</style>
