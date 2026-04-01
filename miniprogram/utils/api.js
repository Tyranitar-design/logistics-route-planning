// utils/api.js - API 请求封装

const app = getApp()

/**
 * 封装 wx.request
 */
const request = (options) => {
  return new Promise((resolve, reject) => {
    const { url, method = 'GET', data = {}, header = {} } = options
    
    if (app.globalData.token) {
      header['Authorization'] = `Bearer ${app.globalData.token}`
    }
    
    wx.request({
      url: `${app.globalData.baseUrl}${url}`,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        ...header
      },
      success: (res) => {
        if (res.statusCode === 200) {
          if (res.data.code === 200) {
            resolve(res.data)
          } else if (res.data.code === 401) {
            app.logout()
            reject(new Error('登录已过期'))
          } else {
            reject(new Error(res.data.message || '请求失败'))
          }
        } else {
          reject(new Error(`网络错误: ${res.statusCode}`))
        }
      },
      fail: (err) => {
        wx.showToast({ title: '网络连接失败', icon: 'none' })
        reject(err)
      }
    })
  })
}

// ==================== 司机相关 ====================
const driverApi = {
  // 获取司机信息
  getInfo: () => request({ url: '/driver/info' }),
  
  // 获取车辆信息
  getVehicle: () => request({ url: '/driver/vehicle' }),
  
  // 更新车辆状态
  updateVehicleStatus: (status) => request({
    url: '/driver/vehicle/status',
    method: 'PUT',
    data: { status }
  }),
  
  // 今日统计
  getTodayStats: () => request({ url: '/driver/stats/today' }),
  
  // 收入统计
  getIncomeStats: (days = 30) => request({
    url: '/driver/stats/income',
    data: { days }
  })
}

// ==================== 派单通知 ====================
const dispatchApi = {
  // 获取派单通知
  getNotifications: (page = 1, pageSize = 20) => request({
    url: '/driver/dispatch/notifications',
    data: { page, page_size: pageSize }
  }),
  
  // 接受派单
  accept: (dispatchId) => request({
    url: `/driver/dispatch/${dispatchId}/accept`,
    method: 'POST'
  }),
  
  // 拒绝派单
  reject: (dispatchId, reason = '') => request({
    url: `/driver/dispatch/${dispatchId}/reject`,
    method: 'POST',
    data: { reason }
  })
}

// ==================== 运输任务 ====================
const taskApi = {
  // 获取任务列表
  getList: (status, date) => request({
    url: '/driver/tasks',
    data: { status, date }
  }),
  
  // 获取任务详情
  getDetail: (taskId) => request({
    url: `/driver/tasks/${taskId}`
  }),
  
  // 开始任务
  start: (taskId, location) => request({
    url: `/driver/tasks/${taskId}/start`,
    method: 'POST',
    data: location
  }),
  
  // 到达取货点
  arrivePickup: (taskId, location) => request({
    url: `/driver/tasks/${taskId}/arrive`,
    method: 'POST',
    data: location
  }),
  
  // 确认取货
  confirmPickup: (taskId, photo) => request({
    url: `/driver/tasks/${taskId}/pickup`,
    method: 'POST',
    data: { photo }
  }),
  
  // 送达签收
  deliver: (taskId, data) => request({
    url: `/driver/tasks/${taskId}/delivery`,
    method: 'POST',
    data
  }),
  
  // 上报异常
  reportException: (taskId, data) => request({
    url: `/driver/tasks/${taskId}/exception`,
    method: 'POST',
    data
  })
}

// ==================== 位置轨迹 ====================
const locationApi = {
  // 上报位置
  report: (data) => request({
    url: '/driver/location/report',
    method: 'POST',
    data
  }),
  
  // 获取轨迹历史
  getHistory: (taskId, startTime, endTime) => request({
    url: '/driver/location/history',
    data: { task_id: taskId, start_time: startTime, end_time: endTime }
  })
}

// ==================== 照片上传 ====================
const uploadApi = {
  // 上传照片
  uploadPhoto: (filePath, taskId, type = 'general') => {
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: `${app.globalData.baseUrl}/driver/upload/photo`,
        filePath,
        name: 'photo',
        formData: {
          task_id: taskId,
          type
        },
        header: {
          'Authorization': `Bearer ${app.globalData.token}`
        },
        success: (res) => {
          const data = JSON.parse(res.data)
          if (data.code === 200) {
            resolve(data.data)
          } else {
            reject(new Error(data.message))
          }
        },
        fail: reject
      })
    })
  }
}

// ==================== 消息 ====================
const messageApi = {
  // 获取消息列表
  getList: (type, page = 1, pageSize = 20) => request({
    url: '/driver/messages',
    data: { type, page, page_size: pageSize }
  }),
  
  // 标记已读
  markRead: (messageId) => request({
    url: `/driver/messages/${messageId}/read`,
    method: 'POST'
  }),
  
  // 未读数量
  getUnreadCount: () => request({
    url: '/driver/messages/unread-count'
  })
}

module.exports = {
  request,
  driverApi,
  dispatchApi,
  taskApi,
  locationApi,
  uploadApi,
  messageApi
}