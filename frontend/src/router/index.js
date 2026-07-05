import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue')
      },
      {
        path: 'map',
        name: 'Map',
        component: () => import('@/views/MapView.vue')
      },
      {
        path: 'nodes',
        name: 'Nodes',
        component: () => import('@/views/Nodes.vue')
      },
      {
        path: 'routes',
        name: 'Routes',
        component: () => import('@/views/Routes.vue')
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/views/Orders.vue')
      },
      {
        path: 'dispatch',
        name: 'Dispatch',
        component: () => import('@/views/DispatchView.vue')
      },
      {
        path: 'tracking',
        name: 'Tracking',
        component: () => import('@/views/Tracking.vue')
      },
      {
        path: 'cost',
        name: 'CostAnalysis',
        component: () => import('@/views/CostAnalysis.vue')
      },
      {
        path: 'vehicles',
        name: 'Vehicles',
        component: () => import('@/views/Vehicles.vue')
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/Users.vue')
      },
      {
        path: 'earth3d',
        name: 'Earth3D',
        component: () => import('@/views/Earth3DPage.vue')
      },
      {
        path: 'multi-objective',
        name: 'MultiObjective',
        component: () => import('@/views/MultiObjectivePage.vue')
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('@/views/AnalyticsView.vue')
      },
      {
        path: 'decision-console',
        name: 'DecisionConsole',
        component: () => import('@/views/DecisionConsoleView.vue')
      },
      {
        path: 'ml-prediction',
        name: 'MLPrediction',
        component: () => import('@/views/MLPredictionView.vue')
      },
      {
        path: 'agile',
        name: 'AgileOptimization',
        component: () => import('@/views/AgileOptimizationView.vue')
      },
      {
        path: 'risk',
        name: 'RiskManagement',
        component: () => import('@/views/RiskManagementView.vue')
      },
      {
        path: 'alert',
        name: 'AlertCenter',
        component: () => import('@/views/AlertCenterView.vue')
      },
      {
        path: 'advanced-route',
        name: 'AdvancedRoute',
        component: () => import('@/views/AdvancedRouteView.vue')
      },
      {
        path: 'advanced-features',
        name: 'AdvancedFeatures',
        component: () => import('@/views/AdvancedFeaturesView.vue')
      },
      {
        path: 'anomaly-detection',
        name: 'AnomalyDetection',
        component: () => import('@/views/AnomalyDetectionView.vue')
      },
      {
        path: 'data-analytics',
        name: 'DataAnalytics',
        component: () => import('@/views/DataAnalyticsView.vue')
      },
      {
        path: 'suppliers',
        name: 'Suppliers',
        component: () => import('@/views/SupplierView.vue')
      },
      {
        path: 'audit-log',
        name: 'AuditLog',
        component: () => import('@/views/AuditLogView.vue')
      },
      {
        path: 'test-data',
        name: 'TestData',
        component: () => import('@/views/TestDataView.vue')
      },
      {
        path: 'data-collection',
        name: 'DataCollection',
        component: () => import('@/views/DataCollectionView.vue')
      },
      {
        path: 'redis-monitor',
        name: 'RedisMonitor',
        component: () => import('@/views/RedisMonitorView.vue')
      },
      {
        path: 'data-screen',
        name: 'DataScreen',
        component: () => import('@/views/DataScreen.vue'),
        meta: { fullscreen: true }
      },
      {
        path: 'big-data',
        name: 'BigData',
        component: () => import('@/views/BigDataScreen.vue'),
        meta: { fullscreen: true }
      },
      {
        path: 'network-design',
        name: 'NetworkDesign',
        component: () => import('@/views/NetworkDesignView.vue')
      },
      {
        path: 'scenario-compare',
        name: 'ScenarioCompare',
        component: () => import('@/views/ScenarioCompareView.vue')
      },
      {
        path: 'optimization-engine',
        name: 'OptimizationEngine',
        component: () => import('@/views/OptimizationEngine.vue')
      },
      {
        path: 'cases/food-supply',
        component: () => import('@/views/case/FoodSupplyCaseLayout.vue'),
        children: [
          { path: '', name: 'CaseOverview', component: () => import('@/views/case/CaseOverview.vue') },
          { path: 'gis', name: 'CaseGis', component: () => import('@/views/case/CaseGis.vue') },
          { path: 'forecast', name: 'CaseForecast', component: () => import('@/views/case/CaseForecast.vue') },
          { path: 'dispatch', name: 'CaseDispatch', component: () => import('@/views/case/CaseDispatch.vue') },
          { path: 'multimodal', name: 'CaseMultimodal', component: () => import('@/views/case/CaseMultimodal.vue') },
          { path: 'c2c', name: 'CaseC2c', component: () => import('@/views/case/CaseC2c.vue') },
          { path: 'clustering', name: 'CaseClustering', component: () => import('@/views/case/CaseClustering.vue') },
          { path: 'trace', name: 'CaseTrace', component: () => import('@/views/case/CaseTrace.vue') },
          { path: 'scenarios', name: 'CaseScenarios', component: () => import('@/views/case/CaseScenarios.vue') },
          { path: 'agent', name: 'CaseAgent', component: () => import('@/views/case/CaseAgent.vue') },
          { path: 'business', name: 'CaseBusiness', component: () => import('@/views/case/CaseBusiness.vue') },
        ]
      },
      {
        path: 'pareto-front',
        name: 'ParetoFront',
        component: () => import('@/views/ParetoFrontPage.vue')
      }
    ]
  }
]

// 大数据分析模块路由
import bigdataRoutes from './bigdata'
routes.push(...bigdataRoutes)

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  
  if (to.meta.requiresAuth !== false && !token) {
    // 需要认证但没有token，跳转登录
    next('/login')
  } else if (to.path === '/login' && token) {
    // 已登录访问登录页，跳转首页
    next('/')
  } else {
    next()
  }
})

const DYNAMIC_IMPORT_RELOAD_KEY = 'logistics_dynamic_import_reload_path'

router.onError((error, to) => {
  if (typeof window === 'undefined') return

  const message = String(error?.message || error || '')
  const isDynamicImportFailure =
    message.includes('Failed to fetch dynamically imported module') ||
    message.includes('Importing a module script failed') ||
    message.includes('NetworkError when attempting to fetch resource') ||
    message.includes('error loading dynamically imported module')

  if (!isDynamicImportFailure) return

  const targetPath = to?.fullPath || window.location.pathname || '/'
  const lastReloadPath = window.sessionStorage.getItem(DYNAMIC_IMPORT_RELOAD_KEY)

  if (lastReloadPath !== targetPath) {
    window.sessionStorage.setItem(DYNAMIC_IMPORT_RELOAD_KEY, targetPath)
    window.location.assign(targetPath)
    return
  }

  console.error('[Router] Dynamic import still failed after one automatic reload.', {
    targetPath,
    message
  })
})

router.afterEach((to) => {
  if (typeof window === 'undefined') return

  const lastReloadPath = window.sessionStorage.getItem(DYNAMIC_IMPORT_RELOAD_KEY)
  if (lastReloadPath && lastReloadPath === to.fullPath) {
    window.sessionStorage.removeItem(DYNAMIC_IMPORT_RELOAD_KEY)
  }
})

export default router
