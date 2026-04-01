// pages/map/map.js
const { formatDistance, showToast } = require('../../utils/util')

Page({
  data: {
    latitude: 39.908823,
    longitude: 116.39747,
    scale: 12,
    
    // 当前订单
    currentOrder: null,
    
    // 地图元素
    markers: []
  },

  onLoad() {
    this.initMap()
  },

  onShow() {
    this.loadCurrentOrder()
  },

  // 初始化地图
  initMap() {
    // 默认定位到北京
    this.setData({
      latitude: 39.908823,
      longitude: 116.39747
    })
  },

  // 加载当前配送订单
  loadCurrentOrder() {
    const currentOrderId = wx.getStorageSync('currentOrderId')
    
    if (!currentOrderId) {
      this.setData({ currentOrder: null })
      return
    }
    
    const myOrders = wx.getStorageSync('myOrders') || []
    const order = myOrders.find(o => o.id === currentOrderId && o.status === 'in_progress')
    
    if (order) {
      this.setData({ currentOrder: order })
      this.setRouteOnMap(order)
    } else {
      this.setData({ currentOrder: null })
    }
  },

  // 在地图上显示路线
  setRouteOnMap(order) {
    const markers = []
    
    // 检查是否有位置数据
    if (!order.origin_lat || !order.destination_lat) {
      console.warn('订单缺少位置数据')
      return
    }
    
    // 发货地标记
    markers.push({
      id: 1,
      latitude: order.origin_lat,
      longitude: order.origin_lng,
      title: '发货地',
      width: 25,
      height: 35
    })
    
    // 收货地标记
    markers.push({
      id: 2,
      latitude: order.destination_lat,
      longitude: order.destination_lng,
      title: '收货地',
      width: 25,
      height: 35
    })
    
    // 设置视野范围（居中到收货地）
    this.setData({
      markers,
      latitude: order.destination_lat,
      longitude: order.destination_lng,
      scale: 13
    })
  },

  // 导航到发货地
  navigateToOrigin() {
    const { currentOrder } = this.data
    
    if (!currentOrder) {
      showToast('暂无订单信息')
      return
    }
    
    if (!currentOrder.origin_lat || !currentOrder.origin_lng) {
      showToast('订单缺少发货地位置信息')
      return
    }
    
    wx.openLocation({
      latitude: currentOrder.origin_lat,
      longitude: currentOrder.origin_lng,
      name: '发货地',
      address: currentOrder.origin_address || '',
      scale: 18
    })
  },

  // 导航到收货地
  navigateToDestination() {
    const { currentOrder } = this.data
    
    if (!currentOrder) {
      showToast('暂无订单信息')
      return
    }
    
    if (!currentOrder.destination_lat || !currentOrder.destination_lng) {
      showToast('订单缺少收货地位置信息')
      return
    }
    
    wx.openLocation({
      latitude: currentOrder.destination_lat,
      longitude: currentOrder.destination_lng,
      name: '收货地',
      address: currentOrder.destination_address || '',
      scale: 18
    })
  },

  // 重新定位
  reLocate() {
    wx.getLocation({
      type: 'gcj02',
      success: (res) => {
        this.setData({
          latitude: res.latitude,
          longitude: res.longitude
        })
      },
      fail: () => {
        showToast('获取位置失败')
      }
    })
  },

  // 去签收
  goToSign() {
    const { currentOrder } = this.data
    if (!currentOrder) return
    
    wx.navigateTo({
      url: `/pages/sign/sign?taskId=${currentOrder.id}`
    })
  },

  formatDistance
})