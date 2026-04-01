<template>
  <div class="test-data-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>测试数据生成</h2>
      <p class="subtitle">一键生成模拟数据，快速体验系统功能</p>
    </div>

    <!-- 当前数据统计 -->
    <el-card class="status-card">
      <template #header>
        <div class="card-header">
          <span>当前数据统计</span>
          <el-button type="primary" size="small" @click="loadStatus">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <el-row :gutter="20">
        <el-col :xs="12" :sm="6">
          <div class="stat-item">
            <div class="stat-icon nodes">
              <el-icon><Location /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ status.nodes || 0 }}</div>
              <div class="stat-label">节点</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="stat-item">
            <div class="stat-icon vehicles">
              <el-icon><Van /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ status.vehicles || 0 }}</div>
              <div class="stat-label">车辆</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="stat-item">
            <div class="stat-icon orders">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ status.orders || 0 }}</div>
              <div class="stat-label">订单</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="stat-item">
            <div class="stat-icon delivered">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ status.orders_by_status?.delivered || 0 }}</div>
              <div class="stat-label">已交付</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 数据生成 -->
    <el-card class="generate-card">
      <template #header>
        <span>生成测试数据</span>
      </template>

      <el-form :model="generateForm" label-width="100px">
        <el-row :gutter="20">
          <el-col :xs="24" :sm="8">
            <el-form-item label="节点数量">
              <el-input-number v-model="generateForm.nodes_count" :min="0" :max="100" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="车辆数量">
              <el-input-number v-model="generateForm.vehicles_count" :min="0" :max="50" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-form-item label="订单数量">
              <el-input-number v-model="generateForm.orders_count" :min="0" :max="200" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="清除现有">
          <el-switch v-model="generateForm.clear_existing" />
          <span class="switch-tip">开启后会删除现有数据再生成</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="generateAll" :loading="generating">
            <el-icon><MagicStick /></el-icon>
            一键生成全部数据
          </el-button>
          <el-button @click="generateNodes" :loading="generatingNodes">只生成节点</el-button>
          <el-button @click="generateVehicles" :loading="generatingVehicles">只生成车辆</el-button>
          <el-button @click="generateOrders" :loading="generatingOrders">只生成订单</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 订单状态分布 -->
    <el-card class="chart-card">
      <template #header>
        <span>订单状态分布</span>
      </template>
      
      <el-row :gutter="20">
        <el-col :xs="12" :sm="6">
          <div class="status-block pending">
            <div class="status-count">{{ status.orders_by_status?.pending || 0 }}</div>
            <div class="status-label">待处理</div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="status-block transit">
            <div class="status-count">{{ status.orders_by_status?.in_transit || 0 }}</div>
            <div class="status-label">运输中</div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="status-block delivered">
            <div class="status-count">{{ status.orders_by_status?.delivered || 0 }}</div>
            <div class="status-label">已交付</div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="status-block cancelled">
            <div class="status-count">{{ status.orders_by_status?.cancelled || 0 }}</div>
            <div class="status-label">已取消</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 车辆状态分布 -->
    <el-card class="chart-card">
      <template #header>
        <span>车辆状态分布</span>
      </template>
      
      <el-row :gutter="20">
        <el-col :xs="12" :sm="6">
          <div class="status-block available">
            <div class="status-count">{{ status.vehicles_by_status?.available || 0 }}</div>
            <div class="status-label">可用</div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="status-block in-use">
            <div class="status-count">{{ status.vehicles_by_status?.in_use || 0 }}</div>
            <div class="status-label">使用中</div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="status-block maintenance">
            <div class="status-count">{{ status.vehicles_by_status?.maintenance || 0 }}</div>
            <div class="status-label">维护中</div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="status-block offline">
            <div class="status-count">{{ status.vehicles_by_status?.offline || 0 }}</div>
            <div class="status-label">离线</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Location, Van, Document, CircleCheck, MagicStick } from '@element-plus/icons-vue'
import request from '../api/request'

// 数据
const status = ref({})
const generating = ref(false)
const generatingNodes = ref(false)
const generatingVehicles = ref(false)
const generatingOrders = ref(false)

const generateForm = reactive({
  nodes_count: 20,
  vehicles_count: 15,
  orders_count: 50,
  clear_existing: false
})

// 加载状态
const loadStatus = async () => {
  try {
    const res = await request.get('/test-data/status')
    status.value = res || {}
  } catch (error) {
    console.error('加载状态失败:', error)
  }
}

// 生成全部数据
const generateAll = async () => {
  generating.value = true
  try {
    const res = await request.post('/test-data/generate', generateForm)
    if (res.success) {
      ElMessage.success(res.message || '生成成功')
      loadStatus()
    } else {
      ElMessage.error(res.error || '生成失败')
    }
  } catch (error) {
    ElMessage.error('生成失败: ' + (error.message || error))
  } finally {
    generating.value = false
  }
}

// 只生成节点
const generateNodes = async () => {
  generatingNodes.value = true
  try {
    const res = await request.post('/test-data/generate/nodes', {
      count: generateForm.nodes_count,
      clear_existing: generateForm.clear_existing
    })
    if (res.success) {
      ElMessage.success(`成功生成 ${res.count} 个节点`)
      loadStatus()
    } else {
      ElMessage.error(res.error || '生成失败')
    }
  } catch (error) {
    ElMessage.error('生成失败: ' + (error.message || error))
  } finally {
    generatingNodes.value = false
  }
}

// 只生成车辆
const generateVehicles = async () => {
  generatingVehicles.value = true
  try {
    const res = await request.post('/test-data/generate/vehicles', {
      count: generateForm.vehicles_count,
      clear_existing: generateForm.clear_existing
    })
    if (res.success) {
      ElMessage.success(`成功生成 ${res.count} 辆车辆`)
      loadStatus()
    } else {
      ElMessage.error(res.error || '生成失败')
    }
  } catch (error) {
    ElMessage.error('生成失败: ' + (error.message || error))
  } finally {
    generatingVehicles.value = false
  }
}

// 只生成订单
const generateOrders = async () => {
  generatingOrders.value = true
  try {
    const res = await request.post('/test-data/generate/orders', {
      count: generateForm.orders_count,
      clear_existing: generateForm.clear_existing
    })
    if (res.success) {
      ElMessage.success(`成功生成 ${res.count} 个订单`)
      loadStatus()
    } else {
      ElMessage.error(res.error || '生成失败')
    }
  } catch (error) {
    ElMessage.error('生成失败: ' + (error.message || error))
  } finally {
    generatingOrders.value = false
  }
}

onMounted(() => {
  loadStatus()
})
</script>

<style scoped>
.test-data-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 8px 0;
  color: #303133;
}

.subtitle {
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-card, .generate-card, .chart-card {
  margin-bottom: 20px;
}

.stat-item {
  display: flex;
  align-items: center;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
  font-size: 24px;
  color: white;
}

.stat-icon.nodes {
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.stat-icon.vehicles {
  background: linear-gradient(135deg, #f093fb, #f5576c);
}

.stat-icon.orders {
  background: linear-gradient(135deg, #4facfe, #00f2fe);
}

.stat-icon.delivered {
  background: linear-gradient(135deg, #43e97b, #38f9d7);
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  color: #909399;
  font-size: 14px;
}

.switch-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.status-block {
  text-align: center;
  padding: 20px;
  border-radius: 8px;
  color: white;
}

.status-block.pending {
  background: linear-gradient(135deg, #ffecd2, #fcb69f);
  color: #8b4513;
}

.status-block.transit {
  background: linear-gradient(135deg, #a1c4fd, #c2e9fb);
  color: #1e3a5f;
}

.status-block.delivered {
  background: linear-gradient(135deg, #d4fc79, #96e6a1);
  color: #2d5016;
}

.status-block.cancelled {
  background: linear-gradient(135deg, #ffecd2, #ffb88c);
  color: #8b4513;
}

.status-block.available {
  background: linear-gradient(135deg, #84fab0, #8fd3f4);
  color: #1a5f2a;
}

.status-block.in-use {
  background: linear-gradient(135deg, #a1c4fd, #c2e9fb);
  color: #1e3a5f;
}

.status-block.maintenance {
  background: linear-gradient(135deg, #ffecd2, #fcb69f);
  color: #8b4513;
}

.status-block.offline {
  background: linear-gradient(135deg, #e0e0e0, #bdbdbd);
  color: #424242;
}

.status-count {
  font-size: 32px;
  font-weight: bold;
}

.status-label {
  font-size: 14px;
  margin-top: 5px;
}

@media (max-width: 768px) {
  .stat-item {
    margin-bottom: 10px;
  }
  
  .status-block {
    margin-bottom: 10px;
  }
}
</style>