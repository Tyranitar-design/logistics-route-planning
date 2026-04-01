import { createI18n } from 'vue-i18n'
import zhCN from './zh-CN'
import enUS from './en-US'

// 获取存储的语言或浏览器语言
function getDefaultLanguage() {
  const stored = localStorage.getItem('language')
  if (stored) return stored
  
  const browserLang = navigator.language.toLowerCase()
  return browserLang.startsWith('zh') ? 'zh-CN' : 'en-US'
}

const i18n = createI18n({
  legacy: false,
  locale: getDefaultLanguage(),
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS
  }
})

export default i18n

// 切换语言
export function setLanguage(lang) {
  i18n.global.locale.value = lang
  localStorage.setItem('language', lang)
  document.querySelector('html').setAttribute('lang', lang)
}
