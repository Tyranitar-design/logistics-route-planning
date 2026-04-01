<template>
  <div class="earth-page">
    <!-- 顶部标题 -->
    <div class="page-header">
      <div class="header-left">
        <h1>🌍 3D 地球可视化</h1>
        <span class="subtitle">Global Logistics Visualization</span>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="refreshData">
          <span class="btn-icon">🔄</span>
          刷新数据
        </el-button>
        <el-button @click="goBack">
          <span class="btn-icon">←</span>
          返回
        </el-button>
      </div>
    </div>
    
    <!-- 地球组件 -->
    <div class="earth-wrapper">
      <Earth3D ref="earthRef" />
    </div>
    
    <!-- 底部信息 -->
    <div class="page-footer">
      <div class="footer-tips">
        <span class="tip-item">🖱️ 拖拽旋转</span>
        <span class="tip-item">🔍 滚轮缩放</span>
        <span class="tip-item">👆 点击查看详情</span>
      </div>
      <div class="footer-time">
        最后更新: {{ lastUpdate }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Earth3D from '@/components/Earth3D.vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const earthRef = ref(null)
const lastUpdate = ref('')

const refreshData = async () => {
  lastUpdate.value = new Date().toLocaleString('zh-CN')
  ElMessage.success('数据已刷新')
}

const goBack = () => {
  router.push('/dashboard')
}

onMounted(() => {
  lastUpdate.value = new Date().toLocaleString('zh-CN')
})
</script>

<style scoped>
.earth-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 50%, #0d1033 100%);
  display: flex;
  flex-direction: column;
  color: #fff;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: rgba(0, 212, 255, 0.05);
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
}

.header-left h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(90deg, #00d4ff, #00ff88);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 2px;
  text-transform: uppercase;
}

.header-right {
  display: flex;
  gap: 12px;
}

.btn-icon {
  margin-right: 6px;
}

.earth-wrapper {
  flex: 1;
  position: relative;
  min-height: calc(100vh - 140px);
}

.page-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: rgba(0, 212, 255, 0.05);
  border-top: 1px solid rgba(0, 212, 255, 0.2);
}

.footer-tips {
  display: flex;
  gap: 24px;
}

.tip-item {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
}

.footer-time {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

/* Element Plus 覆盖 */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #00d4ff, #0088cc);
  border-color: #00d4ff;
}

:deep(.el-button) {
  background: rgba(0, 212, 255, 0.1);
  border-color: rgba(0, 212, 255, 0.3);
  color: #fff;
}

:deep(.el-button:hover) {
  background: rgba(0, 212, 255, 0.2);
  border-color: #00d4ff;
}
</style>
