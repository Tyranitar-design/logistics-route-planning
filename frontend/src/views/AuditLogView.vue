<template>
  <div class="audit-log-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>审计日志分析</span>
          <div class="filters">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              @change="loadData"
            />
            <el-button type="primary" @click="refreshData">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <!-- 统计卡片 -->
      <div class="stat-cards">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card class="stat-card" shadow="hover">
              <div class="stat-content">
                <CountUp :end-value="stats.total" :duration="1500" />
                <div class="stat-label">总操作数</div>
              </div>
              <div class="stat-icon"><el-icon><Document /></el-icon></div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="stat-card" shadow="hover">
              <div class="stat-content">
                <CountUp :end-value="stats.create" :duration="1500" />
                <div class="stat-label">创建操作</div>
              </div>
              <div class="stat-icon" style="color: #67c23a;"><el-icon><Plus /></el-icon></div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="stat-card" shadow="hover">
              <div class="stat-content">
                <CountUp :end-value="stats.update" :duration="1500" />
                <div class="stat-label">更新操作</div>
              </div>
              <div class="stat-icon" style="color: #e6a23c;"><el-icon><Edit /></el-icon></div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="stat-card" shadow="hover">
              <div class="stat-content">
                <CountUp :end-value="stats.delete" :duration="1500" />
                <div class="stat-label">删除操作</div>
              </div>
              <div class="stat-icon" style="color: #f56c6c;"><el-icon><Delete /></el-icon></div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 图表区域 -->
      <el-row :gutter="20" style="margin-top: 20px;">
        <el-col :span="12">
          <el-card>
            <template #header>操作趋势</template>
            <div ref="trendChartRef" style="height: 300px;"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>操作类型分布</template>
            <div ref="pieChartRef" style="height: 300px;"></div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top: 20px;">
        <el-col :span="12">
          <el-card>
            <template #header>活跃用户 TOP 10</template>
            <div ref="userChartRef" style="height: 300px;"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header>模块操作分布</template>
            <div ref="moduleChartRef" style="height: 300px;"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 日志列表 -->
      <el-card style="margin-top: 20px;">
        <template #header>详细日志</template>
        <el-table :data="logs" v-loading="loading" style="width: 100%">
          <el-table-column prop="created_at" label="时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="action" label="操作" width="120">
            <template #default="{ row }">
              <el-tag :type="getActionTypeColor(row.action)">{{ row.action }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="module" label="模块" width="120" />
          <el-table-column prop="description" label="描述" />
          <el-table-column prop="user_name" label="操作用户" width="120" />
          <el-table-column prop="ip_address" label="IP地址" width="140" />
        </el-table>
      </el-card>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { Document, Plus, Edit, Delete, Refresh } from '@element-plus/icons-vue'
import CountUp from '@/components/CountUp.vue'
import { getAuditLogs } from '@/api/audit'

const dateRange = ref([])
const loading = ref(false)
const logs = ref([])
const stats = reactive({ total: 0, create: 0, update: 0, delete: 0 })

// 图表引用
const trendChartRef = ref(null)
const pieChartRef = ref(null)
const userChartRef = ref(null)
const moduleChartRef = ref(null)

// 图表实例
let trendChart = null
let pieChart = null
let userChart = null
let moduleChart = null

// 初始化日期范围（最近30天）
const initDateRange = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 30)
  dateRange.value = [start, end]
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 获取操作类型颜色
const getActionTypeColor = (action) => {
  const colors = {
    CREATE: 'success',
    UPDATE: 'warning',
    DELETE: 'danger',
    LOGIN: 'info',
    LOGOUT: 'info',
    VIEW: '',
    EXPORT: ''
  }
  return colors[action] || 'info'
}

// 加载数据
const loadData = async () => {
  if (!dateRange.value || !dateRange.value.length) return
  
  loading.value = true
  try {
    const [startDate, endDate] = dateRange.value
    const res = await getAuditLogs({
      start_date: startDate.toISOString().split('T')[0],
      end_date: endDate.toISOString().split('T')[0]
    })
    
    logs.value = res.logs || []
    Object.assign(stats, res.stats || { total: 0, create: 0, update: 0, delete: 0 })
    
    // 渲染图表
    await nextTick()
    renderCharts(res.charts)
    
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

// 刷新数据
const refreshData = () => {
  loadData()
}

// 销毁图表实例
const disposeCharts = () => {
  trendChart?.dispose()
  pieChart?.dispose()
  userChart?.dispose()
  moduleChart?.dispose()
  trendChart = null
  pieChart = null
  userChart = null
  moduleChart = null
}

// 渲染图表
const renderCharts = (chartData) => {
  // 先销毁旧实例
  disposeCharts()
  
  // 趋势图
  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['操作总数', '创建', '更新', '删除'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: chartData?.trend?.dates || [] },
      yAxis: { type: 'value' },
      series: [
        { name: '操作总数', type: 'line', smooth: true, data: chartData?.trend?.total || [] },
        { name: '创建', type: 'line', smooth: true, data: chartData?.trend?.create || [] },
        { name: '更新', type: 'line', smooth: true, data: chartData?.trend?.update || [] },
        { name: '删除', type: 'line', smooth: true, data: chartData?.trend?.delete || [] }
      ]
    })
  }
  
  // 饼图
  if (pieChartRef.value) {
    pieChart = echarts.init(pieChartRef.value)
    pieChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { orient: 'vertical', left: 'left' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: chartData?.action_types || [],
        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
      }]
    })
  }
  
  // 用户排行
  if (userChartRef.value) {
    userChart = echarts.init(userChartRef.value)
    const userData = chartData?.top_users || []
    userChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'value' },
      yAxis: { type: 'category', data: userData.map(u => u.name).reverse() },
      series: [{
        type: 'bar',
        data: userData.map(u => u.count).reverse(),
        itemStyle: { color: '#409eff' }
      }]
    })
  }
  
  // 模块分布
  if (moduleChartRef.value) {
    moduleChart = echarts.init(moduleChartRef.value)
    moduleChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      series: [{
        type: 'pie',
        radius: '60%',
        data: chartData?.modules || [],
        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
      }]
    })
  }
}

// 窗口大小变化时重绘图表
const handleResize = () => {
  trendChart?.resize()
  pieChart?.resize()
  userChart?.resize()
  moduleChart?.resize()
}

onMounted(() => {
  initDateRange()
  loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  disposeCharts()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
  gap: 16px;
  align-items: center;
}

.stat-cards {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.stat-content {
  flex: 1;
}

.stat-content :deep(.count-up) {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.stat-icon {
  font-size: 40px;
  color: #dcdfe6;
}
</style>
