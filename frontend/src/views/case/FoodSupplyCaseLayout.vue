<template>
  <div class="case-layout">
    <aside class="case-sidebar">
      <div class="case-brand">
        <span class="cc-kicker">Case Study</span>
        <h2>食品供应链仓配</h2>
        <p>桃类生鲜 · 6-8 月旺季</p>
      </div>
      <nav class="case-nav">
        <router-link v-for="item in nav" :key="item.path" :to="item.path" class="case-nav-item" active-class="active">
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>
      <div class="case-sidebar-footer">
        <a href="http://127.0.0.1:5000/api/cases/food-supply/summary" target="_blank" class="api-link">API →</a>
      </div>
    </aside>
    <main class="case-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
const nav = [
  { path: '/cases/food-supply', label: '案例总览', icon: '📊' },
  { path: '/cases/food-supply/gis', label: 'GIS 地图', icon: '🗺️' },
  { path: '/cases/food-supply/forecast', label: '时序预测', icon: '📈' },
  { path: '/cases/food-supply/dispatch', label: '智能调度', icon: '🚚' },
  { path: '/cases/food-supply/multimodal', label: '多式联运', icon: '✈️' },
  { path: '/cases/food-supply/c2c', label: 'C端 & 无人机', icon: '🚁' },
  { path: '/cases/food-supply/clustering', label: '聚类分析', icon: '🔬' },
  { path: '/cases/food-supply/trace', label: '可追溯', icon: '📦' },
  { path: '/cases/food-supply/scenarios', label: '场景对比', icon: '🏆' },
  { path: '/cases/food-supply/business', label: '业务范畴', icon: '📊' },
  { path: '/cases/food-supply/agent', label: '专家 Agent', icon: '🤖' },
]
</script>

<style scoped>
.case-layout { display: flex; min-height: calc(100vh - 60px); background: #07111f; color: #e6f0ff; }
.case-sidebar { width: 220px; background: rgba(13,25,42,0.85); backdrop-filter: blur(18px); border-right: 1px solid rgba(120,200,255,0.12); padding: 18px 14px; display: flex; flex-direction: column; }
.case-brand { padding-bottom: 14px; border-bottom: 1px solid rgba(120,200,255,0.12); margin-bottom: 12px; }
.case-brand .cc-kicker { font-size: 11px; color: #5eead4; letter-spacing: 2px; text-transform: uppercase; }
.case-brand h2 { margin: 4px 0 2px; font-size: 17px; color: #a8d8ff; }
.case-brand p { margin: 0; font-size: 11px; color: #7a8fb0; }
.case-nav { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.case-nav-item { display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: 8px; color: #9bb3d4; text-decoration: none; font-size: 13px; transition: all 0.2s; }
.case-nav-item:hover { background: rgba(120,200,255,0.06); color: #cfe5ff; }
.case-nav-item.active { background: linear-gradient(90deg, rgba(94,234,212,0.18), transparent); color: #5eead4; box-shadow: inset 2px 0 0 #5eead4; }
.nav-icon { font-size: 15px; }
.case-sidebar-footer { padding-top: 12px; border-top: 1px solid rgba(120,200,255,0.12); }
.api-link { font-size: 11px; color: #7a8fb0; text-decoration: none; }
.case-main { flex: 1; padding: 20px 28px; overflow-y: auto; }
</style>
