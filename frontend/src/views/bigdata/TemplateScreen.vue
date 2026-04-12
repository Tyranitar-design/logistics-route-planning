<template>
  <div class="bigdata-screen">
    <!-- 直接嵌入模板 HTML 结构 -->
    <iframe 
      ref="templateFrame" 
      src="/templates/logistics-bigdata/index.html" 
      class="template-iframe"
      @load="onTemplateLoad"
    ></iframe>
    
    <!-- 数据注入覆盖层 -->
    <div class="data-overlay" v-if="dataReady">
      <!-- 这里可以添加实时数据浮窗 -->
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const templateFrame = ref(null)
const dataReady = ref(false)

// 模板加载完成后注入数据
const onTemplateLoad = () => {
  const iframe = templateFrame.value
  if (!iframe) return
  
  try {
    const iframeWindow = iframe.contentWindow
    const iframeDoc = iframe.contentDocument
    
    // 获取真实数据并注入到模板
    injectRealData(iframeWindow, iframeDoc)
    dataReady.value = true
  } catch (e) {
    console.log('跨域限制，使用备用方案')
  }
}

// 注入真实数据
const injectRealData = async (win, doc) => {
  try {
    // 获取后端数据
    const response = await fetch('/api/orders/stats')
    const data = await response.json()
    
    // 更新模板中的数据
    // 这里可以根据模板的数据结构进行适配
  } catch (e) {
    console.error('数据注入失败:', e)
  }
}

onMounted(() => {
  // 如果需要，可以在这里添加更多逻辑
})
</script>

<style scoped>
.bigdata-screen {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.template-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.data-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}
</style>
