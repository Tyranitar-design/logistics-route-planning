/**
 * WebSocket 实时推送服务
 * - 车辆位置实时更新
 * - 订单状态变化通知
 * - 预警信息弹窗
 */

import { io } from 'socket.io-client'
import { ElNotification, ElMessage } from 'element-plus'

class WebSocketService {
  constructor() {
    this.socket = null
    this.connected = false
    this.connecting = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.heartbeatInterval = null
    this.errorNotified = false
    this.listeners = {
      vehicle_positions: [],
      order_update: [],
      alert: [],
      connected: [],
      disconnected: []
    }
  }

  /**
   * 连接 WebSocket
   */
  connect(url = '') {
    const disabled = String(import.meta.env.VITE_WS_DISABLED || '').toLowerCase()
    if (['1', 'true', 'yes'].includes(disabled)) {
      console.info('[WS] 实时推送已通过 VITE_WS_DISABLED 禁用')
      return null
    }

    if (this.socket && (this.connected || this.connecting || this.socket.active || this.socket.connected)) {
      console.log('[WS] 已存在连接或重连任务，无需重复连接')
      return this.socket
    }

    if (this.socket) {
      this.socket.removeAllListeners()
      this.socket.close()
      this.socket = null
    }

    console.log('[WS] 正在连接...', url)
    
    // 开发环境优先跟随当前页面 host，避免 localhost / 127.0.0.1 混用导致 websocket 握手失败
    const currentProtocol = window.location.protocol === 'https:' ? 'https' : 'http'
    const currentHost = window.location.hostname || '127.0.0.1'
    const isProd = import.meta.env.PROD
    const configuredUrl = (import.meta.env.VITE_WS_URL || '').trim()
    const devSocketUrl = url || configuredUrl || `${currentProtocol}://${currentHost}:5000`
    const socketUrl = isProd ? (url || configuredUrl || window.location.origin) : devSocketUrl
    const configuredTransports = String(import.meta.env.VITE_WS_TRANSPORTS || '')
      .split(',')
      .map(item => item.trim())
      .filter(Boolean)
    const transports = configuredTransports.length
      ? configuredTransports
      : (isProd ? ['websocket', 'polling'] : ['polling'])

    console.log('[WS] 连接地址:', socketUrl)
    console.log('[WS] 传输模式:', transports.join(', '))

    this.connecting = true
    this.errorNotified = false
    this.socket = io(socketUrl, {
      path: '/socket.io/',
      transports,
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      upgrade: isProd,
      rememberUpgrade: false,
      forceNew: true,
      timeout: 20000
    })
    window.socketInstance = this.socket

    // 连接成功
    this.socket.on('connect', () => {
      console.log('[WS] 连接成功')
      this.connected = true
      this.connecting = false
      this.reconnectAttempts = 0
      this.errorNotified = false
      this.emit('connected')
      
      // 订阅频道
      this.subscribe('vehicles')
      this.subscribe('orders')
      this.subscribe('alerts')
    })

    // 连接断开
    this.socket.on('disconnect', (reason) => {
      console.log('[WS] 连接断开:', reason)
      this.connected = false
      this.connecting = false
      this.emit('disconnected', reason)
    })

    // 连接错误
    this.socket.on('connect_error', (error) => {
      console.warn('[WS] 连接错误:', error?.message || error)
      this.connecting = false
      this.reconnectAttempts++
      if (this.reconnectAttempts >= this.maxReconnectAttempts && !this.errorNotified) {
        this.errorNotified = true
        ElMessage.warning('实时推送连接失败，部分功能可能不可用')
      }
    })

    // 车辆位置更新
    this.socket.on('vehicle_positions', (data) => {
      this.emit('vehicle_positions', data)
    })

    // 订单状态更新
    this.socket.on('order_update', (data) => {
      console.log('[WS] 订单更新:', data)
      this.emit('order_update', data)
      
      // 弹窗通知
      const typeMap = {
        'pending': 'info',
        'assigned': 'info',
        'in_transit': 'warning',
        'delivered': 'success',
        'cancelled': 'error'
      }
      
      ElNotification({
        title: '订单状态更新',
        message: data.message,
        type: typeMap[data.status] || 'info',
        duration: 4000,
        position: 'top-right'
      })
    })

    // 预警信息
    this.socket.on('alert', (data) => {
      console.log('[WS] 预警:', data)
      this.emit('alert', data)
      
      // 弹窗通知
      const iconMap = {
        'weather': '🌤️',
        'traffic': '🚗',
        'order': '📦',
        'vehicle': '🚛',
        'system': '📢'
      }
      
      const typeMap = {
        'info': 'info',
        'warning': 'warning',
        'danger': 'error'
      }
      
      ElNotification({
        title: `${iconMap[data.type] || '📢'} ${data.title}`,
        message: data.message,
        type: typeMap[data.level] || 'warning',
        duration: data.level === 'danger' ? 0 : 5000,  // 危险级别不自动关闭
        position: 'top-right'
      })
    })

    // 订阅确认
    this.socket.on('subscribed', (data) => {
      console.log('[WS] 已订阅:', data.channel)
    })

    // 心跳响应
    this.socket.on('pong', (data) => {
      // console.log('[WS] Pong:', data.time)
    })

    // 启动心跳
    this.startHeartbeat()
    return this.socket
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.connected = false
      this.connecting = false
      window.socketInstance = null
      if (this.heartbeatInterval) {
        clearInterval(this.heartbeatInterval)
        this.heartbeatInterval = null
      }
      console.log('[WS] 已断开连接')
    }
  }

  /**
   * 订阅频道
   */
  subscribe(channel) {
    if (this.socket && this.connected) {
      this.socket.emit(`subscribe_${channel}`)
    }
  }

  /**
   * 发送心跳
   */
  startHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
    }
    this.heartbeatInterval = setInterval(() => {
      if (this.socket && this.connected) {
        this.socket.emit('ping')
      }
    }, 30000)  // 30秒心跳
  }

  /**
   * 添加事件监听器
   */
  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback)
    }
  }

  /**
   * 移除事件监听器
   */
  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback)
    }
  }

  /**
   * 触发事件
   */
  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data))
    }
  }

  /**
   * 获取连接状态
   */
  isConnected() {
    return this.connected
  }
}

// 导出单例
export const wsService = new WebSocketService()

if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    wsService.disconnect()
  })
}

export default wsService
