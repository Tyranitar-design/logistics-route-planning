// pages/dispatch/dispatch.js
const { dispatchApi, taskApi } = require('../../utils/api')
const { formatDistance, formatMoney, showToast, showLoading, hideLoading, showConfirm } = require('../../utils/util')

Page({
  data: {
    loading: true,
    notifications: [],
    
    // 当前查看的派单详情
    currentDispatch: null,
    showDetail: false
  },

  onLoad() {
    this.loadNotifications()
  },

  onShow() {
    this.loadNotifications()
  },

  onPullDownRefresh() {
    this.loadNotifications().then(() => {
      wx.stopPullDownRefresh()
    })
  },

  // 加载派单通知
  async loadNotifications() {
    this.setData({ loading: true })
    
    try {
      const res = await dispatchApi.getNotifications()
      this.setData({
        notifications: res.data.list || [],
        loading: false
      })
    } catch (err) {
      console.error('加载派单失败:', err)
      showToast('加载失败')
      this.setData({ loading: false })
    }
  },

  // 查看详情
  showDispatchDetail(e) {
    const { notification } = e.currentTarget.dataset
    this.setData({
      currentDispatch: notification,
      showDetail: true
    })
  },

  // 关闭详情
  closeDetail() {
    this.setData({ showDetail: false })
  },

  // 接受派单
  async acceptDispatch(e) {
    const { id } = e.currentTarget.dataset
    
    const dispatch = this.data.notifications.find(n => n.id === id)
    if (!dispatch) return
    
    const confirm = await showConfirm('确认接单？', `订单：${dispatch.order_number || '新订单'}`)
    if (!confirm) return
    
    showLoading('接单中...')
    
    try {
      await dispatchApi.accept(id)
      hideLoading()
      showToast('接单成功', 'success')
      
      // 刷新列表
      this.loadNotifications()
    } catch (err) {
      hideLoading()
      showToast(err.message || '接单失败')
    }
  },

  // 拒绝派单
  async rejectDispatch(e) {
    const { id } = e.currentTarget.dataset
    
    const confirm = await showConfirm('确定拒绝？', '拒绝后将无法再次接此订单')
    if (!confirm) return
    
    showLoading('处理中...')
    
    try {
      await dispatchApi.reject(id, '司机主动拒绝')
      hideLoading()
      showToast('已拒绝')
      
      // 刷新列表
      this.loadNotifications()
    } catch (err) {
      hideLoading()
      showToast(err.message || '操作失败')
    }
  },

  // 快速接单（从详情弹窗）
  async quickAccept() {
    const { currentDispatch } = this.data
    if (!currentDispatch) return
    
    this.closeDetail()
    
    showLoading('接单中...')
    
    try {
      await dispatchApi.accept(currentDispatch.id)
      hideLoading()
      showToast('接单成功', 'success')
      
      // 刷新列表
      this.loadNotifications()
    } catch (err) {
      hideLoading()
      showToast(err.message || '接单失败')
    }
  },

  formatDistance,
  formatMoney
})