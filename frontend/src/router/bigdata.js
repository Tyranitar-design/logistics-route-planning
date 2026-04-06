// 大数据分析模块路由
export default [
  {
    path: '/bigdata',
    component: () => import('@/views/bigdata/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/bigdata/monitor'
      },
      {
        path: 'monitor',
        name: 'BigDataMonitor',
        component: () => import('@/views/bigdata/Monitor.vue'),
        meta: { title: '实时监控大屏' }
      },
      {
        path: 'search',
        name: 'BigDataSearch',
        component: () => import('@/views/bigdata/Search.vue'),
        meta: { title: '全文搜索' }
      },
      {
        path: 'analytics',
        name: 'BigDataAnalytics',
        component: () => import('@/views/bigdata/Analytics.vue'),
        meta: { title: '大数据分析' }
      },
      {
        path: 'scheduler',
        name: 'BigDataScheduler',
        component: () => import('@/views/bigdata/Scheduler.vue'),
        meta: { title: '任务调度' }
      },
      {
        path: 'spark',
        name: 'BigDataSpark',
        component: () => import('@/views/bigdata/Spark.vue'),
        meta: { title: 'Spark实时处理' }
      },
      {
        path: 'dl-studio',
        name: 'BigDataDLStudio',
        component: () => import('@/views/bigdata/DeepLearning.vue'),
        meta: { title: '深度学习' }
      },
      {
        path: 'visual',
        name: 'BigDataVisual',
        component: () => import('@/views/bigdata/Visualization.vue'),
        meta: { title: '数据可视化' }
      }
    ]
  }
]
