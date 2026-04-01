// pages/order-detail/order-detail.js
const { formatTime, formatMoney, formatDistance, formatDuration, showToast, showLoading, hideLoading, getLocation } = require('../../utils/util')

Page({
  data: {
    loading: true,
    orderId: null,
    order: null,
    
    // 地图
    latitude: 39.908823,
    longitude: 116.39747,
    markers: [],
    
    // 当前步骤
    currentStep: 0,
    steps: [
      { text: '已接单', status: 'process' },
      { text: '已取货', status: 'wait' },
      { text: '配送中', status: 'wait' },
      { text: '已送达', status: 'wait' }
    ]
  },

  onLoad(options) {
    if (options.id) {
      this.setData({ orderId: options.id })
      this.loadOrderDetail()
    }
  },

  // 加载订单详情
  loadOrderDetail() {
    const myOrders = wx.getStorageSync('myOrders') || []
    let order = myOrders.find(o => o.id === parseInt(this.data.orderId))
    
    if (!order) {
      // 模拟数据
      order = {
        id: this.data.orderId,
        order_number: 'WL202603270001',
        status: 'accepted',
        origin_address: '北京市朝阳区建国路88号SOHO现代城',
        destination_address: '北京市海淀区中关村大街1号海龙大厦',
        origin_lat: 39.908823,
        origin_lng: 116.457470,
        destination_lat: 39.984120,
        destination_lng: 116.307463,
        distance: 15000,
        freight: 120,
        estimated_duration: 45,
        goods_name: '电子产品',
        weight: 50,
        sender_name: '张先生',
        sender_phone: '13800138001',
        receiver_name: '李女士',
        receiver_phone: '13800138002',
        created_at: new Date().toISOString(),
        accepted_at: new Date().toISOString()
      }
    }
    
    // 更新步骤
    const steps = this.updateSteps(order.status)
    
    this.setData({ 
      order, 
      steps,
      loading: false,
      latitude: order.origin_lat || 39.908823,
      longitude: order.origin_lng || 116.39747
    })
    
    // 设置地图标记
    if (order.origin_lat && order.destination_lat) {
      this.setData({
        markers: [
          {
            id: 1,
            latitude: order.origin_lat,
            longitude: order.origin_lng,
            title: '发货地',
            width: 25,
            height: 35
          },
          {
            id: 2,
            latitude: order.destination_lat,
            longitude: order.destination_lng,
            title: '收货地',
            width: 25,
            height: 35
          }
        ]
      })
    }
  },

  // 更新步骤状态
  updateSteps(status) {
    const steps = [
      { text: '已接单', status: 'wait' },
      { text: '已取货', status: 'wait' },
      { text: '配送中', status: 'wait' },
      { text: '已送达', status: 'wait' }
    ]
    
    const statusMap = {
      'accepted': 0,
      'picked_up': 1,
      'in_progress': 2,
      'completed': 3
    }
    
    const currentStep = statusMap[status] || 0
    
    for (let i = 0; i <= currentStep; i++) {
      steps[i].status = 'finish'
    }
    if (currentStep < 3) {
      steps[currentStep + 1] && (steps[currentStep + 1].status = 'process')
    }
    
    return steps
  },

  // 导航到发货地
  navigateToOrigin() {
    const { order } = this.data
    if (order && order.origin_lat) {
      wx.openLocation({
        latitude: order.origin_lat,
        longitude: order.origin_lng,
        name: order.origin_address,
        address: order.sender_name ? `联系人: ${order.sender_name}` : ''
      })
    } else {
      showToast('暂无位置信息')
    }
  },

  // 导航到收货地
  navigateToDestination() {
    const { order } = this.data
    if (order && order.destination_lat) {
      wx.openLocation({
        latitude: order.destination_lat,
        longitude: order.destination_lng,
        name: order.destination_address,
        address: order.receiver_name ? `联系人: ${order.receiver_name}` : ''
      })
    } else {
      showToast('暂无位置信息')
    }
  },

  // 拨打电话
  callPhone(e) {
    const { phone } = e.currentTarget.dataset
    if (phone) {
      wx.makePhoneCall({ phoneNumber: phone })
    }
  },

  // 开始配送
  startDelivery() {
    const { orderId, order } = this.data
    
    wx.showModal({
      title: '开始配送',
      content: '确认开始配送？请确保已取到货物。',
      success: (res) => {
        if (res.confirm) {
          // 更新状态
          const myOrders = wx.getStorageSync('myOrders') || []
          const index = myOrders.findIndex(o => o.id === parseInt(orderId))
          
          if (index !== -1) {
            myOrders[index].status = 'in_progress'
            myOrders[index].startedAt = new Date().toISOString()
            wx.setStorageSync('myOrders', myOrders)
            wx.setStorageSync('currentOrderId', orderId)
          }
          
          showToast('已开始配送！', 'success')
          
          // 刷新页面
          this.loadOrderDetail()
        }
      }
    })
  },

  // 确认取货
  confirmPickup() {
    const { orderId } = this.data
    
    const myOrders = wx.getStorageSync('myOrders') || []
    const index = myOrders.findIndex(o => o.id === parseInt(orderId))
    
    if (index !== -1) {
      myOrders[index].status = 'picked_up'
      myOrders[index].pickupAt = new Date().toISOString()
      wx.setStorageSync('myOrders', myOrders)
    }
    
    showToast('取货确认成功', 'success')
    this.loadOrderDetail()
  },

  // 去签收
  goToSign() {
    wx.navigateTo({
      url: `/pages/sign/sign?taskId=${this.data.orderId}`
    })
  },

  formatTime,
  formatMoney,
  formatDistance,
  formatDuration
})