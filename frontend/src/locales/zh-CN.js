export default {
  // 通用
  common: {
    confirm: '确认',
    cancel: '取消',
    save: '保存',
    delete: '删除',
    edit: '编辑',
    add: '添加',
    search: '搜索',
    reset: '重置',
    export: '导出',
    import: '导入',
    refresh: '刷新',
    loading: '加载中...',
    success: '操作成功',
    error: '操作失败',
    warning: '警告',
    tip: '提示',
    all: '全部',
    status: '状态',
    action: '操作',
    createTime: '创建时间',
    updateTime: '更新时间',
    description: '描述',
    remark: '备注',
    detail: '详情'
  },
  
  // 导航菜单
  menu: {
    dashboard: '控制台',
    map: '地图视图',
    earth3d: '3D地球',
    dataScreen: '数据大屏',
    nodes: '节点管理',
    routes: '路线管理',
    orders: '订单管理',
    dispatch: '智能调度',
    advanced: '高级优化',
    tracking: '轨迹模拟',
    multiObjective: '多目标优化',
    agile: '敏捷优化',
    risk: '风险管理',
    alert: '预警中心',
    analytics: '数据分析',
    cost: '成本分析',
    mlPrediction: 'AI预测',
    anomaly: '异常检测',
    dataAnalytics: '数据分析中心',
    auditLog: '审计日志',
    supplier: '供应商管理',
    vehicles: '车辆管理',
    users: '用户管理',
    testData: '测试数据',
    settings: '系统设置'
  },
  
  // 订单
  order: {
    title: '订单管理',
    orderNumber: '订单编号',
    origin: '起点',
    destination: '终点',
    cargo: '货物',
    weight: '重量(kg)',
    volume: '体积(m³)',
    sender: '发货人',
    receiver: '收货人',
    priority: '优先级',
    status: {
      pending: '待处理',
      assigned: '已派单',
      in_transit: '运输中',
      delivered: '已送达',
      cancelled: '已取消'
    }
  },
  
  // 车辆
  vehicle: {
    title: '车辆管理',
    plateNumber: '车牌号',
    vehicleType: '车辆类型',
    brand: '品牌',
    model: '型号',
    loadCapacity: '载重(吨)',
    driver: '司机',
    status: {
      available: '空闲',
      in_use: '使用中',
      maintenance: '维修中',
      offline: '离线'
    }
  },
  
  // 路线
  route: {
    title: '路线管理',
    routeName: '路线名称',
    startNode: '起点',
    endNode: '终点',
    distance: '距离(km)',
    duration: '时长(h)',
    tollCost: '过路费(元)',
    fuelCost: '油费(元)',
    totalCost: '总成本(元)',
    recommend: '路线推荐',
    optimize: '路线优化'
  },
  
  // 数据分析
  analytics: {
    title: '数据分析',
    overview: '概览',
    trend: '趋势',
    distribution: '分布',
    comparison: '对比',
    export: '导出报表',
    totalOrders: '总订单数',
    totalVehicles: '总车辆数',
    totalRoutes: '总路线数',
    totalCost: '总成本',
    avgCost: '平均成本',
    savingRate: '节省率'
  },
  
  // 预警
  alert: {
    title: '预警中心',
    orderAlert: '订单预警',
    vehicleAlert: '车辆预警',
    routeAlert: '路线预警',
    supplyChainAlert: '供应链预警',
    healthScore: '健康度评分',
    viewAll: '查看全部'
  },
  
  // 登录
  login: {
    title: '物流路径规划系统',
    username: '用户名',
    password: '密码',
    rememberMe: '记住我',
    submit: '登录',
    forgotPassword: '忘记密码？',
    register: '注册账号'
  },
  
  // 用户信息
  user: {
    profile: '个人中心',
    logout: '退出登录',
    changePassword: '修改密码',
    role: {
      admin: '管理员',
      user: '普通用户',
      driver: '司机'
    }
  }
}
