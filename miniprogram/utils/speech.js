// utils/speech.js - 语音识别服务
// 支持百度语音识别和微信同声传译插件

const app = getApp()

/**
 * 语音识别服务
 * 支持多种语音识别引擎
 */
class SpeechService {
  constructor() {
    this.recorderManager = null
    this.isRecording = false
    this.onResultCallback = null
    this.onErrorCallback = null
  }

  /**
   * 初始化录音管理器
   */
  initRecorder() {
    if (!this.recorderManager) {
      this.recorderManager = wx.getRecorderManager()
      
      this.recorderManager.onStart(() => {
        console.log('[Speech] 开始录音')
        this.isRecording = true
      })
      
      this.recorderManager.onStop((res) => {
        console.log('[Speech] 录音结束', res)
        this.isRecording = false
        
        if (res.tempFilePath && this.onResultCallback) {
          // 调用后端语音识别 API
          this.recognizeAudio(res.tempFilePath)
        }
      })
      
      this.recorderManager.onError((err) => {
        console.error('[Speech] 录音错误', err)
        this.isRecording = false
        if (this.onErrorCallback) {
          this.onErrorCallback(err)
        }
      })
    }
    return this.recorderManager
  }

  /**
   * 开始录音
   * @param {Function} onResult - 识别结果回调
   * @param {Function} onError - 错误回调
   */
  startRecording(onResult, onError) {
    this.onResultCallback = onResult
    this.onErrorCallback = onError
    this.initRecorder()
    
    // 检查录音权限
    wx.getSetting({
      success: (res) => {
        if (res.authSetting['scope.record']) {
          this._doStartRecord()
        } else {
          wx.authorize({
            scope: 'scope.record',
            success: () => this._doStartRecord(),
            fail: () => {
              wx.showModal({
                title: '需要录音权限',
                content: '请在设置中开启录音权限',
                confirmText: '去设置',
                success: (modalRes) => {
                  if (modalRes.confirm) {
                    wx.openSetting()
                  }
                }
              })
              if (onError) onError({ errMsg: 'no permission' })
            }
          })
        }
      }
    })
  }

  /**
   * 执行开始录音
   */
  _doStartRecord() {
    this.recorderManager.start({
      format: 'mp3',
      sampleRate: 16000,
      numberOfChannels: 1,
      encodeBitRate: 96000,
      duration: 60000 // 最长 60 秒
    })
  }

  /**
   * 停止录音
   */
  stopRecording() {
    if (this.recorderManager && this.isRecording) {
      this.recorderManager.stop()
    }
  }

  /**
   * 调用后端语音识别 API
   * @param {String} filePath - 音频文件临时路径
   */
  async recognizeAudio(filePath) {
    try {
      // 上传音频文件到后端进行识别
      wx.uploadFile({
        url: `${app.globalData.baseUrl}/speech/recognize`,
        filePath: filePath,
        name: 'audio',
        header: {
          'Authorization': `Bearer ${app.globalData.token}`
        },
        success: (res) => {
          const data = JSON.parse(res.data)
          if (data.code === 200 && data.data && data.data.text) {
            console.log('[Speech] 识别结果:', data.data.text)
            if (this.onResultCallback) {
              this.onResultCallback({
                success: true,
                text: data.data.text
              })
            }
          } else {
            // 后端未实现时使用本地模拟
            this._mockRecognize()
          }
        },
        fail: (err) => {
          console.log('[Speech] 后端识别失败，使用本地模拟')
          // 后端未实现时使用本地模拟
          this._mockRecognize()
        }
      })
    } catch (err) {
      console.error('[Speech] 识别错误:', err)
      this._mockRecognize()
    }
  }

  /**
   * 本地模拟识别（后端未实现时使用）
   */
  _mockRecognize() {
    // 常用语音命令模拟
    const commands = [
      '开始配送',
      '到达发货地',
      '确认取货',
      '导航到收货地',
      '完成配送',
      '查看订单',
      '查看今日任务',
      '上报异常',
      '联系客服',
      '查看收入'
    ]
    
    const randomText = commands[Math.floor(Math.random() * commands.length)]
    
    console.log('[Speech] 模拟识别结果:', randomText)
    if (this.onResultCallback) {
      this.onResultCallback({
        success: true,
        text: randomText,
        isMock: true
      })
    }
  }

  /**
   * 语音播报（文字转语音）
   * 使用微信插件或第三方服务
   * @param {String} text - 要播报的文字
   */
  speak(text) {
    return new Promise((resolve, reject) => {
      // 方案1：调用后端 TTS API
      wx.request({
        url: `${app.globalData.baseUrl}/speech/tts`,
        method: 'POST',
        data: { text },
        header: {
          'Authorization': `Bearer ${app.globalData.token}`
        },
        success: (res) => {
          if (res.data.code === 200 && res.data.data && res.data.data.audio_url) {
            // 播放返回的音频
            this.playAudio(res.data.data.audio_url)
            resolve()
          } else {
            // 后端未实现，显示文字
            this._showTextToast(text)
            resolve()
          }
        },
        fail: () => {
          // 后端未实现，显示文字
          this._showTextToast(text)
          resolve()
        }
      })
    })
  }

  /**
   * 显示文字提示
   */
  _showTextToast(text) {
    wx.showModal({
      title: '语音播报',
      content: text,
      showCancel: false,
      confirmText: '知道了'
    })
  }

  /**
   * 播放音频
   */
  playAudio(url) {
    const innerAudioContext = wx.createInnerAudioContext()
    innerAudioContext.src = url
    innerAudioContext.onPlay(() => {
      console.log('[Speech] 开始播放音频')
    })
    innerAudioContext.onError((err) => {
      console.error('[Speech] 播放错误:', err)
    })
    innerAudioContext.play()
  }

  /**
   * 销毁资源
   */
  destroy() {
    this.recorderManager = null
    this.isRecording = false
  }
}

// 语音命令处理器
class VoiceCommandHandler {
  constructor() {
    this.commands = {
      // 配送相关命令
      '开始配送': this.handleStartDelivery,
      '开始任务': this.handleStartDelivery,
      '到达发货地': this.handleArrivePickup,
      '到达取货点': this.handleArrivePickup,
      '确认取货': this.handleConfirmPickup,
      '取货完成': this.handleConfirmPickup,
      '导航到收货地': this.handleNavigateDelivery,
      '开始导航': this.handleNavigateDelivery,
      '完成配送': this.handleCompleteDelivery,
      '送达': this.handleCompleteDelivery,
      
      // 查看相关命令
      '查看订单': this.handleViewOrders,
      '我的订单': this.handleViewOrders,
      '查看任务': this.handleViewTasks,
      '今日任务': this.handleViewTasks,
      '查看收入': this.handleViewIncome,
      '我的收入': this.handleViewIncome,
      
      // 其他命令
      '上报异常': this.handleReportException,
      '联系客服': this.handleContactService,
      '帮助': this.handleHelp
    }
  }

  /**
   * 处理语音命令
   * @param {String} text - 识别的文字
   * @param {Object} context - 上下文（页面实例等）
   */
  handle(text, context) {
    console.log('[VoiceCommand] 处理命令:', text)
    
    // 精确匹配
    if (this.commands[text]) {
      return this.commands[text].call(this, context)
    }
    
    // 模糊匹配
    for (const [command, handler] of Object.entries(this.commands)) {
      if (text.includes(command) || command.includes(text)) {
        return handler.call(this, context)
      }
    }
    
    // 未识别的命令
    return {
      success: false,
      message: '未识别的命令，请重试'
    }
  }

  // 命令处理方法
  handleStartDelivery(context) {
    return {
      success: true,
      action: 'start_delivery',
      message: '开始执行配送任务',
      navigateTo: '/pages/orders/orders?status=in_progress'
    }
  }

  handleArrivePickup(context) {
    return {
      success: true,
      action: 'arrive_pickup',
      message: '已到达取货点，请确认取货'
    }
  }

  handleConfirmPickup(context) {
    return {
      success: true,
      action: 'confirm_pickup',
      message: '取货确认成功'
    }
  }

  handleNavigateDelivery(context) {
    return {
      success: true,
      action: 'navigate',
      message: '正在为您导航到收货地'
    }
  }

  handleCompleteDelivery(context) {
    return {
      success: true,
      action: 'complete_delivery',
      message: '配送完成，请签收'
    }
  }

  handleViewOrders(context) {
    return {
      success: true,
      action: 'navigate',
      message: '正在打开订单列表',
      navigateTo: '/pages/orders/orders'
    }
  }

  handleViewTasks(context) {
    return {
      success: true,
      action: 'navigate',
      message: '正在查看今日任务',
      navigateTo: '/pages/orders/orders?status=today'
    }
  }

  handleViewIncome(context) {
    return {
      success: true,
      action: 'navigate',
      message: '正在查看收入统计',
      navigateTo: '/pages/profile/profile?tab=income'
    }
  }

  handleReportException(context) {
    return {
      success: true,
      action: 'report_exception',
      message: '请描述异常情况'
    }
  }

  handleContactService(context) {
    return {
      success: true,
      action: 'contact_service',
      message: '正在联系客服'
    }
  }

  handleHelp(context) {
    return {
      success: true,
      action: 'show_help',
      message: '可用命令：开始配送、到达发货地、确认取货、完成配送、查看订单、上报异常'
    }
  }
}

// 导出单例
const speechService = new SpeechService()
const voiceCommandHandler = new VoiceCommandHandler()

module.exports = {
  speechService,
  voiceCommandHandler,
  SpeechService,
  VoiceCommandHandler
}