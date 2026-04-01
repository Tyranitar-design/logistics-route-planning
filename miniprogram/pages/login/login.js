// pages/login/login.js
const app = getApp()

Page({
  data: {
    loading: false,
    phone: '',
    password: '',
    canUseGetUserProfile: false
  },

  onLoad() {
    // 检查是否已登录
    if (app.globalData.token) {
      wx.switchTab({ url: '/pages/index/index' })
    }
    
    // 检查是否支持 getUserProfile
    if (wx.getUserProfile) {
      this.setData({ canUseGetUserProfile: true })
    }
  },

  // 输入手机号
  onPhoneInput(e) {
    this.setData({ phone: e.detail.value })
  },

  // 输入密码
  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  // 账号密码登录
  async login() {
    const { phone, password } = this.data
    
    if (!phone || !password) {
      wx.showToast({
        title: '请输入账号和密码',
        icon: 'none'
      })
      return
    }
    
    this.setData({ loading: true })
    
    try {
      // 调用后端登录 API
      const res = await new Promise((resolve, reject) => {
        wx.request({
          url: `${app.globalData.baseUrl}/auth/login`,
          method: 'POST',
          data: {
            username: phone,
            password: password
          },
          header: {
            'Content-Type': 'application/json'
          },
          success: (response) => {
            if (response.statusCode === 200 && response.data.access_token) {
              resolve(response.data)
            } else {
              reject(new Error(response.data?.error || '登录失败'))
            }
          },
          fail: (err) => {
            reject(new Error('网络错误，请检查网络连接'))
          }
        })
      })
      
      // 保存 token 和用户信息
      app.setToken(res.access_token)
      app.setUserInfo({
        id: res.user_id,
        username: phone,
        role: res.role || 'driver'
      })
      
      wx.showToast({
        title: '登录成功',
        icon: 'success'
      })
      
      // 跳转首页
      setTimeout(() => {
        wx.switchTab({ url: '/pages/index/index' })
      }, 1000)
      
    } catch (err) {
      wx.showToast({
        title: err.message || '登录失败',
        icon: 'none'
      })
    } finally {
      this.setData({ loading: false })
    }
  },

  // 微信授权登录
  async wxLogin() {
    this.setData({ loading: true })
    
    try {
      await app.login()
      
      wx.showToast({
        title: '登录成功',
        icon: 'success'
      })
      
      // 跳转首页
      setTimeout(() => {
        wx.switchTab({ url: '/pages/index/index' })
      }, 1000)
    } catch (err) {
      wx.showToast({
        title: err.message || '登录失败',
        icon: 'none'
      })
    } finally {
      this.setData({ loading: false })
    }
  },

  // 演示账号登录
  demoLogin() {
    this.setData({
      phone: 'driver',
      password: 'driver123'
    }, () => {
      this.login()
    })
  }
})