// pages/profile/profile.js
const app = getApp()

Page({
  data: {
    userInfo: {
      real_name: '测试司机',
      phone: '138****8000',
      avatar: ''
    },
    
    // 统计数据
    stats: {
      totalOrders: 0,
      totalIncome: 0,
      totalDistance: 0,
      onTimeRate: 98,
      rating: 4.9,
      todayOrders: 0,
      todayIncome: 0
    },
    
    // 菜单项
    menuItems: [
      { icon: '💰', title: '收入明细', desc: '查看收入记录', page: 'income' },
      { icon: '📊', title: '配送统计', desc: '查看配送数据', page: 'stats' },
      { icon: '🚗', title: '车辆信息', desc: '管理车辆资料', page: 'vehicle' },
      { icon: '🎖️', title: '荣誉中心', desc: '成就与徽章', page: 'honor' },
      { icon: '⭐', title: '评价管理', desc: '查看客户评价', page: 'reviews' },
      { icon: '⚙️', title: '设置', desc: '应用设置', page: 'settings' },
      { icon: '❓', title: '帮助与反馈', desc: '常见问题', page: 'help' }
    ],
    
    // 语音输入
    showVoiceInput: false
  },

  onLoad() {
    this.loadUserInfo()
  },

  onShow() {
    this.loadStats()
  },

  // 加载用户信息
  loadUserInfo() {
    const userInfo = app.globalData.userInfo
    if (userInfo) {
      this.setData({ userInfo })
    }
  },

  // 加载统计数据
  loadStats() {
    const myOrders = wx.getStorageSync('myOrders') || []
    
    const completed = myOrders.filter(o => o.status === 'completed')
    const inProgress = myOrders.filter(o => o.status === 'in_progress')
    
    const totalIncome = completed.reduce((sum, o) => sum + (o.freight || 0), 0)
    const todayOrders = completed.filter(o => {
      const orderDate = new Date(o.completedAt).toDateString()
      return orderDate === new Date().toDateString()
    })
    const todayIncome = todayOrders.reduce((sum, o) => sum + (o.freight || 0), 0)
    
    this.setData({
      stats: {
        totalOrders: completed.length,
        totalIncome: totalIncome,
        totalDistance: completed.reduce((sum, o) => sum + (o.distance || 0), 0) / 1000,
        onTimeRate: 98,
        rating: 4.9,
        todayOrders: todayOrders.length,
        todayIncome: todayIncome
      }
    })
  },

  // 跳转菜单
  goToPage(e) {
    const { page } = e.currentTarget.dataset
    
    switch(page) {
      case 'income':
        this.showIncomeDetail()
        break
      case 'stats':
        this.showDeliveryStats()
        break
      case 'vehicle':
        this.showVehicleInfo()
        break
      case 'honor':
        this.showHonor()
        break
      case 'reviews':
        this.showReviews()
        break
      case 'settings':
        this.showSettings()
        break
      case 'help':
        this.showHelp()
        break
      default:
        wx.showToast({ title: '功能开发中', icon: 'none' })
    }
  },

  // 收入明细
  showIncomeDetail() {
    const myOrders = wx.getStorageSync('myOrders') || []
    const completed = myOrders.filter(o => o.status === 'completed')
    
    const incomeList = completed.map(o => ({
      order_number: o.order_number,
      amount: o.freight || 0,
      time: o.completedAt || o.acceptedAt
    }))
    
    const total = incomeList.reduce((sum, i) => sum + i.amount, 0)
    
    wx.showModal({
      title: '💰 收入明细',
      content: `总收入：¥${total.toFixed(2)}\n完成订单：${completed.length}单\n平均单价：¥${completed.length > 0 ? (total / completed.length).toFixed(2) : 0}`,
      showCancel: false
    })
  },

  // 配送统计
  showDeliveryStats() {
    const myOrders = wx.getStorageSync('myOrders') || []
    const completed = myOrders.filter(o => o.status === 'completed')
    
    wx.showModal({
      title: '📊 配送统计',
      content: `总订单数：${myOrders.length}单\n已完成：${completed.length}单\n总里程：${this.data.stats.totalDistance.toFixed(1)}km\n准时率：${this.data.stats.onTimeRate}%\n评分：${this.data.stats.rating}分`,
      showCancel: false
    })
  },

  // 车辆信息
  showVehicleInfo() {
    wx.showModal({
      title: '🚗 车辆信息',
      content: '车牌号：京A12345\n车型：东风天龙重卡\n载重：10吨\n状态：正常运营\n\n驾驶员：张师傅\n联系电话：138****8000',
      confirmText: '修改信息',
      success: (res) => {
        if (res.confirm) {
          wx.showToast({ title: '修改功能开发中', icon: 'none' })
        }
      }
    })
  },

  // 荣誉中心
  showHonor() {
    wx.showModal({
      title: '🎖️ 荣誉中心',
      content: '🏆 配送之星\n完成100单配送任务\n\n⭐ 五星好评\n获得50次五星好评\n\n🚀 速度达人\n单日完成10单配送\n\n💪 更多荣誉，等你解锁！',
      showCancel: false
    })
  },

  // 评价管理
  showReviews() {
    wx.showModal({
      title: '⭐ 客户评价',
      content: '平均评分：4.9分\n\n📝 最近评价：\n"送货很快，服务态度好！" - 李女士\n"准时送达，非常满意！" - 王先生\n"包装完好，感谢师傅！" - 张总',
      showCancel: false
    })
  },

  // 设置
  showSettings() {
    wx.showActionSheet({
      itemList: ['消息通知设置', '语音播报设置', '清除缓存数据', '关于我们'],
      success: (res) => {
        switch(res.tapIndex) {
          case 0:
            wx.showToast({ title: '消息通知：已开启', icon: 'success' })
            break
          case 1:
            this.setData({ showVoiceInput: true })
            break
          case 2:
            this.clearCache()
            break
          case 3:
            wx.showModal({
              title: '关于我们',
              content: '物流司机端 v1.0.2\n\n为司机师傅提供便捷的配送管理工具\n\n© 2026 物流路径规划系统',
              showCancel: false
            })
            break
        }
      }
    })
  },

  // 帮助与反馈
  showHelp() {
    wx.showActionSheet({
      itemList: ['常见问题', '联系客服', '意见反馈'],
      success: (res) => {
        switch(res.tapIndex) {
          case 0:
            wx.showModal({
              title: '常见问题',
              content: 'Q: 如何接单？\nA: 在首页点击"接单"按钮\n\nQ: 如何导航？\nA: 点击"开始配送"后进入地图页\n\nQ: 如何签收？\nA: 到达目的地后点击"送达签收"',
              showCancel: false
            })
            break
          case 1:
            wx.makePhoneCall({ phoneNumber: '4001234567' })
            break
          case 2:
            wx.showToast({ title: '感谢您的反馈！', icon: 'success' })
            break
        }
      }
    })
  },

  // 清除缓存
  clearCache() {
    wx.showModal({
      title: '清除缓存',
      content: '确定要清除所有本地数据吗？这将删除您的订单记录。',
      success: (res) => {
        if (res.confirm) {
          wx.clearStorageSync()
          wx.showToast({ title: '已清除', icon: 'success' })
          this.loadStats()
        }
      }
    })
  },

  // 打开语音输入
  openVoiceInput() {
    this.setData({ showVoiceInput: true })
  },

  // 关闭语音输入
  closeVoiceInput() {
    this.setData({ showVoiceInput: false })
  },

  // 处理语音结果
  onVoiceResult(e) {
    const { text } = e.detail
    this.setData({ showVoiceInput: false })
    
    // 处理语音指令
    this.handleVoiceCommand(text)
  },

  // 处理语音指令
  handleVoiceCommand(text) {
    wx.showToast({ title: `识别到: ${text}`, icon: 'none', duration: 2000 })
    
    // 根据指令跳转
    setTimeout(() => {
      if (text.includes('订单') || text.includes('查看')) {
        wx.switchTab({ url: '/pages/orders/orders' })
      } else if (text.includes('地图') || text.includes('导航')) {
        wx.switchTab({ url: '/pages/map/map' })
      } else if (text.includes('首页')) {
        wx.switchTab({ url: '/pages/index/index' })
      } else if (text.includes('收入')) {
        this.showIncomeDetail()
      } else if (text.includes('设置')) {
        this.showSettings()
      }
    }, 500)
  },

  // 退出登录
  logout() {
    wx.showModal({
      title: '提示',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          wx.clearStorageSync()
          wx.showToast({ title: '已退出登录', icon: 'success' })
          setTimeout(() => {
            wx.reLaunch({ url: '/pages/login/login' })
          }, 1000)
        }
      }
    })
  },

  // 联系客服
  contactService() {
    wx.showModal({
      title: '联系客服',
      content: '客服电话：400-123-4567\n工作时间：9:00-18:00',
      confirmText: '拨打电话',
      success: (res) => {
        if (res.confirm) {
          wx.makePhoneCall({ phoneNumber: '4001234567' })
        }
      }
    })
  },

  formatMoney(value) {
    if (!value && value !== 0) return '¥0.00'
    return '¥' + Number(value).toFixed(2)
  }
})