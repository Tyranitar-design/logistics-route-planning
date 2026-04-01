<template>
  <el-dropdown @command="handleCommand" trigger="click">
    <el-button text class="lang-switch">
      <el-icon><SwitchButton /></el-icon>
      {{ currentLangLabel }}
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="zh-CN" :disabled="currentLang === 'zh-CN'">
          🇨🇳 简体中文
        </el-dropdown-item>
        <el-dropdown-item command="en-US" :disabled="currentLang === 'en-US'">
          🇺🇸 English
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { SwitchButton } from '@element-plus/icons-vue'
import { setLanguage } from '@/locales'

const { locale } = useI18n()

const currentLang = computed(() => locale.value)

const currentLangLabel = computed(() => {
  return currentLang.value === 'zh-CN' ? '中文' : 'EN'
})

const handleCommand = (lang) => {
  setLanguage(lang)
}
</script>

<style scoped>
.lang-switch {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
}
</style>
