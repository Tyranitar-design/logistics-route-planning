<template>
  <div class="command-shell">
    <div
      v-if="isMobile && !sidebarCollapsed"
      class="mobile-overlay"
      @click="sidebarCollapsed = true"
    ></div>

    <aside
      class="command-sidebar"
      :class="{ 'command-sidebar--hidden': sidebarCollapsed, 'command-sidebar--mobile': isMobile }"
    >
      <div class="command-sidebar__brand">
        <div class="brand-mark">L</div>
        <div class="brand-copy">
          <h1>物流指挥中枢</h1>
          <p>Logistics Command Center</p>
        </div>
      </div>

      <el-scrollbar class="command-sidebar__scroll">
        <section
          v-for="group in navigationGroups"
          :key="group.key"
          class="nav-group"
        >
          <div class="nav-group__title">
            <span class="nav-group__line"></span>
            <span>{{ group.title }}</span>
          </div>

          <button
            v-for="item in group.items"
            :key="item.index"
            class="nav-item"
            :class="{ 'nav-item--active': isRouteActive(item.index) }"
            type="button"
            @click="navigateTo(item.index)"
          >
            <span class="nav-item__glow"></span>
            <span class="nav-item__icon">
              <el-icon><component :is="item.icon" /></el-icon>
            </span>
            <span class="nav-item__content">
              <span class="nav-item__label">{{ item.label }}</span>
              <span class="nav-item__hint">{{ item.hint }}</span>
            </span>
          </button>
        </section>
      </el-scrollbar>
    </aside>

    <div class="command-workspace">
      <header class="command-header">
        <div class="command-header__left">
          <el-button
            v-if="isMobile"
            class="hamburger-btn"
            :icon="sidebarCollapsed ? Expand : Fold"
            @click="toggleSidebar"
            text
          />

          <div class="page-intro">
            <span class="cc-kicker">Command Layer</span>
            <div class="page-intro__title-row">
              <h2 class="page-title">{{ pageTitle }}</h2>
              <span class="page-zone">{{ currentZoneTitle }}</span>
            </div>
          </div>
        </div>

        <div class="command-header__right">
          <div class="header-pill">
            <span class="cc-dot"></span>
            <span>系统在线</span>
          </div>
          <div class="header-pill header-pill--accent">
            <span>策略模式</span>
            <strong>{{ strategyModeLabel }}</strong>
          </div>
          <div class="header-clock">
            <strong>{{ currentTimeLabel }}</strong>
            <span>{{ currentDateLabel }}</span>
          </div>
          <LangSwitch />

          <el-dropdown @command="handleCommand">
            <span class="user-anchor">
              <el-avatar :size="34" class="user-avatar">
                {{ userInitial }}
              </el-avatar>
              <span class="user-anchor__meta">
                <strong>{{ userName }}</strong>
                <small>{{ isAdmin ? '管理员视图' : '业务操作视图' }}</small>
              </span>
              <el-icon><ArrowDown /></el-icon>
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
      </header>

      <section
        v-if="!route.meta.fullscreen"
        class="command-status-strip cc-panel"
      >
        <div class="status-chip">
          <span class="status-chip__label">当前分区</span>
          <strong>{{ currentZoneTitle }}</strong>
        </div>
        <div class="status-chip status-chip--success">
          <span class="status-chip__label">运行态势</span>
          <strong>稳定</strong>
        </div>
        <div class="status-chip status-chip--info">
          <span class="status-chip__label">策略模式</span>
          <strong>{{ strategyModeLabel }}</strong>
        </div>
        <div class="status-chip status-chip--warning">
          <span class="status-chip__label">页面类型</span>
          <strong>{{ route.meta.fullscreen ? '沉浸式' : '指挥台' }}</strong>
        </div>
      </section>

      <main
        class="command-main-stage"
        :class="{ 'command-main-stage--fullscreen': route.meta.fullscreen }"
      >
        <router-view />
      </main>
    </div>

    <RealtimeNotification />
    <AiChat />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Aim,
  ArrowDown,
  Bell,
  Box,
  Coin,
  Connection,
  Cpu,
  DataAnalysis,
  DataBoard,
  DataLine,
  Document,
  Download,
  Expand,
  Fold,
  Grid,
  Lightning,
  Location,
  MagicStick,
  Monitor,
  OfficeBuilding,
  Promotion,
  SetUp,
  Share,
  Shop,
  TrendCharts,
  User,
  Van,
  VideoPlay,
  Warning
} from '@element-plus/icons-vue'
import AiChat from '@/components/AiChat.vue'
import LangSwitch from '@/components/LangSwitch.vue'
import RealtimeNotification from '@/components/RealtimeNotification.vue'

const router = useRouter()
const route = useRoute()

const userInfo = ref(null)
const isMobile = ref(false)
const sidebarCollapsed = ref(true)
const currentTimeLabel = ref('--:--:--')
const currentDateLabel = ref('----')

let clockTimer = null

const rawNavigationGroups = [
  {
    key: 'overview',
    title: '总览态势',
    items: [
      { index: '/', label: '指挥总览', hint: '首页总览与态势感知', icon: DataAnalysis },
      { index: '/map', label: '地图视图', hint: '路网与节点空间态势', icon: Location },
      { index: '/earth3d', label: '3D 地球', hint: '三维地理与全球视角', icon: Promotion },
      { index: '/data-screen', label: '数据大屏', hint: '沉浸式可视化展示', icon: Monitor },
      { index: '/big-data', label: '大数据大屏', hint: '平台级大屏监控', icon: DataBoard }
    ]
  },
  {
    key: 'dispatch',
    title: '调度执行',
    items: [
      { index: '/dispatch', label: '智能调度', hint: '订单与运力编排', icon: Grid },
      { index: '/tracking', label: '轨迹监控', hint: '路线回放与执行追踪', icon: VideoPlay },
      { index: '/orders', label: '订单管理', hint: '订单池与执行状态', icon: Box },
      { index: '/vehicles', label: '车辆管理', hint: '车队与资源配置', icon: Van },
      { index: '/nodes', label: '节点管理', hint: '仓站与配送节点', icon: OfficeBuilding },
      { index: '/routes', label: '路线管理', hint: '线路与连接关系', icon: Connection }
    ]
  },
  {
    key: 'optimization',
    title: '优化决策',
    items: [
      { index: '/optimization-engine', label: '优化引擎', hint: '求解与方案对比', icon: TrendCharts },
      { index: '/multi-objective', label: '多目标优化', hint: '真实 Pareto 决策', icon: Aim },
      { index: '/pareto-front', label: 'Pareto 前沿', hint: '多方案权衡可视化', icon: Aim },
      { index: '/advanced-route', label: '高级路径', hint: '约束强化与高级求解', icon: Cpu },
      { index: '/agile', label: '敏捷优化', hint: '快节奏方案迭代', icon: Lightning },
      { index: '/network-design', label: '网络设计', hint: '仓网布局与选址', icon: Share },
      { index: '/scenario-compare', label: '场景对比', hint: '情景分析与策略复盘', icon: DataAnalysis }
    ]
  },
  {
    key: 'insights',
    title: '洞察预警',
    items: [
      { index: '/risk', label: '风险管理', hint: '风险画像与策略干预', icon: Warning },
      { index: '/alert', label: '预警中心', hint: '异常与告警流', icon: Bell },
      { index: '/cost', label: '成本分析', hint: '成本结构与趋势', icon: TrendCharts },
      { index: '/analytics', label: '分析总览', hint: '统计报表与表现监控', icon: DataLine },
      { index: '/ml-prediction', label: 'AI 预测', hint: '预测与智能判断', icon: Cpu },
      { index: '/advanced-features', label: '高级功能', hint: '增强能力与扩展模块', icon: MagicStick },
      { index: '/anomaly-detection', label: '异常检测', hint: '实时识别与追踪', icon: Warning },
      { index: '/data-analytics', label: '数据分析', hint: '运营分析与洞察', icon: DataLine }
    ]
  },
  {
    key: 'platform',
    title: '平台与治理',
    items: [
      { index: '/suppliers', label: '供应商管理', hint: '业务协同与生态管理', icon: Shop },
      { index: '/data-collection', label: '数据采集', hint: '采集链路与任务状态', icon: Download },
      { index: '/redis-monitor', label: 'Redis 监控', hint: '缓存与实时运行监控', icon: Coin },
      { index: '/bigdata/monitor', label: '大数据分析', hint: '流处理与平台监控', icon: DataBoard },
      { index: '/audit-log', label: '审计日志', hint: '操作留痕与追溯', icon: Document },
      { index: '/test-data', label: '测试数据', hint: '演示与验证支撑', icon: SetUp },
      { index: '/users', label: '用户管理', hint: '权限与账户治理', icon: User, adminOnly: true }
    ]
  }
]

const checkMobile = () => {
  isMobile.value = window.innerWidth < 1024
  sidebarCollapsed.value = isMobile.value
}

const updateClock = () => {
  const now = new Date()
  currentTimeLabel.value = now.toLocaleTimeString('zh-CN', { hour12: false })
  currentDateLabel.value = now.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'short'
  })
}

const isAdmin = computed(() => userInfo.value?.role === 'admin')

const navigationGroups = computed(() =>
  rawNavigationGroups.map((group) => ({
    ...group,
    items: group.items.filter((item) => !item.adminOnly || isAdmin.value)
  }))
)

const flattenedNavigation = computed(() =>
  navigationGroups.value.flatMap((group) =>
    group.items.map((item) => ({
      ...item,
      groupTitle: group.title
    }))
  )
)

const userName = computed(() => userInfo.value?.real_name || '系统用户')
const userInitial = computed(() => userName.value.charAt(0).toUpperCase())

const strategyModeLabel = computed(() => {
  if (route.path.includes('optimization')) return '优化决策模式'
  if (route.path.includes('dispatch') || route.path.includes('tracking')) return '实时执行模式'
  if (route.path.includes('risk') || route.path.includes('alert')) return '风控监测模式'
  return '平台总览模式'
})

const currentNavItem = computed(() =>
  flattenedNavigation.value.find((item) => isRouteActive(item.index))
)

const currentZoneTitle = computed(() => currentNavItem.value?.groupTitle || '总览态势')
const pageTitle = computed(() => currentNavItem.value?.label || '物流指挥中枢')

function isRouteActive(target) {
  if (target === '/') {
    return route.path === '/'
  }
  return route.path === target || route.path.startsWith(`${target}/`)
}

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

const navigateTo = (path) => {
  router.push(path)
  if (isMobile.value) {
    sidebarCollapsed.value = true
  }
}

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
    default:
      break
  }
}

const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    type: 'warning'
  })
    .then(() => {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
      ElMessage.success('已退出登录')
      router.push('/login')
    })
    .catch(() => {})
}

onMounted(() => {
  checkMobile()
  updateClock()
  clockTimer = window.setInterval(updateClock, 1000)
  window.addEventListener('resize', checkMobile)

  const userStr = localStorage.getItem('user')
  if (userStr) {
    try {
      userInfo.value = JSON.parse(userStr)
    } catch (error) {
      console.error('解析用户信息失败:', error)
    }
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  if (clockTimer) {
    window.clearInterval(clockTimer)
  }
})
</script>

<style scoped>
.command-shell {
  position: relative;
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  min-height: 100vh;
  background:
    radial-gradient(circle at left top, rgba(0, 212, 255, 0.08), transparent 24%),
    linear-gradient(160deg, rgba(4, 11, 20, 0.88), rgba(7, 17, 31, 0.96));
}

.mobile-overlay {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 14, 0.72);
  backdrop-filter: blur(6px);
  z-index: 40;
}

.command-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 20px 16px 18px;
  background:
    linear-gradient(180deg, rgba(8, 18, 32, 0.98), rgba(5, 12, 24, 0.92));
  border-right: 1px solid var(--cc-border);
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.03);
  z-index: 50;
  transition: transform 0.3s ease, width 0.3s ease;
}

.command-sidebar--mobile {
  position: fixed;
  width: 300px;
  max-width: calc(100vw - 32px);
}

.command-sidebar--hidden {
  transform: translateX(-100%);
}

.command-sidebar__brand {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 8px 8px 16px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.26), rgba(17, 224, 183, 0.22));
  border: 1px solid rgba(0, 212, 255, 0.24);
  color: var(--cc-text-primary);
  font-weight: 700;
  letter-spacing: 0.08em;
  box-shadow: var(--cc-shadow-glow);
}

.brand-copy h1 {
  margin: 0;
  font-size: 18px;
  color: var(--cc-text-primary);
}

.brand-copy p {
  margin: 4px 0 0;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--cc-text-muted);
}

.command-sidebar__scroll {
  height: calc(100vh - 110px);
  padding-right: 4px;
}

.nav-group {
  margin-bottom: 18px;
}

.nav-group__title {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 8px;
  margin-bottom: 10px;
  color: var(--cc-text-muted);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.nav-group__line {
  width: 18px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--cc-cyan));
}

.nav-item {
  position: relative;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  margin-bottom: 8px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  color: var(--cc-text-secondary);
  text-align: left;
  cursor: pointer;
  transition: transform 0.24s ease, border-color 0.24s ease, background 0.24s ease;
}

.nav-item:hover {
  transform: translateX(4px);
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(0, 212, 255, 0.16);
  color: var(--cc-text-primary);
}

.nav-item--active {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.14), rgba(17, 224, 183, 0.06));
  border-color: rgba(0, 212, 255, 0.34);
  color: var(--cc-text-primary);
  box-shadow: var(--cc-shadow-glow);
}

.nav-item--active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 999px;
  background: linear-gradient(180deg, var(--cc-cyan), var(--cc-teal));
}

.nav-item__glow {
  position: absolute;
  inset: 0;
  border-radius: 14px;
  background: radial-gradient(circle at left center, rgba(0, 212, 255, 0.14), transparent 55%);
  opacity: 0;
  transition: opacity 0.24s ease;
}

.nav-item:hover .nav-item__glow,
.nav-item--active .nav-item__glow {
  opacity: 1;
}

.nav-item__icon {
  position: relative;
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 18px;
}

.nav-item__content {
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.nav-item__label {
  font-size: 14px;
  font-weight: 600;
}

.nav-item__hint {
  margin-top: 3px;
  font-size: 12px;
  color: var(--cc-text-muted);
}

.command-workspace {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.command-header {
  position: sticky;
  top: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 18px 24px 14px;
  background: linear-gradient(180deg, rgba(8, 18, 32, 0.96), rgba(8, 18, 32, 0.8));
  border-bottom: 1px solid var(--cc-border);
  backdrop-filter: blur(18px);
  z-index: 30;
}

.command-header__left,
.command-header__right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.command-header__right {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.hamburger-btn {
  font-size: 20px;
}

.page-intro {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.page-intro__title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--cc-text-primary);
}

.page-zone {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(0, 212, 255, 0.16);
  color: var(--cc-text-secondary);
  font-size: 12px;
}

.header-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: var(--cc-text-secondary);
  font-size: 12px;
}

.header-pill--accent {
  border-color: rgba(0, 212, 255, 0.2);
  color: var(--cc-text-primary);
}

.header-clock {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  padding: 6px 12px;
  color: var(--cc-text-secondary);
}

.header-clock strong {
  font-size: 18px;
  color: var(--cc-cyan);
}

.header-clock span {
  font-size: 12px;
}

.user-anchor {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: var(--cc-text-primary);
  cursor: pointer;
}

.user-avatar {
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.9), rgba(17, 224, 183, 0.78));
  color: #04121f;
  font-weight: 700;
}

.user-anchor__meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-anchor__meta small {
  color: var(--cc-text-muted);
}

.command-status-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 24px 0;
  padding: 14px 16px;
}

.status-chip {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.status-chip__label {
  color: var(--cc-text-muted);
  font-size: 12px;
}

.status-chip--success {
  border-color: rgba(30, 230, 143, 0.14);
}

.status-chip--info {
  border-color: rgba(0, 212, 255, 0.16);
}

.status-chip--warning {
  border-color: rgba(255, 191, 71, 0.18);
}

.command-main-stage {
  min-width: 0;
  padding: 20px 24px 28px;
}

.command-main-stage--fullscreen {
  padding-top: 12px;
}

@media (max-width: 1366px) {
  .command-shell {
    grid-template-columns: 272px minmax(0, 1fr);
  }

  .command-status-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1023px) {
  .command-shell {
    grid-template-columns: minmax(0, 1fr);
  }

  .command-header {
    padding: 16px 18px 14px;
  }

  .command-status-strip {
    margin: 14px 18px 0;
  }

  .command-main-stage {
    padding: 16px 18px 22px;
  }
}

@media (max-width: 768px) {
  .command-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .command-header__left,
  .command-header__right {
    width: 100%;
  }

  .command-header__right {
    justify-content: space-between;
  }

  .page-title {
    font-size: 22px;
  }

  .user-anchor__meta,
  .header-clock span {
    display: none;
  }

  .command-status-strip {
    grid-template-columns: 1fr;
  }

  .command-main-stage {
    padding: 14px 14px 20px;
  }
}
</style>
