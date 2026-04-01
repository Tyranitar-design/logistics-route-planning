// utils/util.js - 通用工具函数

/**
 * 格式化时间
 * @param {Date|String|Number} date - 日期
 * @param {String} format - 格式
 * @returns {String}
 */
const formatTime = (date, format = 'YYYY-MM-DD HH:mm') => {
  if (!date) return '-'
  
  const d = new Date(date)
  if (isNaN(d.getTime())) return '-'
  
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const minute = String(d.getMinutes()).padStart(2, '0')
  const second = String(d.getSeconds()).padStart(2, '0')
  
  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hour)
    .replace('mm', minute)
    .replace('ss', second)
}

/**
 * 格式化距离
 * @param {Number} meters - 米
 * @returns {String}
 */
const formatDistance = (meters) => {
  if (!meters && meters !== 0) return '-'
  if (meters < 1000) {
    return `${Math.round(meters)}米`
  }
  return `${(meters / 1000).toFixed(1)}公里`
}

/**
 * 格式化金额
 * @param {Number} amount - 金额
 * @returns {String}
 */
const formatMoney = (amount) => {
  if (!amount && amount !== 0) return '-'
  return `¥${Number(amount).toFixed(2)}`
}

/**
 * 格式化时长
 * @param {Number} minutes - 分钟
 * @returns {String}
 */
const formatDuration = (minutes) => {
  if (!minutes && minutes !== 0) return '-'
  if (minutes < 60) {
    return `${Math.round(minutes)}分钟`
  }
  const hours = Math.floor(minutes / 60)
  const mins = Math.round(minutes % 60)
  return mins > 0 ? `${hours}小时${mins}分钟` : `${hours}小时`
}

/**
 * 获取订单状态文字
 * @param {String} status - 状态码
 * @returns {Object} - { text, class }
 */
const getOrderStatus = (status) => {
  const statusMap = {
    pending: { text: '待接单', class: 'warning' },
    accepted: { text: '已接单', class: 'primary' },
    in_progress: { text: '配送中', class: 'primary' },
    completed: { text: '已完成', class: 'success' },
    cancelled: { text: '已取消', class: 'danger' }
  }
  return statusMap[status] || { text: '未知', class: 'info' }
}

/**
 * 显示加载中
 * @param {String} title - 提示文字
 */
const showLoading = (title = '加载中...') => {
  wx.showLoading({
    title,
    mask: true
  })
}

/**
 * 隐藏加载中
 */
const hideLoading = () => {
  wx.hideLoading()
}

/**
 * 显示提示
 * @param {String} title - 提示文字
 * @param {String} icon - 图标类型
 */
const showToast = (title, icon = 'none') => {
  wx.showToast({
    title,
    icon,
    duration: 2000
  })
}

/**
 * 显示确认对话框
 * @param {String} title - 标题
 * @param {String} content - 内容
 * @returns {Promise}
 */
const showConfirm = (title, content) => {
  return new Promise((resolve, reject) => {
    wx.showModal({
      title,
      content,
      success: (res) => {
        if (res.confirm) {
          resolve(true)
        } else {
          resolve(false)
        }
      },
      fail: reject
    })
  })
}

/**
 * 获取位置
 * @returns {Promise}
 */
const getLocation = () => {
  return new Promise((resolve, reject) => {
    wx.getLocation({
      type: 'gcj02',
      success: resolve,
      fail: reject
    })
  })
}

/**
 * 打开地图导航
 * @param {Number} latitude - 纬度
 * @param {Number} longitude - 经度
 * @param {String} name - 地点名称
 */
const openNavigation = (latitude, longitude, name = '') => {
  wx.openLocation({
    latitude,
    longitude,
    name,
    scale: 18
  })
}

/**
 * 拨打电话
 * @param {String} phoneNumber - 电话号码
 */
const makePhoneCall = (phoneNumber) => {
  wx.makePhoneCall({
    phoneNumber
  })
}

module.exports = {
  formatTime,
  formatDistance,
  formatMoney,
  formatDuration,
  getOrderStatus,
  showLoading,
  hideLoading,
  showToast,
  showConfirm,
  getLocation,
  openNavigation,
  makePhoneCall
}