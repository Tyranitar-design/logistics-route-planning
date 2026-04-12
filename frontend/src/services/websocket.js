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
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
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
    if (this.socket && this.connected) {
      console.log('[WS] 已经连接，无需重复连接')
      return
    }

    console.log('[WS] 正在连接...', url)
    
    // 开发环境使用后端地址，生产环境使用当前域名
    const socketUrl = import.meta.env.PROD ? window.location.origin : 'http://localhost:5000'

    console.log('[WS] 连接地址:', socketUrl)

    this.socket = io(socketUrl, {
      path: '/socket.io/',
      transports: ['websocket', 'polling'],  // websocket 优先
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      upgrade: true,
      rememberUpgrade: true,
      forceNew: true,
      timeout: 20000
    })

    // 连接成功
    this.socket.on('connect', () => {
      console.log('[WS] 连接成功')
      this.connected = true
      this.reconnectAttempts = 0
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
      this.emit('disconnected', reason)
    })

    // 连接错误
    this.socket.on('connect_error', (error) => {
      console.error('[WS] 连接错误:', error)
      this.reconnectAttempts++
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
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
  }

  /**
   * 断开连接
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.connected = false
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

export default wsService