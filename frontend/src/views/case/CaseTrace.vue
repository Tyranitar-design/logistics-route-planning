<template>
  <div class="case-page">
    <header class="page-hero">
      <h1>📦 可追溯链路</h1>
      <p>采摘 → 包装 → 运输 → 签收 · 确定性追溯码（码即数据）</p>
    </header>
    <section class="panel">
      <h2>签发追溯码</h2>
      <el-form :inline="true" class="trace-form">
        <el-form-item label="果园"><el-input v-model="form.orchard_code" /></el-form-item>
        <el-form-item label="波次日期"><el-input v-model="form.wave_date" placeholder="MM-DD" /></el-form-item>
        <el-form-item label="聚类"><el-input v-model="form.cluster_code" /></el-form-item>
        <el-button type="primary" :loading="loading" @click="issue">签发追溯码</el-button>
      </el-form>
    </section>
    <section v-if="result" class="panel">
      <div class="trace-code">追溯码：<strong>{{ result.trace_code }}</strong></div>
      <el-steps :space="220" :active="(result.stages?.length || 1) - 1" finish-status="success" class="trace-steps">
        <el-step v-for="(s, i) in result.stages || []" :key="i" :title="s.stage" :description="`${s.time} · ${s.location} · ${s.note}`" />
      </el-steps>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { issueFoodSupplyTrace } from '@/api/foodSupplyCase'

const form = ref({ orchard_code: 'ORCHARD-A', wave_date: '09-01', cluster_code: 'CC-HEFEI' })
const result = ref(null)
const loading = ref(false)

async function issue() {
  loading.value = true
  try {
    result.value = await issueFoodSupplyTrace({ ...form.value })
    ElMessage.success('追溯码已签发')
  } catch (e) { ElMessage.error('签发失败：' + (e.message || '后端未启动')) }
  finally { loading.value = false }
}
onMounted(issue)
</script>

<style scoped>
.case-page { color: #e6f0ff; }
.page-hero { margin-bottom: 18px; }
.page-hero h1 { margin: 0 0 4px; font-size: 22px; color: #a8d8ff; }
.page-hero p { margin: 0; color: #7a8fb0; font-size: 13px; }
.panel { background: rgba(13,25,42,0.7); border: 1px solid rgba(120,200,255,0.12); border-radius: 10px; padding: 16px; margin-bottom: 16px; }
.panel h2 { margin: 0 0 14px; font-size: 15px; color: #a8d8ff; }
.trace-form { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.trace-code { font-size: 16px; color: #5eead4; margin-bottom: 20px; }
.trace-code strong { font-family: monospace; color: #a8d8ff; font-size: 14px; word-break: break-all; }
.trace-steps { padding: 12px 0; }
</style>
