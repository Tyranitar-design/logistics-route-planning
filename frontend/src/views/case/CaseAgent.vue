<template>
  <div class="case-page">
    <header class="page-hero">
      <h1>🤖 食品供应链专家 Agent</h1>
      <p>MiniMax-M3 · 只读解释 · 不会写入业务状态</p>
    </header>
    <section class="panel">
      <div class="agent-form">
        <el-select v-model="role" size="small" style="width:220px">
          <el-option v-for="r in roles" :key="r" :label="r" :value="r" />
        </el-select>
        <el-input v-model="question" type="textarea" :rows="3" placeholder="请输入问题…" />
        <el-button type="primary" :loading="loading" @click="ask">获取建议</el-button>
      </div>
      <div v-if="answer" class="agent-answer">
        <div class="answer-meta">真实性 {{ answer.authenticity_level || '-' }} · {{ answer.provider_status || '-' }}</div>
        <div class="answer-text">{{ answer.answer || JSON.stringify(answer) }}</div>
      </div>
      <div v-else-if="error" class="agent-error">{{ error }}</div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { explainFoodSupplyCase } from '@/api/foodSupplyCase'

const role = ref('食品供应链优化专家')
const roles = ['食品供应链优化专家', '鲜度与冷链专家', '仓网选址专家', '调度算法专家']
const question = ref('请基于当前案例（5 果园、3 仓库、46 门店、C 端 22259 地址、B747-8F、无人机）给出调度、仓网和鲜度风险建议。')
const answer = ref(null)
const error = ref('')
const loading = ref(false)

async function ask() {
  loading.value = true; error.value = ''; answer.value = null
  try {
    answer.value = await explainFoodSupplyCase({ question: question.value, agent_role: role.value })
  } catch (e) { error.value = 'Agent 调用失败：' + (e.message || '后端未启动或 MINIMAX_API_KEY 未配') }
  finally { loading.value = false }
}
onMounted(ask)
</script>

<style scoped>
.case-page { color: #e6f0ff; max-width: 920px; }
.page-hero { margin-bottom: 18px; }
.page-hero h1 { margin: 0 0 4px; font-size: 22px; color: #a8d8ff; }
.page-hero p { margin: 0; color: #7a8fb0; font-size: 13px; }
.panel { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 16px; }
.agent-form { display: flex; flex-direction: column; gap: 10px; margin-bottom: 18px; }
.agent-answer { background: rgba(7,17,31,0.6); border: 1px solid rgba(94,234,212,0.2); border-radius: 8px; padding: 14px; }
.answer-meta { font-size: 11px; color: #5eead4; margin-bottom: 8px; }
.answer-text { color: #d6e6ff; font-size: 14px; line-height: 1.8; white-space: pre-wrap; }
.agent-error { color: #ff9966; font-size: 13px; padding: 12px; background: rgba(255,100,50,0.06); border-radius: 6px; }
</style>
