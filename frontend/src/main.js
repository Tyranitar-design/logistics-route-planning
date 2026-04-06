import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import i18n from './locales'

import './assets/main.css'
import './assets/mobile.css' // 移动端响应式样式

// 初始化 WebSocket 服务
import { wsService } from './services/websocket'
wsService.connect('http://localhost:5000')
window.socketInstance = wsService.socket
window.wsService = wsService

// 过滤 Element Plus DropdownManager 调试日志
const originalLog = console.log
console.log = (...args) => {
  const message = args.join(' ')
  if (message.includes('[DropdownManager]')) {
    return // 忽略 DropdownManager 的日志
  }
  originalLog.apply(console, args)
}

const app = createApp(App)

// 注册Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')
