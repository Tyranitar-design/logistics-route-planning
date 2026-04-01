// pages/orders/orders.js
const { formatMoney, formatDistance, showToast } = require('../../utils/util')

Page({
  data: {
    loading: true,
    
    // 当前标签
    activeTab: 'pending',
    tabs: [
      { key: 'pending', name: '待接单' },
      { key: 'accepted', name: '已接单' },
      { key: 'in_progress', name: '配送中' },
      { key: 'completed', name: '已完成' }
    ],
    
    // 订单列表
    orders: []
  },

  onLoad(options) {
    if (options.status) {
      this.setData({ activeTab: options.status })
    }
  },

  onShow() {
    this.loadOrders()
  },

  onPullDownRefresh() {
    this.loadOrders()
    wx.stopPullDownRefresh()
  },

  // 切换标签
  switchTab(e) {
    const { key } = e.currentTarget.dataset
    this.setData({ activeTab: key })
    this.loadOrders()
  },

  // 加载订单
  loadOrders() {
    const { activeTab } = this.data
    
    // 从本地存储读取
    const myOrders = wx.getStorageSync('myOrders') || []
    const pendingOrders = wx.getStorageSync('pendingOrders') || this.getDefaultPendingOrders()
    
    let orders = []
    
    if (activeTab === 'pending') {
      orders = pendingOrders.filter(o => o.status === 'pending')
    } else {
      orders = myOrders.filter(o => o.status === activeTab)
    }
    
    this.setData({ orders, loading: false })
  },

  // 默认待接单（带完整坐标）
  getDefaultPendingOrders() {
    const defaults = [
      {
        id: 101,
        order_number: 'WL202603271001',
        origin_address: '北京市朝阳区国贸大厦',
        destination_address: '北京市海淀区五道口',
        origin_lat: 39.908823,
        origin_lng: 116.457470,
        destination_lat: 39.984120,
        destination_lng: 116.307463,
        distance: 12000,
        freight: 98,
        goods_name: '办公用品',
        sender_name: '刘总',
        sender_phone: '13900139001',
        receiver_name: '王经理',
        receiver_phone: '13900139002',
        status: 'pending'
      },
      {
        id: 102,
        order_number: 'WL202603271002',
        origin_address: '北京市西城区西单商场',
        destination_address: '北京市朝阳区望京SOHO',
        origin_lat: 39.9139,
        origin_lng: 116.3744,
        destination_lat: 39.9963,
        destination_lng: 116.4817,
        distance: 8500,
        freight: 75,
        goods_name: '服装',
        sender_name: '陈女士',
        sender_phone: '13900139003',
        receiver_name: '张先生',
        receiver_phone: '13900139004',
        status: 'pending'
      }
    ]
    wx.setStorageSync('pendingOrders', defaults)
    return defaults
  },

  // 接单
  acceptOrder(e) {
    const { id } = e.currentTarget.dataset
    
    const pendingOrders = wx.getStorageSync('pendingOrders') || []
    const order = pendingOrders.find(o => o.id === id)
    
    if (!order) {
      showToast('订单不存在')
      return
    }
    
    wx.showModal({
      title: '确认接单',
      content: `确认接单 ${order.order_number}？`,
      success: (res) => {
        if (res.confirm) {
          // 添加到我的订单
          const myOrders = wx.getStorageSync('myOrders') || []
          const acceptedOrder = {
            ...order,
            status: 'accepted',
            acceptedAt: new Date().toISOString()
          }
          myOrders.unshift(acceptedOrder)
          wx.setStorageSync('myOrders', myOrders)
          
          // 从待接单移除
          const newPending = pendingOrders.filter(o => o.id !== id)
          wx.setStorageSync('pendingOrders', newPending)
          
          showToast('接单成功！', 'success')
          this.loadOrders()
        }
      }
    })
  },

  // 开始配送
  startDelivery(e) {
    const { id } = e.currentTarget.dataset
    
    const myOrders = wx.getStorageSync('myOrders') || []
    const index = myOrders.findIndex(o => o.id === id)
    
    if (index === -1) return
    
    myOrders[index].status = 'in_progress'
    myOrders[index].startedAt = new Date().toISOString()
    wx.setStorageSync('myOrders', myOrders)
    wx.setStorageSync('currentOrderId', id)
    
    showToast('开始配送！', 'success')
    this.loadOrders()
    
    // 跳转到详情
    setTimeout(() => {
      wx.navigateTo({
        url: `/pages/order-detail/order-detail?id=${id}`
      })
    }, 500)
  },

  // 查看详情
  goToDetail(e) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/order-detail/order-detail?id=${id}`
    })
  },

  // 签收
  goToSign(e) {
    const { id } = e.currentTarget.dataset
    wx.navigateTo({
      url: `/pages/sign/sign?taskId=${id}`
    })
  },

  formatMoney,
  formatDistance
})