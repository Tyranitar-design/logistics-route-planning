// utils/voice.js - 语音识别和播报工具

/**
 * 语音管理器
 * 支持语音识别和语音播报
 */
class VoiceManager {
  constructor() {
    this.recorderManager = null
    this.innerAudioContext = null
    this.isRecording = false
    this.onRecognizeCallback = null
  }

  /**
   * 初始化录音管理器
   */
  initRecorder() {
    if (!this.recorderManager) {
      this.recorderManager = wx.getRecorderManager()
      
      this.recorderManager.onStart(() => {
        console.log('[Voice] 开始录音')
        this.isRecording = true
      })
      
      this.recorderManager.onStop((res) => {
        console.log('[Voice] 录音结束', res)
        this.isRecording = false
        
        // 这里可以调用语音识别 API
        if (this.onRecognizeCallback) {
          this.onRecognizeCallback({
            success: true,
            tempFilePath: res.tempFilePath,
            duration: res.duration
          })
        }
      })
      
      this.recorderManager.onError((err) => {
        console.error('[Voice] 录音错误', err)
        this.isRecording = false
        if (this.onRecognizeCallback) {
          this.onRecognizeCallback({
            success: false,
            error: err
          })
        }
      })
    }
    return this.recorderManager
  }

  /**
   * 开始录音
   */
  startRecord(callback) {
    this.onRecognizeCallback = callback
    this.initRecorder()
    
    // 检查权限
    wx.getSetting({
      success: (res) => {
        if (res.authSetting['scope.record']) {
          this.recorderManager.start({
            format: 'mp3',
            sampleRate: 16000,
            numberOfChannels: 1,
            encodeBitRate: 96000
          })
        } else {
          wx.authorize({
            scope: 'scope.record',
            success: () => {
              this.recorderManager.start({
                format: 'mp3',
                sampleRate: 16000
              })
            },
            fail: () => {
              wx.showModal({
                title: '需要录音权限',
                content: '请在设置中开启录音权限',
                confirmText: '去设置',
                success: (res) => {
                  if (res.confirm) {
                    wx.openSetting()
                  }
                }
              })
            }
          })
        }
      }
    })
  }

  /**
   * 停止录音
   */
  stopRecord() {
    if (this.recorderManager && this.isRecording) {
      this.recorderManager.stop()
    }
  }

  /**
   * 语音播报（使用系统 TTS）
   * @param {String} text - 要播报的文字
   * @param {Object} options - 配置选项
   */
  speak(text, options = {}) {
    // 微信小程序没有原生 TTS，使用插件或第三方服务
    // 这里提供几种方案：
    
    // 方案1：使用微信同声传译插件（需要申请）
    // 方案2：使用百度/讯飞等第三方 TTS API
    // 方案3：显示文字提示
    
    console.log('[Voice] 播报:', text)
    
    // 显示文字提示
    wx.showModal({
      title: options.title || '语音提示',
      content: text,
      showCancel: false,
      confirmText: '知道了'
    })
  }

  /**
   * 播放音频文件
   * @param {String} url - 音频文件地址
   */
  playAudio(url) {
    if (!this.innerAudioContext) {
      this.innerAudioContext = wx.createInnerAudioContext()
    }
    
    this.innerAudioContext.src = url
    this.innerAudioContext.play()
  }

  /**
   * 停止播放
   */
  stopAudio() {
    if (this.innerAudioContext) {
      this.innerAudioContext.stop()
    }
  }

  /**
   * 销毁资源
   */
  destroy() {
    if (this.innerAudioContext) {
      this.innerAudioContext.destroy()
      this.innerAudioContext = null
    }
    this.recorderManager = null
  }
}

// 导出单例
const voiceManager = new VoiceManager()

module.exports = {
  voiceManager,
  VoiceManager
}