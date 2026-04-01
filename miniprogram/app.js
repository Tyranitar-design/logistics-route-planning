// app.js - 小程序入口
App({
  globalData: {
    // API 基础地址 - 真机调试时使用局域网 IP
    baseUrl: 'http://100.106.251.139:5000/api',
    // baseUrl: 'http://localhost:5000/api',  // 本地调试用
    userInfo: null,
    token: null,
    driverInfo: null,
    systemInfo: null,
    // 版本号，用于检测是否需要清除旧数据
    dataVersion: '1.0.3'
  },

  onLaunch() {
    // 检查数据版本，必要时清除旧数据
    this.checkDataVersion()
    
    // 检查登录状态
    this.checkLoginStatus()
    
    // 获取系统信息
    try {
      const deviceInfo = wx.getDeviceInfo()
      const windowInfo = wx.getWindowInfo()
      this.globalData.systemInfo = {
        ...deviceInfo,
        ...windowInfo
      }
    } catch (e) {
      console.error('获取系统信息失败:', e)
    }
    
    // 检查更新
    this.checkUpdate()
  },

  // 检查数据版本
  checkDataVersion() {
    const savedVersion = wx.getStorageSync('dataVersion')
    if (savedVersion !== this.globalData.dataVersion) {
      console.log('[App] 数据版本不匹配，清除旧数据...')
      // 清除所有本地数据
      wx.clearStorageSync()
      // 保存新版本号
      wx.setStorageSync('dataVersion', this.globalData.dataVersion)
      console.log('[App] 数据已重置')
    }
  },

  // 检查登录状态
  checkLoginStatus() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    
    if (token && userInfo) {
      this.globalData.token = token
      this.globalData.userInfo = userInfo
      this.getDriverInfo()
    } else {
      // 未登录，跳转到登录页
      wx.reLaunch({ url: '/pages/login/login' })
    }
  },

  // 获取司机信息
  getDriverInfo() {
    wx.request({
      url: `${this.globalData.baseUrl}/driver/info`,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${this.globalData.token}`
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          this.globalData.driverInfo = res.data.data || res.data
        }
      }
    })
  },

  // 设置 token
  setToken(token) {
    this.globalData.token = token
    wx.setStorageSync('token', token)
  },

  // 设置用户信息
  setUserInfo(userInfo) {
    this.globalData.userInfo = userInfo
    wx.setStorageSync('userInfo', userInfo)
  },

  // 检查小程序更新
  checkUpdate() {
    if (!wx.canIUse('getUpdateManager')) return
    
    const updateManager = wx.getUpdateManager()
    
    updateManager.onCheckForUpdate((res) => {
      if (res.hasUpdate) {
        console.log('检测到新版本')
      }
    })
    
    updateManager.onUpdateReady(() => {
      wx.showModal({
        title: '更新提示',
        content: '新版本已准备好，是否重启应用？',
        success: (res) => {
          if (res.confirm) {
            updateManager.applyUpdate()
          }
        }
      })
    })
    
    updateManager.onUpdateFailed(() => {
      console.log('更新失败')
    })
  },

  // 登录
  login() {
    return new Promise((resolve, reject) => {
      wx.login({
        success: (res) => {
          if (res.code) {
            // 发送 code 到后端换取 token
            wx.request({
              url: `${this.globalData.baseUrl}/auth/wechat-login`,
              method: 'POST',
              data: { code: res.code },
              success: (loginRes) => {
                if (loginRes.data.code === 200) {
                  const { token, userInfo } = loginRes.data.data
                  this.globalData.token = token
                  this.globalData.userInfo = userInfo
                  wx.setStorageSync('token', token)
                  wx.setStorageSync('userInfo', userInfo)
                  resolve(userInfo)
                } else {
                  // 模拟登录成功
                  const mockUser = {
                    id: 1,
                    real_name: '测试司机',
                    phone: '13800138000'
                  }
                  this.globalData.userInfo = mockUser
                  this.globalData.token = 'mock_token_123'
                  resolve(mockUser)
                }
              },
              fail: () => {
                // 网络失败时模拟登录
                const mockUser = {
                  id: 1,
                  real_name: '测试司机',
                  phone: '13800138000'
                }
                this.globalData.userInfo = mockUser
                this.globalData.token = 'mock_token_123'
                resolve(mockUser)
              }
            })
          } else {
            reject(new Error('wx.login 失败'))
          }
        },
        fail: reject
      })
    })
  },

  // 退出登录
  logout() {
    this.globalData.token = null
    this.globalData.userInfo = null
    this.globalData.driverInfo = null
    wx.removeStorageSync('token')
    wx.removeStorageSync('userInfo')
    wx.reLaunch({ url: '/pages/login/login' })
  }
})