// components/location-tracker/location-tracker.js
const { locationApi } = require('../../utils/api')
const app = getApp()

Component({
  properties: {
    // 是否启用
    enabled: {
      type: Boolean,
      value: false
    },
    // 当前任务ID
    taskId: {
      type: Number,
      value: null
    },
    // 上报间隔（秒）
    interval: {
      type: Number,
      value: 30
    }
  },

  data: {
    isTracking: false,
    lastReportTime: null,
    currentLocation: null
  },

  lifetimes: {
    attached() {
      if (this.data.enabled) {
        this.startTracking()
      }
    },

    detached() {
      this.stopTracking()
    }
  },

  observers: {
    'enabled': function(enabled) {
      if (enabled) {
        this.startTracking()
      } else {
        this.stopTracking()
      }
    }
  },

  methods: {
    // 开始追踪
    startTracking() {
      if (this.data.isTracking) return
      
      console.log('[LocationTracker] 开始轨迹追踪')
      
      this.setData({ isTracking: true })
      
      // 立即上报一次
      this.reportLocation()
      
      // 设置定时器
      this.timer = setInterval(() => {
        this.reportLocation()
      }, this.data.interval * 1000)
    },

    // 停止追踪
    stopTracking() {
      if (!this.data.isTracking) return
      
      console.log('[LocationTracker] 停止轨迹追踪')
      
      if (this.timer) {
        clearInterval(this.timer)
        this.timer = null
      }
      
      this.setData({ isTracking: false })
    },

    // 上报位置
    async reportLocation() {
      try {
        const location = await this.getLocation()
        
        if (!location) return
        
        const data = {
          latitude: location.latitude,
          longitude: location.longitude,
          accuracy: location.accuracy || 0,
          speed: location.speed || 0,
          direction: location.horizontalAccuracy || 0
        }
        
        // 如果有任务ID，带上
        if (this.data.taskId) {
          data.task_id = this.data.taskId
        }
        
        // 调用API上报
        await locationApi.report(data)
        
        this.setData({
          lastReportTime: new Date(),
          currentLocation: location
        })
        
        console.log('[LocationTracker] 位置上报成功', data)
        
        // 触发自定义事件
        this.triggerEvent('locationReported', { location, time: new Date() })
        
      } catch (err) {
        console.error('[LocationTracker] 位置上报失败:', err)
      }
    },

    // 获取位置
    getLocation() {
      return new Promise((resolve, reject) => {
        wx.getLocation({
          type: 'gcj02',
          success: resolve,
          fail: (err) => {
            console.error('[LocationTracker] 获取位置失败:', err)
            resolve(null)
          }
        })
      })
    },

    // 获取当前位置（供外部调用）
    getCurrentLocation() {
      return this.data.currentLocation
    },

    // 手动上报（供外部调用）
    manualReport() {
      return this.reportLocation()
    }
  }
})