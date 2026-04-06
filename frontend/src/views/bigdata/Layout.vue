<template>
  <div class="bigdata-layout">
    <!-- 顶部标题栏 -->
    <div class="bigdata-header">
      <div class="header-left">
        <h1>📊 大数据分析平台</h1>
        <span class="subtitle">实时监控 · 全文搜索 · 智能分析 · 任务调度</span>
      </div>
      <div class="header-right">
        <el-tag type="success" effect="dark">
          <el-icon><Connection /></el-icon>
          系统运行中
        </el-tag>
        <el-button type="primary" @click="goBack" text>
          <el-icon><Back /></el-icon>
          返回主系统
        </el-button>
      </div>
    </div>

    <!-- 侧边导航 -->
    <div class="bigdata-sidebar">
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#1a1a2e"
        text-color="#a0a0a0"
        active-text-color="#00d4ff"
      >
        <el-menu-item index="/bigdata/monitor">
          <el-icon><Monitor /></el-icon>
          <span>实时监控</span>
        </el-menu-item>
        <el-menu-item index="/bigdata/search">
          <el-icon><Search /></el-icon>
          <span>全文搜索</span>
        </el-menu-item>
        <el-menu-item index="/bigdata/analytics">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据分析</span>
        </el-menu-item>
        <el-menu-item index="/bigdata/scheduler">
          <el-icon><Timer /></el-icon>
          <span>任务调度</span>
        </el-menu-item>
        <el-menu-item index="/bigdata/spark">
          <el-icon><Lightning /></el-icon>
          <span>Spark处理</span>
        </el-menu-item>
        <el-menu-item index="/bigdata/dl-studio">
          <el-icon><Cpu /></el-icon>
          <span>深度学习</span>
        </el-menu-item>
        <el-menu-item index="/bigdata/visual">
          <el-icon><DataLine /></el-icon>
          <span>数据可视化</span>
        </el-menu-item>
      </el-menu>

      <!-- 服务状态 -->
      <div class="service-status">
        <h4>服务状态</h4>
        <div class="status-item" v-for="service in services" :key="service.name">
          <span class="status-dot" :class="service.status"></span>
          <span class="status-name">{{ service.name }}</span>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="bigdata-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Monitor, Search, DataAnalysis, Timer, Lightning, Connection, Back } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

const activeMenu = computed(() => route.path)

const services = ref([
  { name: 'Prometheus', status: 'online' },
  { name: 'Grafana', status: 'online' },
  { name: 'Elasticsearch', status: 'online' },
  { name: 'ClickHouse', status: 'online' },
  { name: 'Airflow', status: 'online' },
  { name: 'Kafka', status: 'online' },
  { name: 'Spark', status: 'online' }
])

const goBack = () => {
  router.push('/')
}
</script>

<style scoped>
.bigdata-layout {
  display: flex;
  height: 100vh;
  background: #0f0f1a;
  color: #fff;
}

.bigdata-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  z-index: 100;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
  color: #00d4ff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.subtitle {
  margin-left: 16px;
  font-size: 12px;
  color: #666;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.bigdata-sidebar {
  position: fixed;
  top: 60px;
  left: 0;
  width: 200px;
  height: calc(100vh - 60px);
  background: #1a1a2e;
  border-right: 1px solid rgba(0, 212, 255, 0.1);
}

.el-menu {
  border-right: none;
}

.el-menu-item {
  height: 50px;
  line-height: 50px;
}

.el-menu-item:hover {
  background: rgba(0, 212, 255, 0.1) !important;
}

.el-menu-item.is-active {
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.2) 0%, transparent 100%) !important;
  border-left: 3px solid #00d4ff;
}

.service-status {
  position: absolute;
  bottom: 20px;
  left: 16px;
  right: 16px;
}

.service-status h4 {
  color: #666;
  font-size: 12px;
  margin-bottom: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #888;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.online {
  background: #00ff88;
  box-shadow: 0 0 8px #00ff88;
}

.status-dot.offline {
  background: #ff4444;
}

.bigdata-content {
  margin-left: 200px;
  margin-top: 60px;
  flex: 1;
  padding: 20px;
  overflow: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
