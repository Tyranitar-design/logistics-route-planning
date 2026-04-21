<template>
  <el-container class="layout-container">
    <!-- 移动端遮罩层 -->
    <div 
      v-if="isMobile && sidebarCollapsed === false" 
      class="mobile-overlay"
      @click="sidebarCollapsed = true"
    ></div>
    
    <!-- 侧边栏 -->
    <el-aside 
      :width="isMobile ? '220px' : (sidebarCollapsed ? '0px' : '220px')" 
      class="sidebar"
      :class="{ 'sidebar-hidden': sidebarCollapsed, 'sidebar-mobile': isMobile }"
    >
      <div class="logo">
        <h2>🚚 物流系统</h2>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/">
          <el-icon><DataAnalysis /></el-icon>
          <span>{{ t('menu.dashboard') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/map">
          <el-icon><Location /></el-icon>
          <span>{{ t('menu.map') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/earth3d">
          <el-icon><Promotion /></el-icon>
          <span>{{ t('menu.earth3d') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/data-screen">
          <el-icon><DataAnalysis /></el-icon>
          <span>{{ t('menu.dataScreen') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/big-data">
          <el-icon><DataBoard /></el-icon>
          <span>大数据大屏</span>
        </el-menu-item>
        
        <el-menu-item index="/nodes">
          <el-icon><OfficeBuilding /></el-icon>
          <span>{{ t('menu.nodes') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/routes">
          <el-icon><Connection /></el-icon>
          <span>{{ t('menu.routes') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/orders">
          <el-icon><Box /></el-icon>
          <span>{{ t('menu.orders') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/dispatch">
          <el-icon><Grid /></el-icon>
          <span>{{ t('menu.dispatch') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/advanced-route">
          <el-icon><Cpu /></el-icon>
          <span>{{ t('menu.advanced') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/tracking">
          <el-icon><VideoPlay /></el-icon>
          <span>{{ t('menu.tracking') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/multi-objective">
          <el-icon><Aim /></el-icon>
          <span>{{ t('menu.multiObjective') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/agile">
          <el-icon><Lightning /></el-icon>
          <span>敏捷优化</span>
        </el-menu-item>
        
        <el-menu-item index="/network-design">
          <el-icon><Share /></el-icon>
          <span>网络设计</span>
        </el-menu-item>
        
        <el-menu-item index="/optimization-engine">
          <el-icon><TrendCharts /></el-icon>
          <span>优化引擎</span>
        </el-menu-item>
        
        <el-menu-item index="/pareto-front">
          <el-icon><Aim /></el-icon>
          <span>Pareto前沿</span>
        </el-menu-item>
        
        <el-menu-item index="/risk">
          <el-icon><Warning /></el-icon>
          <span>风险管理</span>
        </el-menu-item>
        
        <el-menu-item index="/alert">
          <el-icon><Bell /></el-icon>
          <span>预警中心</span>
        </el-menu-item>
        
        <el-menu-item index="/cost">
          <el-icon><TrendCharts /></el-icon>
          <span>成本分析</span>
        </el-menu-item>
        
        <el-menu-item index="/analytics">
          <el-icon><DataLine /></el-icon>
          <span>{{ t('menu.analytics') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/ml-prediction">
          <el-icon><Cpu /></el-icon>
          <span>{{ t('menu.mlPrediction') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/advanced-features">
          <el-icon><MagicStick /></el-icon>
          <span>{{ t('menu.advanced') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/anomaly-detection">
          <el-icon><Warning /></el-icon>
          <span>{{ t('menu.anomaly') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/data-analytics">
          <el-icon><DataLine /></el-icon>
          <span>{{ t('menu.dataAnalytics') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/suppliers">
          <el-icon><Shop /></el-icon>
          <span>{{ t('menu.supplier') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/vehicles">
          <el-icon><Van /></el-icon>
          <span>{{ t('menu.vehicles') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/users" v-if="isAdmin">
          <el-icon><User /></el-icon>
          <span>{{ t('menu.users') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/audit-log">
          <el-icon><Document /></el-icon>
          <span>{{ t('menu.auditLog') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/test-data">
          <el-icon><SetUp /></el-icon>
          <span>{{ t('menu.testData') }}</span>
        </el-menu-item>
        
        <el-menu-item index="/data-collection">
          <el-icon><Download /></el-icon>
          <span>📊 数据采集</span>
        </el-menu-item>
        
        <el-menu-item index="/redis-monitor">
          <el-icon><Coin /></el-icon>
          <span>⚡ Redis 监控</span>
        </el-menu-item>
        
        <el-menu-item index="/bigdata/monitor">
          <el-icon><Monitor /></el-icon>
          <span>📊 大数据分析</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <!-- 移动端汉堡菜单按钮 -->
          <el-button 
            v-if="isMobile"
            class="hamburger-btn"
            :icon="sidebarCollapsed ? Expand : Fold"
            @click="toggleSidebar"
            text
          />
          <span class="page-title">{{ pageTitle }}</span>
        </div>
        
        <div class="header-right">
          <!-- 语言切换 -->
          <LangSwitch style="margin-right: 16px;" />
          
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" style="background: #409EFF">
                {{ userInfo?.real_name?.charAt(0) || 'A' }}
              </el-avatar>
              <span class="username">{{ userInfo?.real_name || '用户' }}</span>
              <el-tag 
                :type="isAdmin ? 'danger' : 'success'" 
                size="small" 
                style="margin-left: 8px;"
              >
                {{ isAdmin ? '管理员' : '普通用户' }}
              </el-tag>
              <el-icon style="margin-left: 4px;"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <!-- 内容区 -->
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
  
  <!-- 实时推送通知组件 -->
  <RealtimeNotification />
  
  <!-- 智能客服组件 -->
  <AiChat />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, TrendCharts, Grid, Promotion, DataLine, Cpu, Lightning, Warning, Bell, MagicStick, Expand, Fold, Shop, Van, User, Document, SetUp, DataBoard, Monitor, Download, Coin, Share, Platform } from '@element-plus/icons-vue'
import RealtimeNotification from '@/components/RealtimeNotification.vue'
import AiChat from '@/components/AiChat.vue'
import LangSwitch from '@/components/LangSwitch.vue'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()

const userInfo = ref(null)
const loading = ref(false)

// 移动端适配
const isMobile = ref(false)
const sidebarCollapsed = ref(true) // 移动端默认折叠

const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) {
    sidebarCollapsed.value = false // 桌面端默认展开
  }
}

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

const activeMenu = computed(() => route.path)

const pageTitle = computed(() => {
  const titles = {
    '/': t('menu.dashboard'),
    '/map': t('menu.map', '地图视图'),
    '/earth3d': '3D 地球可视化',
    '/nodes': t('menu.nodes'),
    '/routes': t('menu.routes'),
    '/orders': t('menu.orders'),
    '/dispatch': t('menu.dispatch', '智能调度'),
    '/advanced-route': t('menu.advanced', '高级路径优化'),
    '/tracking': t('menu.tracking', '轨迹模拟'),
    '/multi-objective': t('menu.multiObjective', '多目标路径优化'),
    '/agile': t('menu.agile'),
    '/risk': t('menu.risk'),
    '/alert': t('menu.alert'),
    '/cost': t('menu.cost'),
    '/analytics': t('menu.analytics'),
    '/ml-prediction': t('menu.mlPrediction'),
    '/advanced-features': t('menu.advanced', '高级功能中心'),
    '/anomaly-detection': t('menu.anomaly', '实时异常检测中心'),
    '/data-analytics': t('menu.dataAnalytics', '数据分析中心'),
    '/network-design': '网络设计',
    '/optimization-engine': '优化引擎',
    '/pareto-front': 'Pareto前沿',
    '/scenario-compare': '场景对比',
    '/suppliers': t('menu.supplier'),
    '/vehicles': '车辆管理',
    '/users': '用户管理',
    '/audit-log': '审计日志',
    '/test-data': '测试数据生成',
    '/data-collection': '数据采集中心',
    '/redis-monitor': 'Redis 实时监控',
    '/big-data': '大数据大屏',
    '/network-design': '物流网络设计'
  }
  return titles[route.path] || '物流路径规划系统'
})

const isAdmin = computed(() => {
  return userInfo.value?.role === 'admin'
})

// 是否有编辑权限
const canEdit = computed(() => {
  return userInfo.value?.role === 'admin'
})

onMounted(() => {
  // 检测移动端
  checkMobile()
  window.addEventListener('resize', checkMobile)
  
  // 从localStorage获取用户信息
  const userStr = localStorage.getItem('user')
  if (userStr) {
    try {
      userInfo.value = JSON.parse(userStr)
    } catch (e) {
      console.error('解析用户信息失败:', e)
    }
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

const handleCommand = (command) => {
  switch (command) {
    case 'profile':
      ElMessage.info('个人信息功能开发中')
      break
    case 'password':
      ElMessage.info('修改密码功能开发中')
      break
    case 'logout':
      handleLogout()
      break
  }
}

const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    type: 'warning'
  }).then(() => {
    // 清除本地存储
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    
    ElMessage.success('已退出登录')
    router.push('/login')
  }).catch(() => {})
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

/* 移动端遮罩层 */
.mobile-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
}

.sidebar {
  background-color: #304156;
  overflow-x: hidden;
  transition: width 0.3s ease, transform 0.3s ease;
}

/* 移动端侧边栏 */
.sidebar.sidebar-mobile {
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  z-index: 1000;
  width: 220px !important;
}

.sidebar.sidebar-hidden {
  transform: translateX(-100%);
}

/* 桌面端隐藏状态 */
@media (min-width: 768px) {
  .sidebar.sidebar-hidden {
    transform: translateX(0);
    width: 0 !important;
    overflow: hidden;
  }
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-bottom: 1px solid #3a4a5d;
}

.logo h2 {
  margin: 0;
  font-size: 18px;
}

.sidebar :deep(.el-menu) {
  border-right: none;
}

.header {
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.hamburger-btn {
  font-size: 20px;
  padding: 8px;
}

.page-title {
  font-size: 18px;
  font-weight: 500;
  color: #303133;
}

/* 移动端页面标题 */
@media (max-width: 768px) {
  .page-title {
    font-size: 16px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 150px;
  }
  
  .header {
    padding: 0 10px;
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

/* 移动端用户信息 */
@media (max-width: 768px) {
  .user-info .username {
    display: none;
  }
}

.username {
  color: #606266;
}

.main {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}

/* 移动端主内容区 */
@media (max-width: 768px) {
  .main {
    padding: 10px;
  }
}
</style>
