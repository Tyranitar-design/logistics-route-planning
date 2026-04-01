// pages/index/index.js
const app = getApp()
const { formatMoney, formatDistance, showToast } = require('../../utils/util')
const { driverApi, dispatchApi, taskApi } = require('../../utils/api')

Page({
  data: {
    loading: true,
    
    // 今日统计
    stats: {
      completedOrders: 0,
      totalDistance: 0,
      totalIncome: 0,
      onTimeRate: 98
    },
    
    // 待接单列表
    pendingOrders: [],
    
    // 进行中订单
    currentOrder: null,
    
    // 车辆状态
    vehicleStatus: 'online',
    
    // 司机信息
    driverInfo: null,
    
    // 是否显示语音输入
    showVoiceInput: false
  },

  onLoad() {
    this.loadData()
  },

  onShow() {
    this.loadData()
  },

  onPullDownRefresh() {
    this.loadData().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  // 加载数据
  async loadData() {
    this.setData({ loading: true })
    
    try {
      // 并行加载数据
      const [statsRes, dispatchesRes, driverRes] = await Promise.all([
        this.loadStats(),
        this.loadPendingOrders(),
        this.loadDriverInfo()
      ])
      
      // 检查是否有进行中的订单
      const currentOrderId = wx.getStorageSync('currentOrderId')
      if (currentOrderId) {
        await this.loadCurrentOrder(currentOrderId)
      }
    } catch (err) {
      console.error('加载数据失败:', err)
      // 使用本地模拟数据
      this.loadLocalData()
    } finally {
      this.setData({ loading: false })
    }
  },

  // 加载统计数据
  async loadStats() {
    try {
      const res = await driverApi.getTodayStats()
      if (res.code === 200) {
        this.setData({
          stats: {
            completedOrders: res.data.completed_orders || 0,
            totalDistance: res.data.total_distance || 0,
            totalIncome: res.data.total_income || 0,
            onTimeRate: res.data.on_time_rate || 98
          }
        })
      }
    } catch (err) {
      console.log('加载统计失败，使用模拟数据')
    }
  },

  // 加载待接单
  async loadPendingOrders() {
    try {
      const res = await dispatchApi.getNotifications(1, 10)
      if (res.code === 200) {
        const pendingOrders = (res.data.list || []).map(item => ({
          id: item.id,
          order_number: item.order_number,
          origin_address: item.origin_name || item.origin_address,
          destination_address: item.destination_name || item.destination_address,
          origin_lat: item.origin_lat,
          origin_lng: item.origin_lng,
          destination_lat: item.destination_lat,
          destination_lng: item.destination_lng,
          distance: item.distance || 0,
          freight: item.freight || 0,
          goods_name: item.goods_name || '普通货物',
          weight: item.weight || 0,
          sender_name: item.sender_name || '',
          sender_phone: item.sender_phone || '',
          receiver_name: item.receiver_name || '',
          receiver_phone: item.receiver_phone || '',
          status: 'pending'
        }))
        this.setData({ pendingOrders })
      }
    } catch (err) {
      console.log('加载派单失败，使用模拟数据')
      // 使用本地模拟数据
      this.loadLocalPendingOrders()
    }
  },

  // 加载司机信息
  async loadDriverInfo() {
    try {
      const res = await driverApi.getInfo()
      if (res.code === 200) {
        this.setData({ driverInfo: res.data })
        app.globalData.driverInfo = res.data
      }
    } catch (err) {
      console.log('加载司机信息失败')
    }
  },

  // 加载当前进行中订单
  async loadCurrentOrder(orderId) {
    try {
      const res = await taskApi.getDetail(orderId)
      if (res.code === 200 && res.data) {
        this.setData({ currentOrder: res.data })
      }
    } catch (err) {
      console.log('加载当前订单失败')
    }
  },

  // 使用本地模拟数据
  loadLocalData() {
    this.setData({
      stats: {
        completedOrders: 5,
        totalDistance: 156.8,
        totalIncome: 680.00,
        onTimeRate: 98
      }
    })
    this.loadLocalPendingOrders()
  },

  // 本地模拟待接单数据
  loadLocalPendingOrders() {
    const localOrders = [
      {
        id: 1,
        order_number: 'WL202603270001',
        origin_address: '北京市朝阳区建国路88号SOHO现代城',
        destination_address: '北京市海淀区中关村大街1号海龙大厦',
        origin_lat: 39.908823,
        origin_lng: 116.457470,
        destination_lat: 39.984120,
        destination_lng: 116.307463,
        distance: 15000,
        freight: 120,
        goods_name: '电子产品',
        weight: 50,
        sender_name: '张先生',
        sender_phone: '13800138001',
        receiver_name: '李女士',
        receiver_phone: '13800138002',
        status: 'pending'
      },
      {
        id: 2,
        order_number: 'WL202603270002',
        origin_address: '北京市东城区王府井大街255号',
        destination_address: '北京市西城区金融街19号',
        origin_lat: 39.9139,
        origin_lng: 116.4103,
        destination_lat: 39.9147,
        destination_lng: 116.3667,
        distance: 5200,
        freight: 68,
        goods_name: '服装',
        weight: 20,
        sender_name: '王先生',
        sender_phone: '13800138003',
        receiver_name: '赵女士',
        receiver_phone: '13800138004',
        status: 'pending'
      }
    ]
    this.setData({ pendingOrders: localOrders })
  },

  // 查看订单详情
  goToOrderDetail(e) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/order-detail/order-detail?id=${id}`
    })
  },

  // 接单
  async acceptOrder(e) {
    const { id } = e.currentTarget.dataset
    const order = this.data.pendingOrders.find(o => o.id === id)
    
    if (!order) {
      showToast('订单不存在')
      return
    }
    
    wx.showModal({
      title: '确认接单',
      content: `订单：${order.order_number}\n从：${order.origin_address}\n到：${order.destination_address}`,
      success: async (res) => {
        if (res.confirm) {
          try {
            // 尝试调用后端 API
            await dispatchApi.accept(id)
          } catch (err) {
            console.log('后端接单失败，使用本地模式')
          }
          
          // 保存到本地
          let myOrders = wx.getStorageSync('myOrders') || []
          const acceptedOrder = {
            ...order,
            status: 'accepted',
            acceptedAt: new Date().toISOString()
          }
          myOrders.unshift(acceptedOrder)
          wx.setStorageSync('myOrders', myOrders)
          
          // 从待接单列表移除
          const pendingOrders = this.data.pendingOrders.filter(o => o.id !== id)
          this.setData({ pendingOrders })
          
          showToast('接单成功！', 'success')
          
          // 跳转到订单详情
          setTimeout(() => {
            wx.navigateTo({
              url: `/pages/order-detail/order-detail?id=${id}`
            })
          }, 500)
        }
      }
    })
  },

  // 开始配送
  startDelivery(e) {
    const { id } = e.currentTarget.dataset
    
    let myOrders = wx.getStorageSync('myOrders') || []
    const orderIndex = myOrders.findIndex(o => o.id === id)
    
    if (orderIndex === -1) {
      showToast('订单不存在')
      return
    }
    
    myOrders[orderIndex].status = 'in_progress'
    myOrders[orderIndex].startedAt = new Date().toISOString()
    wx.setStorageSync('myOrders', myOrders)
    wx.setStorageSync('currentOrderId', id)
    
    showToast('开始配送！', 'success')
    
    // 刷新页面
    this.loadData()
    
    // 跳转到地图页
    setTimeout(() => {
      wx.switchTab({
        url: '/pages/map/map'
      })
    }, 500)
  },

  // 查看更多
  goToMoreOrders() {
    wx.switchTab({
      url: '/pages/orders/orders'
    })
  },

  // 切换状态
  async toggleVehicleStatus() {
    const newStatus = this.data.vehicleStatus === 'online' ? 'offline' : 'online'
    
    try {
      await driverApi.updateVehicleStatus(newStatus)
    } catch (err) {
      console.log('更新状态失败')
    }
    
    this.setData({ vehicleStatus: newStatus })
    showToast(newStatus === 'online' ? '已上线接单' : '已下线休息')
  },

  // 显示语音输入
  showVoiceInput() {
    this.setData({ showVoiceInput: true })
  },

  // 隐藏语音输入
  hideVoiceInput() {
    this.setData({ showVoiceInput: false })
  },

  // 处理语音命令
  onVoiceCommand(e) {
    const { action, message, navigateTo } = e.detail
    console.log('收到语音命令:', action, message)
    
    // 关闭语音输入面板
    this.setData({ showVoiceInput: false })
    
    // 根据命令执行操作
    switch (action) {
      case 'start_delivery':
        // 开始配送
        if (this.data.currentOrder) {
          this.startDelivery({ currentTarget: { dataset: { id: this.data.currentOrder.id } } })
        }
        break
        
      case 'navigate':
        // 导航
        if (navigateTo) {
          wx.navigateTo({ url: navigateTo })
        }
        break
        
      default:
        console.log('未知命令:', action)
    }
  },

  // 工具函数
  formatMoney,
  formatDistance
})