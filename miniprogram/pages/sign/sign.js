// pages/sign/sign.js
const { showToast, showLoading, hideLoading, formatTime } = require('../../utils/util')

Page({
  data: {
    taskId: null,
    order: null,
    
    // 签收信息
    receiverName: '',
    receiverPhone: '',
    remark: '',
    
    // 签名
    signatureImage: '',
    
    // 照片
    photos: [],
    
    // 画布
    canvasWidth: 300,
    canvasHeight: 200,
    isDrawing: false,
    lastX: 0,
    lastY: 0,
    paths: []
  },

  onLoad(options) {
    if (options.taskId) {
      this.setData({ taskId: options.taskId })
      this.loadTaskDetail()
    }
    
    // 获取屏幕宽度设置画布
    try {
      const windowInfo = wx.getWindowInfo()
      this.setData({
        canvasWidth: windowInfo.windowWidth - 60
      })
    } catch (e) {}
  },

  // 加载任务详情
  loadTaskDetail() {
    const myOrders = wx.getStorageSync('myOrders') || []
    const order = myOrders.find(o => o.id === parseInt(this.data.taskId))
    
    if (order) {
      this.setData({ order })
    } else {
      // 模拟数据
      this.setData({
        order: {
          order_number: 'WL202603270001',
          destination: {
            contact: '李女士',
            phone: '13800138002',
            address: '北京市海淀区中关村大街1号'
          }
        }
      })
    }
  },

  // 输入
  onInputChange(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [field]: e.detail.value })
  },

  // 签名相关
  onCanvasStart(e) {
    const touch = e.touches[0]
    this.setData({
      isDrawing: true,
      lastX: touch.x,
      lastY: touch.y
    })
  },

  onCanvasMove(e) {
    if (!this.data.isDrawing) return
    
    const touch = e.touches[0]
    const { lastX, lastY, paths } = this.data
    
    paths.push({
      x1: lastX,
      y1: lastY,
      x2: touch.x,
      y2: touch.y
    })
    
    const ctx = wx.createCanvasContext('signatureCanvas', this)
    ctx.setStrokeStyle('#333333')
    ctx.setLineWidth(3)
    ctx.setLineCap('round')
    ctx.setLineJoin('round')
    ctx.moveTo(lastX, lastY)
    ctx.lineTo(touch.x, touch.y)
    ctx.stroke()
    ctx.draw(true)
    
    this.setData({
      lastX: touch.x,
      lastY: touch.y,
      paths
    })
  },

  onCanvasEnd() {
    this.setData({ isDrawing: false })
  },

  clearSignature() {
    const ctx = wx.createCanvasContext('signatureCanvas', this)
    ctx.clearRect(0, 0, this.data.canvasWidth, this.data.canvasHeight)
    ctx.draw()
    this.setData({ paths: [], signatureImage: '' })
  },

  // 照片相关
  takePhoto() {
    const { photos } = this.data
    if (photos.length >= 3) {
      showToast('最多上传3张照片')
      return
    }
    
    wx.chooseImage({
      count: 3 - photos.length,
      sizeType: ['compressed'],
      sourceType: ['camera', 'album'],
      success: (res) => {
        this.setData({
          photos: [...photos, ...res.tempFilePaths]
        })
      }
    })
  },

  deletePhoto(e) {
    const { index } = e.currentTarget.dataset
    const photos = this.data.photos.filter((_, i) => i !== index)
    this.setData({ photos })
  },

  previewPhoto(e) {
    const { src } = e.currentTarget.dataset
    wx.previewImage({
      current: src,
      urls: this.data.photos
    })
  },

  // 提交签收
  submitSign() {
    const { receiverName, taskId, paths, photos } = this.data
    
    if (!receiverName.trim()) {
      showToast('请填写收货人姓名')
      return
    }
    
    if (paths.length === 0) {
      showToast('请签名确认')
      return
    }
    
    wx.showModal({
      title: '确认签收',
      content: '请确认货物已送达收货人',
      success: (res) => {
        if (res.confirm) {
          showLoading('提交中...')
          
          // 更新订单状态
          const myOrders = wx.getStorageSync('myOrders') || []
          const index = myOrders.findIndex(o => o.id === parseInt(taskId))
          
          if (index !== -1) {
            myOrders[index].status = 'completed'
            myOrders[index].completedAt = new Date().toISOString()
            myOrders[index].receiverName = receiverName
            myOrders[index].receiverPhone = this.data.receiverPhone
            myOrders[index].remark = this.data.remark
            myOrders[index].hasPhoto = photos.length > 0
            wx.setStorageSync('myOrders', myOrders)
          }
          
          // 清除当前订单
          wx.removeStorageSync('currentOrderId')
          
          setTimeout(() => {
            hideLoading()
            showToast('签收成功！', 'success')
            
            // 返回首页
            setTimeout(() => {
              wx.switchTab({
                url: '/pages/index/index'
              })
            }, 1500)
          }, 1000)
        }
      }
    })
  },

  formatTime
})