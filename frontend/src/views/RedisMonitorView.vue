<template>
  <div class="redis-monitor">
    <!-- Redis 连接状态 -->
    <div class="status-bar">
      <div class="status-item">
        <span class="status-dot" :class="{ connected: redisConnected, disconnected: !redisConnected }"></span>
        <span class="status-text">Redis {{ redisConnected ? '已连接' : '未连接' }}</span>
      </div>
      <div v-if="redisInfo.connected" class="status-info">
        <el-tag size="small" type="info">版本 {{ redisInfo.version }}</el-tag>
        <el-tag size="small" type="warning">内存 {{ redisInfo.used_memory }}</el-tag>
        <el-tag size="small" type="success">{{ redisInfo.keyspace }} 个键</el-tag>
        <el-tag size="small">已处理 {{ redisInfo.total_commands_processed }} 命令</el-tag>
      </div>
      <el-button size="small" :icon="Refresh" @click="fetchAll" :loading="loading">
        刷新数据
      </el-button>
    </div>

    <!-- 订单实时统计 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon today-icon">
            <el-icon :size="28"><Calendar /></el-icon>
          </div>
          <el-statistic title="今日订单" :value="todayOrders" class="stat-number">
            <template #suffix>
              <span class="stat-suffix positive">单</span>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon total-icon">
            <el-icon :size="28"><Document /></el-icon>
          </div>
          <el-statistic title="总订单数" :value="totalOrders" class="stat-number">
            <template #suffix>
              <span class="stat-suffix">单</span>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon route-icon">
            <el-icon :size="28"><Connection /></el-icon>
          </div>
          <el-statistic title="活跃路线" :value="popularRoutes.length" class="stat-number">
            <template #suffix>
              <span class="stat-suffix">条</span>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon vehicle-icon">
            <el-icon :size="28"><Van /></el-icon>
          </div>
          <el-statistic title="在线车辆" :value="onlineVehicles" class="stat-number">
            <template #suffix>
              <span class="stat-suffix">辆</span>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 热门路线排行榜 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">🏆 热门路线排行榜</span>
              <el-tag size="small" effect="plain">实时更新</el-tag>
            </div>
          </template>
          <el-table
            :data="popularRoutes"
            stripe
            style="width: 100%"
            :header-cell-style="{ background: '#f5f7fa', color: '#606266' }"
            empty-text="暂无数据"
            max-height="400"
          >
            <el-table-column label="排名" width="70" align="center">
              <template #default="{ row, $index }">
                <span v-if="$index === 0" class="rank-badge gold">🥇</span>
                <span v-else-if="$index === 1" class="rank-badge silver">🥈</span>
                <span v-else-if="$index === 2" class="rank-badge bronze">🥉</span>
                <span v-else class="rank-badge normal">{{ $index + 1 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="route_id" label="路线ID" width="100" />
            <el-table-column prop="route_name" label="路线名称" min-width="200" show-overflow-tooltip />
            <el-table-column label="访问量" width="120" align="right">
              <template #default="{ row }">
                <span class="access-count">{{ row.score.toLocaleString() }}</span>
              </template>
            </el-table-column>
            <el-table-column label="热度" width="120">
              <template #default="{ row }">
                <el-progress
                  :percentage="getHeatPercent(row.score)"
                  :stroke-width="8"
                  :color="getHeatColor($index)"
                  :show-text="false"
                />
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="popularRoutes.length === 0" description="暂无热门路线数据" :image-size="80" />
        </el-card>
      </el-col>

      <!-- 实时车辆状态面板 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">🚛 实时车辆状态</span>
              <div class="vehicle-legend">
                <span class="legend-item"><span class="legend-dot online"></span>配送中</span>
                <span class="legend-item"><span class="legend-dot idle"></span>空闲</span>
                <span class="legend-item"><span class="legend-dot offline"></span>离线</span>
              </div>
            </div>
          </template>
          <div class="vehicle-grid">
            <div
              v-for="vehicle in vehicleStatuses"
              :key="vehicle.vehicle_id"
              class="vehicle-card"
              :class="getVehicleClass(vehicle)"
            >
              <div class="vehicle-header">
                <el-icon :size="20"><Van /></el-icon>
                <span class="vehicle-id">车辆 #{{ vehicle.vehicle_id }}</span>
              </div>
              <div class="vehicle-status">
                <el-tag :type="getVehicleTagType(vehicle)" size="small" effect="dark">
                  {{ getVehicleStatusLabel(vehicle) }}
                </el-tag>
              </div>
              <div v-if="vehicle.current_order" class="vehicle-order">
                <el-icon :size="12"><Box /></el-icon>
                订单: {{ vehicle.current_order }}
              </div>
              <div v-if="vehicle.location" class="vehicle-location">
                <el-icon :size="12"><Location /></el-icon>
                {{ vehicle.location }}
              </div>
            </div>
          </div>
          <el-empty v-if="vehicleStatuses.length === 0" description="暂无车辆状态数据" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索历史 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span class="header-title">🔍 搜索历史</span>
              <el-button size="small" text type="danger" @click="searchHistory = []">
                清空
              </el-button>
            </div>
          </template>
          <div class="search-history-list">
            <el-tag
              v-for="(query, index) in searchHistory"
              :key="index"
              class="search-tag"
              closable
              @close="searchHistory.splice(index, 1)"
              effect="plain"
            >
              {{ query }}
            </el-tag>
          </div>
          <el-empty v-if="searchHistory.length === 0" description="暂无搜索记录" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { Refresh, Calendar, Document, Connection, Van, Box, Location } from '@element-plus/icons-vue'
import { getRedisStatus, getPopularRoutes, getOrderCount, getSearchHistory } from '@/api/redis'
import { ElMessage } from 'element-plus'

// 状态
const loading = ref(false)
const redisConnected = ref(false)
const redisInfo = ref({})
const popularRoutes = ref([])
const vehicleStatuses = ref([])
const searchHistory = ref([])
const todayOrders = ref(0)
const totalOrders = ref(0)
let refreshTimer = null

// 在线车辆数
const onlineVehicles = computed(() => {
  return vehicleStatuses.value.filter(v => {
    const status = (v.status || '').toLowerCase()
    return status === '配送中' || status === 'delivering' || status === 'online' || status === 'active'
  }).length
})

// 热度百分比
const maxScore = computed(() => {
  if (popularRoutes.value.length === 0) return 1
  return Math.max(...popularRoutes.value.map(r => r.score))
})

function getHeatPercent(score) {
  return maxScore.value > 0 ? Math.round((score / maxScore.value) * 100) : 0
}

function getHeatColor(index) {
  if (index === 0) return '#f56c6c'
  if (index === 1) return '#e6a23c'
  if (index === 2) return '#409eff'
  return '#67c23a'
}

// 车辆状态样式
function getVehicleClass(vehicle) {
  const status = (vehicle.status || '').toLowerCase()
  if (['配送中', 'delivering', 'active', 'online'].includes(status)) return 'vehicle-delivering'
  if (['空闲', 'idle', 'available'].includes(status)) return 'vehicle-idle'
  return 'vehicle-offline'
}

function getVehicleTagType(vehicle) {
  const status = (vehicle.status || '').toLowerCase()
  if (['配送中', 'delivering', 'active', 'online'].includes(status)) return 'success'
  if (['空闲', 'idle', 'available'].includes(status)) return 'warning'
  return 'info'
}

function getVehicleStatusLabel(vehicle) {
  const status = vehicle.status || '未知'
  return status
}

// 获取 Redis 状态
async function fetchRedisStatus() {
  try {
    const res = await getRedisStatus()
    if (res.success) {
      redisInfo.value = res.data
      redisConnected.value = res.data.connected
    }
  } catch (err) {
    redisConnected.value = false
    console.warn('Redis 未连接:', err)
  }
}

// 获取热门路线
async function fetchPopularRoutes() {
  try {
    const res = await getPopularRoutes(10)
    if (res.success) {
      popularRoutes.value = res.data || []
    }
  } catch (err) {
    console.warn('获取热门路线失败:', err)
  }
}

// 获取订单计数
async function fetchOrderCounts() {
  try {
    const today = new Date().toISOString().split('T')[0]
    const [todayRes, totalRes] = await Promise.all([
      getOrderCount('total', today),
      getOrderCount('total', 'total')
    ])
    if (todayRes.success) todayOrders.value = todayRes.data.count
    if (totalRes.success) totalOrders.value = totalRes.data.count
  } catch (err) {
    console.warn('获取订单计数失败:', err)
  }
}

// 获取搜索历史
async function fetchSearchHistory() {
  try {
    const res = await getSearchHistory(1, 20)
    if (res.success) {
      searchHistory.value = res.data || []
    }
  } catch (err) {
    console.warn('获取搜索历史失败:', err)
  }
}

// 全部刷新
async function fetchAll() {
  loading.value = true
  try {
    // 串行请求避免触发限流
    await fetchRedisStatus()
    await fetchPopularRoutes()
    await fetchOrderCounts()
    await fetchSearchHistory()
  } catch (e) {
    console.log('部分请求失败，稍后重试')
  }
  loading.value = false
}

onMounted(() => {
  fetchAll()
  refreshTimer = setInterval(fetchAll, 60000) // 改为60秒刷新
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<style scoped>
.redis-monitor {
  padding: 4px;
}

/* 状态栏 */
.status-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 20px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 12px;
  margin-bottom: 16px;
  color: #fff;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.status-dot.connected {
  background: #67c23a;
  box-shadow: 0 0 8px #67c23a;
  animation: pulse 2s infinite;
}

.status-dot.disconnected {
  background: #f56c6c;
  box-shadow: 0 0 8px #f56c6c;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-size: 14px;
  font-weight: 500;
}

.status-info {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  flex: 1;
}

/* 统计卡片行 */
.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  border-radius: 12px;
  border: none;
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
}

.stat-card:nth-child(1)::before { background: linear-gradient(90deg, #409eff, #67c23a); }
.stat-card:nth-child(2)::before { background: linear-gradient(90deg, #e6a23c, #f56c6c); }
.stat-card:nth-child(3)::before { background: linear-gradient(90deg, #9b59b6, #3498db); }
.stat-card:nth-child(4)::before { background: linear-gradient(90deg, #1abc9c, #2ecc71); }

.stat-icon {
  position: absolute;
  top: 12px;
  right: 16px;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.today-icon { background: linear-gradient(135deg, #409eff, #67c23a); }
.total-icon { background: linear-gradient(135deg, #e6a23c, #f56c6c); }
.route-icon { background: linear-gradient(135deg, #9b59b6, #3498db); }
.vehicle-icon { background: linear-gradient(135deg, #1abc9c, #2ecc71); }

.stat-number {
  text-align: center;
}

.stat-suffix {
  font-size: 12px;
  color: #909399;
}

.stat-suffix.positive {
  color: #67c23a;
}

/* 区块卡片 */
.section-card {
  border-radius: 12px;
  border: none;
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 排名 */
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 14px;
}

.rank-badge.gold { font-size: 20px; }
.rank-badge.silver { font-size: 18px; }
.rank-badge.bronze { font-size: 16px; }
.rank-badge.normal {
  background: #f0f2f5;
  color: #909399;
  font-size: 13px;
  font-weight: 500;
}

.access-count {
  font-weight: 600;
  color: #409eff;
  font-size: 14px;
}

/* 车辆状态网格 */
.vehicle-legend {
  display: flex;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #909399;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.legend-dot.online { background: #67c23a; }
.legend-dot.idle { background: #e6a23c; }
.legend-dot.offline { background: #909399; }

.vehicle-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.vehicle-card {
  padding: 14px;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  transition: all 0.3s;
  background: #fff;
}

.vehicle-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.vehicle-card.vehicle-delivering {
  border-left: 4px solid #67c23a;
  background: linear-gradient(135deg, #f0f9eb 0%, #fff 100%);
}

.vehicle-card.vehicle-idle {
  border-left: 4px solid #e6a23c;
  background: linear-gradient(135deg, #fdf6ec 0%, #fff 100%);
}

.vehicle-card.vehicle-offline {
  border-left: 4px solid #909399;
  background: linear-gradient(135deg, #f4f4f5 0%, #fff 100%);
  opacity: 0.7;
}

.vehicle-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.vehicle-id {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.vehicle-status {
  margin-bottom: 6px;
}

.vehicle-order, .vehicle-location {
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}

/* 搜索历史 */
.search-history-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.search-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.search-tag:hover {
  transform: scale(1.05);
}

/* 响应式 */
@media (max-width: 768px) {
  .status-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .status-info {
    font-size: 11px;
  }

  .stats-row .el-col {
    margin-bottom: 12px;
  }

  .stat-icon {
    width: 36px;
    height: 36px;
  }

  .stat-icon .el-icon {
    font-size: 20px !important;
  }

  .vehicle-grid {
    grid-template-columns: 1fr;
  }
}
</style>
