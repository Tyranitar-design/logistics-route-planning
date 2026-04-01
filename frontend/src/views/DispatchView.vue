<template>
  <div class="dispatch-view">
    <el-row :gutter="20">
      <!-- 左侧：订单选择 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>📦 待调度订单</span>
              <el-tag>{{ pendingOrders.length }} 单</el-tag>
            </div>
          </template>
          
          <!-- 筛选 -->
          <div class="filter-bar">
            <el-input
              v-model="orderSearch"
              placeholder="搜索订单号/客户"
              size="small"
              clearable
              style="width: 200px"
            />
            <el-select v-model="priorityFilter" placeholder="优先级" size="small" clearable style="width: 100px">
              <el-option label="全部" value="" />
              <el-option label="紧急" value="urgent" />
              <el-option label="加急" value="express" />
              <el-option label="普通" value="normal" />
            </el-select>
          </div>
          
          <!-- 订单列表 -->
          <div class="order-list">
            <!-- 快速选择下拉 -->
            <el-select
              v-model="selectedOrders"
              multiple
              filterable
              collapse-tags
              collapse-tags-tooltip
              placeholder="选择要调度的订单"
              style="width: 100%; margin-bottom: 10px"
            >
              <el-option
                v-for="order in filteredOrders"
                :key="order.id"
                :label="`${order.order_number} - ${order.customer_name} (${order.weight || 0}吨)`"
                :value="order.id"
              >
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span>{{ order.order_number }}</span>
                  <span style="color: #909399; font-size: 12px;">{{ order.customer_name }}</span>
                  <el-tag v-if="order.priority !== 'normal'" :type="getPriorityType(order.priority)" size="small">
                    {{ getPriorityText(order.priority) }}
                  </el-tag>
                </div>
              </el-option>
            </el-select>
            
            <!-- 详情列表（可选查看） -->
            <el-checkbox-group v-model="selectedOrders">
              <div
                v-for="order in filteredOrders"
                :key="order.id"
                class="order-item"
                :class="{ 'selected': selectedOrders.includes(order.id) }"
              >
                <el-checkbox :value="order.id">
                  <div class="order-info">
                    <div class="order-header">
                      <span class="order-number">{{ order.order_number }}</span>
                      <el-tag 
                        :type="getPriorityType(order.priority)" 
                        size="small"
                        v-if="order.priority !== 'normal'"
                      >
                        {{ getPriorityText(order.priority) }}
                      </el-tag>
                    </div>
                    <div class="order-detail">
                      <span>{{ order.customer_name }}</span>
                      <span>{{ order.weight || 0 }}吨</span>
                    </div>
                  </div>
                </el-checkbox>
              </div>
            </el-checkbox-group>
          </div>
          
          <div class="action-bar">
            <el-button size="small" @click="selectAllOrders">全选</el-button>
            <el-button size="small" @click="selectedOrders = []">清空</el-button>
          </div>
        </el-card>
        
        <!-- 合并建议 -->
        <el-card style="margin-top: 15px" v-if="mergeClusters.length > 0">
          <template #header>
            <span>🔗 合并配送建议</span>
          </template>
          <div v-for="(cluster, index) in mergeClusters" :key="index" class="merge-cluster">
            <div class="cluster-header">
              <el-tag type="success">可合并 {{ cluster.orders.length }} 单</el-tag>
              <el-button 
                size="small" 
                text 
                @click="applyMergeCluster(cluster)"
              >
                应用
              </el-button>
            </div>
            <div class="cluster-info">
              总重量: {{ cluster.total_weight?.toFixed(1) || 0 }}吨
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 中间：调度配置 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>⚙️ 调度配置</span>
          </template>
          
          <el-form :model="dispatchConfig" label-width="120px" size="small">
            <el-form-item label="调度算法">
              <el-radio-group v-model="dispatchConfig.algorithm">
                <el-radio-button 
                  v-for="algo in algorithms" 
                  :key="algo.id" 
                  :value="algo.id"
                >
                  {{ algo.name }}
                </el-radio-button>
              </el-radio-group>
              <div class="config-hint" style="margin-top: 5px">
                {{ algorithms.find(a => a.id === dispatchConfig.algorithm)?.description }}
              </div>
            </el-form-item>
            
            <el-divider content-position="left">多目标权重</el-divider>
            
            <el-form-item label="成本权重">
              <el-slider 
                v-model="dispatchConfig.weights.cost" 
                :min="0" 
                :max="1" 
                :step="0.1"
                show-input
                :show-input-controls="false"
              />
            </el-form-item>
            
            <el-form-item label="时间权重">
              <el-slider 
                v-model="dispatchConfig.weights.time" 
                :min="0" 
                :max="1" 
                :step="0.1"
                show-input
                :show-input-controls="false"
              />
            </el-form-item>
            
            <el-form-item label="满意度权重">
              <el-slider 
                v-model="dispatchConfig.weights.satisfaction" 
                :min="0" 
                :max="1" 
                :step="0.1"
                show-input
                :show-input-controls="false"
              />
            </el-form-item>
            
            <el-divider content-position="left">调度选项</el-divider>
            
            <el-form-item label="考虑天气">
              <el-switch v-model="dispatchConfig.consider_weather" />
              <span class="config-hint">根据天气调整运输时间</span>
            </el-form-item>
            
            <el-form-item label="考虑路况">
              <el-switch v-model="dispatchConfig.consider_traffic" />
              <span class="config-hint">避开拥堵路段</span>
            </el-form-item>
            
            <el-form-item label="每车最大订单">
              <el-input-number 
                v-model="dispatchConfig.max_orders_per_vehicle" 
                :min="1" 
                :max="10"
              />
            </el-form-item>
            
            <el-divider />
            
            <el-form-item label="选择车辆">
              <el-select 
                v-model="selectedVehicles" 
                multiple 
                placeholder="默认使用所有可用车辆"
                style="width: 100%"
              >
                <el-option
                  v-for="v in availableVehicles"
                  :key="v.id"
                  :label="`${v.plate_number} (${v.capacity_weight}吨)`"
                  :value="v.id"
                />
              </el-select>
            </el-form-item>
          </el-form>
          
          <div class="config-actions">
            <el-button type="primary" @click="handlePreview" :loading="previewLoading">
              👁️ 预览调度
            </el-button>
            <el-button type="success" @click="handleAutoDispatch" :loading="dispatchLoading">
              🚀 智能调度
            </el-button>
          </div>
        </el-card>
        
        <!-- 调度汇总 -->
        <el-card style="margin-top: 15px" v-if="dispatchSummary">
          <template #header>
            <span>📊 调度汇总</span>
          </template>
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="已分配订单">
              {{ dispatchSummary.total_orders_assigned }} 单
            </el-descriptions-item>
            <el-descriptions-item label="未分配订单">
              {{ dispatchSummary.total_orders_unassigned }} 单
            </el-descriptions-item>
            <el-descriptions-item label="使用车辆">
              {{ dispatchSummary.total_vehicles_used }} 辆
            </el-descriptions-item>
            <el-descriptions-item label="总里程">
              {{ dispatchSummary.total_distance_km }} 公里
            </el-descriptions-item>
            <el-descriptions-item label="总成本" :span="2">
              <span class="cost">{{ dispatchSummary.total_cost }} 元</span>
            </el-descriptions-item>
            <el-descriptions-item label="平均成本" :span="2">
              {{ dispatchSummary.average_cost_per_order }} 元/单
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      
      <!-- 右侧：调度结果 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>🚚 调度结果</span>
              <el-button 
                v-if="dispatchPlans.length > 0"
                type="success" 
                size="small"
                @click="handleApplyAll"
                :loading="applyLoading"
              >
                确认执行
              </el-button>
            </div>
          </template>
          
          <div v-if="dispatchPlans.length === 0" class="empty-state">
            <span class="empty-icon">📋</span>
            <p>点击「预览调度」查看结果</p>
          </div>
          
          <div v-else class="plan-list">
            <el-collapse v-model="activePlan">
              <el-collapse-item
                v-for="(plan, index) in dispatchPlans"
                :key="plan.vehicle_id"
                :name="index"
              >
                <template #title>
                  <div class="plan-title">
                    <span class="vehicle-name">{{ plan.vehicle_info?.plate_number }}</span>
                    <el-tag size="small">{{ plan.orders.length }} 单</el-tag>
                    <el-tag type="warning" size="small">{{ plan.total_cost }} 元</el-tag>
                  </div>
                </template>
                
                <div class="plan-detail">
                  <el-descriptions :column="2" size="small">
                    <el-descriptions-item label="总距离">
                      {{ plan.total_distance }} 公里
                    </el-descriptions-item>
                    <el-descriptions-item label="预计时长">
                      {{ plan.total_duration?.toFixed(1) }} 小时
                    </el-descriptions-item>
                    <el-descriptions-item label="载重">
                      {{ plan.vehicle_info?.capacity_weight }} 吨
                    </el-descriptions-item>
                    <el-descriptions-item label="评分">
                      {{ plan.score }}
                    </el-descriptions-item>
                  </el-descriptions>
                  
                  <!-- 分配的订单 -->
                  <div class="assigned-orders">
                    <h5>分配订单：</h5>
                    <el-tag 
                      v-for="order in plan.orders" 
                      :key="order.id"
                      style="margin: 2px"
                    >
                      {{ order.order_number }}
                    </el-tag>
                  </div>
                  
                  <!-- 建议 -->
                  <div v-if="plan.suggestions?.length > 0" class="plan-suggestions">
                    <el-alert type="info" :closable="false">
                      <ul>
                        <li v-for="(s, i) in plan.suggestions" :key="i">{{ s }}</li>
                      </ul>
                    </el-alert>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
          
          <!-- 未分配订单 -->
          <div v-if="unassignedOrders.length > 0" class="unassigned-section">
            <el-divider />
            <h4>⚠️ 未分配订单</h4>
            <el-table :data="unassignedOrders" size="small">
              <el-table-column prop="order_number" label="订单号" width="120" />
              <el-table-column prop="reason" label="原因" />
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getOrders } from '@/api/orders'
import { getVehicles } from '@/api/vehicles'
import { autoDispatch, previewDispatch, getMergeSuggestions, applyDispatch, smartDispatch, getAlgorithms } from '@/api/dispatch'

// 订单相关
const pendingOrders = ref([])
const selectedOrders = ref([])
const orderSearch = ref('')
const priorityFilter = ref('')

// 车辆相关
const availableVehicles = ref([])
const selectedVehicles = ref([])

// 调度配置
const dispatchConfig = ref({
  consider_weather: true,
  consider_traffic: true,
  max_orders_per_vehicle: 5,
  algorithm: 'genetic',  // 新增：算法选择
  weights: {             // 新增：多目标权重
    cost: 0.4,
    time: 0.3,
    satisfaction: 0.3
  }
})

// 可用算法列表
const algorithms = ref([
  { id: 'genetic', name: '遗传算法', description: '多目标优化，结果更优' },
  { id: 'greedy', name: '贪心算法', description: '快速响应，适合简单场景' },
  { id: 'balanced', name: '均衡策略', description: '速度和质量的平衡' }
])

// 调度结果
const dispatchPlans = ref([])
const unassignedOrders = ref([])
const dispatchSummary = ref(null)
const mergeClusters = ref([])
const activePlan = ref([0])

// 加载状态
const previewLoading = ref(false)
const dispatchLoading = ref(false)
const applyLoading = ref(false)

// 筛选后的订单
const filteredOrders = computed(() => {
  let result = pendingOrders.value
  
  if (priorityFilter.value) {
    result = result.filter(o => o.priority === priorityFilter.value)
  }
  
  if (orderSearch.value) {
    const search = orderSearch.value.toLowerCase()
    result = result.filter(o => 
      o.order_number?.toLowerCase().includes(search) ||
      o.customer_name?.toLowerCase().includes(search)
    )
  }
  
  return result
})

// 获取优先级类型
const getPriorityType = (priority) => {
  const map = {
    urgent: 'danger',
    express: 'warning',
    normal: 'info'
  }
  return map[priority] || 'info'
}

const getPriorityText = (priority) => {
  const map = {
    urgent: '紧急',
    express: '加急',
    normal: '普通'
  }
  return map[priority] || priority
}

// 全选订单
const selectAllOrders = () => {
  selectedOrders.value = filteredOrders.value.map(o => o.id)
}

// 加载数据
onMounted(async () => {
  await loadPendingOrders()
  await loadAvailableVehicles()
  await loadMergeSuggestions()
})

const loadPendingOrders = async () => {
  try {
    const res = await getOrders({ status: 'pending', per_page: 100 })
    pendingOrders.value = res.orders || []
  } catch (error) {
    console.error('加载订单失败:', error)
  }
}

const loadAvailableVehicles = async () => {
  try {
    const res = await getVehicles({ status: 'available' })
    availableVehicles.value = res.vehicles || []
  } catch (error) {
    console.error('加载车辆失败:', error)
  }
}

const loadMergeSuggestions = async () => {
  try {
    const res = await getMergeSuggestions({ max_distance: 30 })
    if (res.success) {
      mergeClusters.value = res.clusters || []
    }
  } catch (error) {
    console.error('加载合并建议失败:', error)
  }
}

// 预览调度
const handlePreview = async () => {
  if (selectedOrders.value.length === 0) {
    ElMessage.warning('请先选择要调度的订单')
    return
  }
  
  previewLoading.value = true
  
  try {
    const res = await previewDispatch({
      order_ids: selectedOrders.value,
      vehicle_ids: selectedVehicles.value.length > 0 ? selectedVehicles.value : null,
      ...dispatchConfig.value
    })
    
    if (res.success) {
      dispatchPlans.value = res.plans || []
      unassignedOrders.value = res.unassigned_orders || []
      dispatchSummary.value = res.summary
      ElMessage.success(`预览完成：${res.plans.length} 辆车`)
    } else {
      ElMessage.error(res.error || '预览失败')
    }
  } catch (error) {
    ElMessage.error('预览调度失败')
  } finally {
    previewLoading.value = false
  }
}

// 执行调度
const handleAutoDispatch = async () => {
  if (selectedOrders.value.length === 0) {
    ElMessage.warning('请先选择要调度的订单')
    return
  }
  
  dispatchLoading.value = true
  
  try {
    // 使用智能调度 API
    const res = await smartDispatch({
      order_ids: selectedOrders.value,
      vehicle_ids: selectedVehicles.value.length > 0 ? selectedVehicles.value : null,
      weights: dispatchConfig.value.weights,
      consider_weather: dispatchConfig.value.consider_weather,
      consider_traffic: dispatchConfig.value.consider_traffic,
      algorithm: dispatchConfig.value.algorithm
    })
    
    if (res.success) {
      dispatchPlans.value = res.plans || []
      unassignedOrders.value = res.unassigned_orders || []
      dispatchSummary.value = res.summary
      
      const algoName = algorithms.value.find(a => a.id === dispatchConfig.value.algorithm)?.name || dispatchConfig.value.algorithm
      ElMessage.success(`${algoName}调度完成：${res.summary.assigned_orders} 单已分配`)
      
      // 显示优化信息
      if (res.generations) {
        console.log(`遗传算法迭代 ${res.generations} 代，收敛分数: ${res.convergence_score?.toFixed(4)}`)
      }
    } else {
      ElMessage.error(res.error || '调度失败')
    }
  } catch (error) {
    ElMessage.error('执行调度失败')
  } finally {
    dispatchLoading.value = false
  }
}

// 确认执行调度
const handleApplyAll = async () => {
  try {
    await ElMessageBox.confirm(
      '确认执行调度计划？这将更新订单和车辆状态。',
      '确认执行',
      { type: 'warning' }
    )
    
    applyLoading.value = true
    
    const plans = dispatchPlans.value.map(p => ({
      vehicle_id: p.vehicle_id,
      order_ids: p.orders.map(o => o.id)
    }))
    
    const res = await applyDispatch(plans)
    
    if (res.success) {
      ElMessage.success(res.message)
      // 重新加载数据
      await loadPendingOrders()
      await loadAvailableVehicles()
      dispatchPlans.value = []
      dispatchSummary.value = null
      selectedOrders.value = []
    } else {
      ElMessage.error(res.error || '执行失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('执行调度失败')
    }
  } finally {
    applyLoading.value = false
  }
}

// 应用合并建议
const applyMergeCluster = (cluster) => {
  selectedOrders.value = cluster.order_ids
  ElMessage.success(`已选择 ${cluster.orders.length} 个可合并订单`)
}
</script>

<style scoped>
.dispatch-view {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.order-list {
  max-height: 400px;
  overflow-y: auto;
}

.order-item {
  padding: 10px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  margin-bottom: 8px;
  transition: all 0.3s;
}

.order-item.selected {
  background: #ecf5ff;
  border-color: #409eff;
}

.order-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.order-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.order-number {
  font-weight: 500;
  color: #303133;
}

.order-detail {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #909399;
}

.action-bar {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}

.config-hint {
  font-size: 12px;
  color: #909399;
  margin-left: 10px;
}

.config-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.cost {
  font-size: 18px;
  font-weight: bold;
  color: #e6a23c;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  color: #909399;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.plan-list {
  max-height: 500px;
  overflow-y: auto;
}

.plan-title {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.vehicle-name {
  font-weight: 500;
}

.plan-detail {
  padding: 10px 0;
}

.assigned-orders {
  margin-top: 15px;
}

.assigned-orders h5 {
  margin-bottom: 8px;
  color: #606266;
}

.plan-suggestions {
  margin-top: 15px;
}

.plan-suggestions ul {
  margin: 0;
  padding-left: 20px;
}

.merge-cluster {
  padding: 10px;
  background: #f0f9eb;
  border-radius: 4px;
  margin-bottom: 10px;
}

.cluster-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.cluster-info {
  font-size: 12px;
  color: #606266;
}

.unassigned-section h4 {
  color: #f56c6c;
  margin-bottom: 10px;
}
</style>
