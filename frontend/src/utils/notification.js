/**
 * 统一的通知提示工具
 * 提供成功、警告、错误、信息四种样式的通知
 */

import { ElNotification, ElMessage, ElLoading } from 'element-plus'

// 默认配置
const defaultOptions = {
  duration: 3000,  // 默认3秒后关闭
  position: 'top-right',
  showClose: true
}

/**
 * 成功通知
 * @param {string} title 标题
 * @param {string} message 内容
 * @param {object} options 配置选项
 */
export function success(title, message = '', options = {}) {
  return ElNotification({
    title,
    message,
    type: 'success',
    ...defaultOptions,
    ...options
  })
}

/**
 * 警告通知
 * @param {string} title 标题
 * @param {string} message 内容
 * @param {object} options 配置选项
 */
export function warning(title, message = '', options = {}) {
  return ElNotification({
    title,
    message,
    type: 'warning',
    duration: 5000,  // 警告显示更长
    ...defaultOptions,
    ...options
  })
}

/**
 * 错误通知
 * @param {string} title 标题
 * @param {string} message 内容
 * @param {object} options 配置选项
 */
export function error(title, message = '', options = {}) {
  return ElNotification({
    title,
    message,
    type: 'error',
    duration: 0,  // 错误默认不自动关闭
    ...defaultOptions,
    ...options
  })
}

/**
 * 信息通知
 * @param {string} title 标题
 * @param {string} message 内容
 * @param {object} options 配置选项
 */
export function info(title, message = '', options = {}) {
  return ElNotification({
    title,
    message,
    type: 'info',
    ...defaultOptions,
    ...options
  })
}

/**
 * 加载中提示（持久化）
 * @param {string} message 提示信息
 * @returns {object} 关闭函数
 */
export function loading(message = '加载中...') {
  return ElLoading.service({
    lock: true,
    text: message,
    background: 'rgba(0, 0, 0, 0.7)'
  })
}

/**
 * 进度提示
 * @param {string} title 标题
 * @param {number} progress 进度 0-100
 * @param {string} status 状态文本
 */
export function progress(title, progress, status = '') {
  return ElNotification({
    title,
    message: `${status} ${progress}%`,
    type: 'info',
    duration: 0,
    position: 'bottom-right',
    customClass: 'progress-notification'
  })
}

/**
 * 快捷消息提示（轻量级）
 */
export const toast = {
  success: (msg) => ElMessage.success(msg),
  warning: (msg) => ElMessage.warning(msg),
  error: (msg) => ElMessage.error(msg),
  info: (msg) => ElMessage.info(msg)
}

/**
 * 确认对话框快捷方法
 * @param {string} message 确认信息
 * @param {object} options 配置
 */
export function confirm(message, options = {}) {
  return ElMessageBox.confirm(message, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
    ...options
  })
}

// 默认导出所有方法
export default {
  success,
  warning,
  error,
  info,
  loading,
  progress,
  toast,
  confirm
}
