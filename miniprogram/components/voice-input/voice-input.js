// components/voice-input/voice-input.js
const { speechService, voiceCommandHandler } = require('../../utils/speech')

Component({
  properties: {
    // 是否显示
    show: {
      type: Boolean,
      value: false
    },
    // 提示文字
    placeholder: {
      type: String,
      value: '按住说话'
    },
    // 是否自动执行命令
    autoExecute: {
      type: Boolean,
      value: true
    }
  },

  data: {
    isRecording: false,
    voiceText: '',
    animationClass: '',
    statusText: '按住说话，松开识别',
    recognizedText: ''
  },

  lifetimes: {
    detached() {
      speechService.destroy()
    }
  },

  methods: {
    // 长按开始录音
    onTouchStart() {
      this.setData({ 
        isRecording: true,
        animationClass: 'pulse',
        statusText: '正在录音...',
        recognizedText: ''
      })
      
      speechService.startRecording(
        (result) => {
          this.setData({ 
            isRecording: false,
            animationClass: ''
          })
          
          if (result.success) {
            const text = result.text
            this.setData({ 
              recognizedText: text,
              statusText: '识别完成'
            })
            
            // 自动执行命令
            if (this.properties.autoExecute) {
              this.executeCommand(text)
            } else {
              // 只返回识别结果
              this.triggerEvent('result', { text, isMock: result.isMock })
            }
          }
        },
        (error) => {
          this.setData({ 
            isRecording: false,
            animationClass: '',
            statusText: '录音失败，请重试'
          })
          this.triggerEvent('error', error)
        }
      )
    },

    // 松开停止录音
    onTouchEnd() {
      if (this.data.isRecording) {
        this.setData({ statusText: '正在识别...' })
        speechService.stopRecording()
      }
    },

    // 执行语音命令
    executeCommand(text) {
      const result = voiceCommandHandler.handle(text, this)
      
      if (result.success) {
        // 显示执行结果
        wx.showToast({
          title: result.message,
          icon: 'success',
          duration: 2000
        })
        
        // 触发命令执行事件
        this.triggerEvent('command', {
          text,
          action: result.action,
          message: result.message,
          navigateTo: result.navigateTo
        })
        
        // 如果有跳转页面
        if (result.navigateTo) {
          setTimeout(() => {
            wx.navigateTo({
              url: result.navigateTo,
              fail: () => {
                wx.switchTab({ url: result.navigateTo })
              }
            })
          }, 500)
        }
        
        // 语音播报结果
        speechService.speak(result.message)
      } else {
        wx.showToast({
          title: result.message || '未识别的命令',
          icon: 'none'
        })
      }
    },

    // 取消
    cancel() {
      if (this.data.isRecording) {
        speechService.stopRecording()
      }
      this.triggerEvent('cancel')
    },

    // 确认
    confirm() {
      const text = this.data.recognizedText
      if (text) {
        this.executeCommand(text)
      }
      this.triggerEvent('confirm', { text })
    },

    // 显示帮助
    showHelp() {
      wx.showModal({
        title: '语音命令帮助',
        content: '可用命令：\n• 开始配送\n• 到达发货地\n• 确认取货\n• 导航到收货地\n• 完成配送\n• 查看订单\n• 查看今日任务\n• 查看收入\n• 上报异常\n• 联系客服',
        showCancel: false
      })
    }
  }
})