<!-- components/AiChat.vue - 智能客服组件 -->
<template>
  <div class="ai-chat-container">
    <!-- 悬浮按钮 -->
    <div class="chat-float-btn" @click="toggleChat" v-if="!isOpen">
      <el-badge :value="unreadCount" :hidden="unreadCount === 0">
        <el-icon :size="28"><ChatDotRound /></el-icon>
      </el-badge>
    </div>
    
    <!-- 聊天窗口 -->
    <transition name="slide-up">
      <div class="chat-window" v-if="isOpen">
        <!-- 头部 -->
        <div class="chat-header">
          <div class="header-info">
            <div class="avatar">🤖</div>
            <div class="title">
              <div class="name">智能客服</div>
              <div class="status">在线</div>
            </div>
          </div>
          <div class="header-actions">
            <el-button text @click="clearHistory" title="清空对话">
              <el-icon><Delete /></el-icon>
            </el-button>
            <el-button text @click="toggleChat" title="关闭">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
        </div>
        
        <!-- 消息列表 -->
        <div class="chat-messages" ref="messagesContainer">
          <div 
            v-for="(msg, index) in messages" 
            :key="index"
            :class="['message', msg.type]"
          >
            <div class="message-avatar">
              {{ msg.type === 'bot' ? '🤖' : '👤' }}
            </div>
            <div class="message-content">
              <div class="message-text" v-html="formatMessage(msg.content)"></div>
              <div class="message-time">{{ msg.time }}</div>
            </div>
          </div>
          
          <!-- 正在输入 -->
          <div class="message bot" v-if="isTyping">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
              <div class="typing-indicator">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 快捷问题 -->
        <div class="quick-questions" v-if="messages.length <= 1">
          <div class="quick-title">快捷问题</div>
          <div class="quick-list">
            <div 
              v-for="q in quickQuestions" 
              :key="q"
              class="quick-item"
              @click="sendQuickQuestion(q)"
            >
              {{ q }}
            </div>
          </div>
        </div>
        
        <!-- 输入区域 -->
        <div class="chat-input">
          <el-input
            v-model="inputMessage"
            placeholder="输入您的问题..."
            @keyup.enter="sendMessage"
            :disabled="isTyping"
          >
            <template #append>
              <el-button 
                type="primary" 
                @click="sendMessage"
                :loading="isTyping"
              >
                发送
              </el-button>
            </template>
          </el-input>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { ChatDotRound, Delete, Close } from '@element-plus/icons-vue'
import axios from 'axios'

// 状态
const isOpen = ref(false)
const isTyping = ref(false)
const inputMessage = ref('')
const messages = ref([])
const unreadCount = ref(0)
const messagesContainer = ref(null)

// 快捷问题
const quickQuestions = [
  '如何查看订单？',
  '如何优化路线？',
  '成本分析怎么用？',
  '系统功能介绍'
]

// 初始化欢迎消息
onMounted(() => {
  addBotMessage('您好！我是智能客服小彩，有什么可以帮您的吗？😊')
})

// 切换聊天窗口
const toggleChat = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    unreadCount.value = 0
    scrollToBottom()
  }
}

// 发送消息
const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || isTyping.value) return
  
  // 添加用户消息
  addUserMessage(text)
  inputMessage.value = ''
  
  // 显示输入中
  isTyping.value = true
  
  try {
    // 调用后端 API 或本地知识库
    const response = await getBotResponse(text)
    
    // 模拟延迟
    await new Promise(resolve => setTimeout(resolve, 500))
    
    // 添加机器人回复
    addBotMessage(response)
  } catch (error) {
    addBotMessage('抱歉，我暂时无法回答这个问题。请稍后再试或联系管理员。')
  } finally {
    isTyping.value = false
    scrollToBottom()
  }
}

// 发送快捷问题
const sendQuickQuestion = (question) => {
  inputMessage.value = question
  sendMessage()
}

// 获取机器人回复
const getBotResponse = async (question) => {
  // 本地知识库（可扩展）
  const knowledgeBase = {
    '订单': '您可以在左侧菜单点击「订单管理」查看所有订单。订单支持创建、编辑、删除和导出功能。',
    '路线': '路线管理功能可以帮您规划最优配送路线。支持多目标优化、实时路况规避等功能。',
    '成本': '成本分析页面提供详细的运输成本统计，包括燃油费、路桥费、人工费等，支持按时间段筛选和导出报表。',
    '调度': '智能调度使用遗传算法优化配送方案，可以自动分配订单给最合适的车辆和司机。',
    '预测': 'ML预测功能使用机器学习算法预测未来订单需求，帮助您提前做好运力规划。',
    '预警': '预警中心实时监控订单、车辆、路线状态，发现异常自动推送提醒。',
    '功能': '本系统包含：订单管理、路线规划、智能调度、成本分析、数据分析、ML预测、预警中心、风险管理等28项核心功能。',
    '帮助': '您可以点击左下角悬浮按钮随时联系我，或者发送邮件至 support@example.com 获取技术支持。'
  }
  
  // 匹配关键词
  for (const [keyword, answer] of Object.entries(knowledgeBase)) {
    if (question.includes(keyword)) {
      return answer
    }
  }
  
  // 调用后端 AI API（如果配置了）
  try {
    const res = await axios.post('/api/chat', { message: question })
    if (res.data.code === 200 && res.data.data) {
      return res.data.data.response
    }
  } catch (e) {
    // 后端 API 不可用，使用默认回复
  }
  
  // 默认回复
  return '感谢您的提问！关于"' + question + '"，建议您：\n\n1. 查看系统帮助文档\n2. 联系管理员获取支持\n\n您也可以尝试换个方式描述您的问题。'
}

// 添加用户消息
const addUserMessage = (content) => {
  messages.value.push({
    type: 'user',
    content,
    time: formatTime(new Date())
  })
  scrollToBottom()
  
  // 如果窗口关闭，增加未读计数
  if (!isOpen.value) {
    unreadCount.value++
  }
}

// 添加机器人消息
const addBotMessage = (content) => {
  messages.value.push({
    type: 'bot',
    content,
    time: formatTime(new Date())
  })
  scrollToBottom()
}

// 清空历史
const clearHistory = () => {
  messages.value = []
  addBotMessage('对话已清空，有什么新问题吗？😊')
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 格式化消息（支持换行）
const formatMessage = (text) => {
  return text.replace(/\n/g, '<br>')
}

// 格式化时间
const formatTime = (date) => {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.ai-chat-container {
  position: fixed;
  z-index: 9999;
}

/* 悬浮按钮 */
.chat-float-btn {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #409EFF, #66b1ff);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.4);
  transition: all 0.3s;
}

.chat-float-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.5);
}

/* 聊天窗口 */
.chat-window {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 380px;
  height: 520px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 头部 */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: linear-gradient(135deg, #409EFF, #66b1ff);
  color: white;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  font-size: 28px;
}

.title .name {
  font-size: 16px;
  font-weight: 600;
}

.title .status {
  font-size: 12px;
  opacity: 0.9;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.header-actions .el-button {
  color: white;
}

/* 消息列表 */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f5f7fa;
}

.message {
  display: flex;
  margin-bottom: 16px;
  gap: 10px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  font-size: 24px;
  flex-shrink: 0;
}

.message-content {
  max-width: 70%;
}

.message-text {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
}

.message.bot .message-text {
  background: white;
  color: #303133;
  border-bottom-left-radius: 4px;
}

.message.user .message-text {
  background: #409EFF;
  color: white;
  border-bottom-right-radius: 4px;
}

.message-time {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}

.message.user .message-time {
  text-align: right;
}

/* 输入中动画 */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: white;
  border-radius: 12px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #409EFF;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-8px); }
}

/* 快捷问题 */
.quick-questions {
  padding: 12px 16px;
  background: white;
  border-top: 1px solid #ebeef5;
}

.quick-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.quick-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-item {
  padding: 6px 12px;
  background: #f5f7fa;
  border-radius: 16px;
  font-size: 12px;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-item:hover {
  background: #409EFF;
  color: white;
}

/* 输入区域 */
.chat-input {
  padding: 12px 16px;
  background: white;
  border-top: 1px solid #ebeef5;
}

.chat-input .el-input {
  --el-input-border-radius: 20px;
}

/* 动画 */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .chat-window {
    right: 0;
    bottom: 0;
    width: 100%;
    height: 100%;
    border-radius: 0;
  }
  
  .chat-float-btn {
    right: 16px;
    bottom: 16px;
  }
}
</style>