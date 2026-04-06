<template>
  <div class="scheduler-page">
    <div class="scheduler-header">
      <h2>⏰ Airflow 任务调度中心</h2>
      <el-tag type="success" effect="dark">
        <el-icon><Connection /></el-icon>
        服务运行中
      </el-tag>
    </div>

    <!-- 快速入口卡片 -->
    <div class="quick-access">
      <el-card class="access-card" @click="openAirflow">
        <div class="access-icon">🎛️</div>
        <h3>Airflow 控制台</h3>
        <p>管理 DAG 任务、查看执行状态</p>
        <el-button type="primary">打开控制台</el-button>
      </el-card>
      
      <el-card class="access-card">
        <div class="access-icon">📋</div>
        <h3>任务列表</h3>
        <p>查看所有调度任务</p>
        <el-button @click="refreshTasks">刷新</el-button>
      </el-card>
      
      <el-card class="access-card">
        <div class="access-icon">📊</div>
        <h3>执行统计</h3>
        <p>任务成功率、执行时间</p>
        <el-button @click="openAirflow">查看统计</el-button>
      </el-card>
    </div>

    <!-- 任务说明 -->
    <el-card class="info-card">
      <template #header>
        <span>📌 关于 Airflow 任务调度</span>
      </template>
      <div class="info-content">
        <p><strong>Airflow</strong> 是一个开源的工作流管理平台，用于开发、调度和监控批处理工作流。</p>
        <el-divider />
        <h4>核心功能：</h4>
        <ul>
          <li>✅ DAG（有向无环图）任务编排</li>
          <li>✅ 定时调度（Cron 表达式）</li>
          <li>✅ 任务依赖管理</li>
          <li>✅ 执行日志追踪</li>
          <li>✅ 失败重试机制</li>
        </ul>
        <el-divider />
        <h4>登录信息：</h4>
        <p>用户名：<code>admin</code> 密码：<code>admin123</code></p>
      </div>
    </el-card>

    <!-- 常用任务 -->
    <el-card class="tasks-card">
      <template #header>
        <div class="tasks-header">
          <span>🔄 物流系统调度任务</span>
          <el-button size="small" type="primary" @click="openAirflow">管理任务</el-button>
        </div>
      </template>
      <el-table :data="sampleTasks" stripe>
        <el-table-column prop="name" label="任务名称" />
        <el-table-column prop="schedule" label="调度周期" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '运行中' : '已暂停' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_run" label="上次执行" width="160" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Connection } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const sampleTasks = ref([
  { name: 'logistics_daily_tasks', schedule: '每天 08:00', status: 'active', last_run: '待执行' },
  { name: 'logistics_vehicle_tracking', schedule: '每 5 分钟', status: 'active', last_run: '实时运行' },
  { name: 'logistics_weekly_cost_analysis', schedule: '每周一 09:00', status: 'active', last_run: '待执行' },
  { name: 'data_cleanup_monthly', schedule: '每月 1 号', status: 'paused', last_run: '已暂停' }
])

const openAirflow = () => {
  window.open('http://localhost:8085', '_blank')
}

const refreshTasks = () => {
  ElMessage.success('任务列表已刷新')
}
</script>

<style scoped>
.scheduler-page {
  max-width: 1000px;
  margin: 0 auto;
}

.scheduler-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.scheduler-header h2 {
  margin: 0;
  color: #00d4ff;
  font-size: 20px;
}

.quick-access {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.access-card {
  background: #1a1a2e;
  border: 1px solid rgba(0, 212, 255, 0.1);
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.access-card:hover {
  border-color: #00d4ff;
  transform: translateY(-2px);
}

.access-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.access-card h3 {
  margin: 0 0 8px;
  color: #fff;
}

.access-card p {
  margin: 0 0 16px;
  color: #888;
  font-size: 12px;
}

.info-card {
  background: #1a1a2e;
  border: 1px solid rgba(0, 212, 255, 0.1);
  margin-bottom: 24px;
}

.info-content {
  color: #a0a0a0;
  line-height: 1.8;
}

.info-content h4 {
  color: #00d4ff;
  margin: 12px 0 8px;
}

.info-content ul {
  padding-left: 20px;
}

.info-content li {
  margin-bottom: 4px;
}

.info-content code {
  background: rgba(0, 212, 255, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  color: #00d4ff;
}

.tasks-card {
  background: #1a1a2e;
  border: 1px solid rgba(0, 212, 255, 0.1);
}

.tasks-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
