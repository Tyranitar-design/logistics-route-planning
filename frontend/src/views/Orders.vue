<template>
  <div class="orders-page">
    <!-- 搜索栏 -->
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="订单状态">
          <el-select v-model="searchForm.status" placeholder="全部" clearable>
            <el-option label="待分配" value="pending" />
            <el-option label="已分配" value="assigned" />
            <el-option label="运输中" value="in_transit" />
            <el-option label="已送达" value="delivered" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="searchForm.priority" placeholder="全部" clearable>
            <el-option label="低" value="low" />
            <el-option label="普通" value="normal" />
            <el-option label="高" value="high" />
            <el-option label="紧急" value="urgent" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadOrders">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 操作栏 -->
    <el-card class="toolbar-card">
      <el-button type="primary" @click="showAddDialog" v-if="canEdit">
        <el-icon><Plus /></el-icon> 新增订单
      </el-button>
      <span v-else style="color: #909399; font-size: 14px;">
        💡 您是普通用户，仅可查看数据
      </span>
    </el-card>
    
    <!-- 订单列表 -->
    <el-card class="table-card">
      <el-table :data="orders" v-loading="loading" stripe>
        <el-table-column prop="order_number" label="订单号" width="150" />
        <el-table-column prop="cargo_name" label="货物名称" width="120" />
        <el-table-column label="起点" width="120">
          <template #default="{ row }">
            {{ row.pickup_node?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="终点" width="120">
          <template #default="{ row }">
            {{ row.delivery_node?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="weight" label="重量(kg)" width="80" />
        <el-table-column label="预估成本" width="100">
          <template #default="{ row }">
            <span v-if="row.estimated_cost">{{ row.estimated_cost }} 元</span>
            <span v-else style="color: #909399">未计算</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ statusMap[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="70">
          <template #default="{ row }">
            <el-tag :type="getPriorityType(row.priority)" size="small">
              {{ priorityMap[row.priority] || row.priority }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="150">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="280">
          <template #default="{ row }">
            <el-button size="small" @click="showRouteRecommend(row)" type="success">
              路线推荐
            </el-button>
            <el-button size="small" @click="showDetail(row)">详情</el-button>
            <el-button size="small" type="primary" @click="showAssignDialog(row)" 
                       v-if="row.status === 'pending' && canEdit">分配</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)"
                       v-if="row.status === 'pending' && canEdit">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.perPage"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadOrders"
        @current-change="loadOrders"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>
    
    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="800px" :close-on-click-modal="false">
      <el-form :model="orderForm" :rules="rules" ref="formRef" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="货物名称" prop="cargo_name">
              <el-input v-model="orderForm.cargo_name" placeholder="请输入货物名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="货物类型">
              <el-input v-model="orderForm.cargo_type" placeholder="如：易碎品、生鲜等" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="起点" prop="pickup_node_id">
              <el-select v-model="orderForm.pickup_node_id" placeholder="选择起点" style="width: 100%" filterable @change="onNodeChange">
                <el-option v-for="node in nodes" :key="node.id" 
                           :label="`${node.name} (${node.province || ''}${node.city || ''})`" 
                           :value="node.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="终点" prop="delivery_node_id">
              <el-select v-model="orderForm.delivery_node_id" placeholder="选择终点" style="width: 100%" filterable @change="onNodeChange">
                <el-option v-for="node in nodes" :key="node.id" 
                           :label="`${node.name} (${node.province || ''}${node.city || ''})`" 
                           :value="node.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="重量(kg)">
              <el-input-number v-model="orderForm.weight" :min="0" :precision="2" style="width: 100%" @change="onNodeChange" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="体积(m3)">
              <el-input-number v-model="orderForm.volume" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="优先级">
              <el-select v-model="orderForm.priority" style="width: 100%">
                <el-option label="低" value="low" />
                <el-option label="普通" value="normal" />
                <el-option label="高" value="high" />
                <el-option label="紧急" value="urgent" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- 路线推荐预览 -->
        <div v-if="routePreview" class="route-preview">
          <el-divider content-position="left">
            <el-icon><Guide /></el-icon> 路线推荐预览
          </el-divider>
          
          <div v-if="routePreviewLoading" style="text-align: center; padding: 20px">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span style="margin-left: 10px">正在计算最优路线...</span>
          </div>
          
          <div v-else-if="routePreview.success" class="route-preview-content">
            <el-alert :title="routePreview.recommendation_reason" type="success" :closable="false" show-icon style="margin-bottom: 15px" />
            
            <el-row :gutter="15">
              <!-- 推荐路线卡片 -->
              <el-col :span="12" v-if="routePreview.recommended_route">
                <el-card shadow="hover" class="route-card recommended">
                  <template #header>
                    <div class="route-card-header">
                      <el-tag type="success" effect="dark">推荐</el-tag>
                      <span>{{ routePreview.recommended_route.source === 'amap' ? '高德地图' : '本地算法' }}</span>
                    </div>
                  </template>
                  <el-descriptions :column="1" size="small">
                    <el-descriptions-item label="距离">{{ routePreview.recommended_route.distance_km }} 公里</el-descriptions-item>
                    <el-descriptions-item label="时长">{{ routePreview.recommended_route.duration_minutes }} 分钟</el-descriptions-item>
                    <el-descriptions-item label="预估成本">{{ routePreview.recommended_route.cost }} 元</el-descriptions-item>
                    <el-descriptions-item label="过路费" v-if="routePreview.recommended_route.tolls">
                      {{ routePreview.recommended_route.tolls }} 元
                    </el-descriptions-item>
                  </el-descriptions>
                </el-card>
              </el-col>
              
              <!-- 高德路线 -->
              <el-col :span="12" v-if="routePreview.amap_route && routePreview.recommended_route?.source !== 'amap'">
                <el-card shadow="hover" class="route-card">
                  <template #header>
                    <span>高德地图</span>
                  </template>
                  <el-descriptions :column="1" size="small">
                    <el-descriptions-item label="距离">{{ routePreview.amap_route.distance_km }} 公里</el-descriptions-item>
                    <el-descriptions-item label="时长">{{ routePreview.amap_route.duration_minutes }} 分钟</el-descriptions-item>
                    <el-descriptions-item label="预估成本">{{ routePreview.amap_route.cost }} 元</el-descriptions-item>
                  </el-descriptions>
                </el-card>
              </el-col>
              
              <!-- 本地路线 -->
              <el-col :span="12" v-if="routePreview.local_route && routePreview.recommended_route?.source !== 'local'">
                <el-card shadow="hover" class="route-card">
                  <template #header>
                    <span>本地算法</span>
                  </template>
                  <el-descriptions :column="1" size="small">
                    <el-descriptions-item label="距离">{{ routePreview.local_route.distance_km }} 公里</el-descriptions-item>
                    <el-descriptions-item label="时长">{{ routePreview.local_route.duration_minutes }} 分钟</el-descriptions-item>
                    <el-descriptions-item label="预估成本">{{ routePreview.local_route.cost }} 元</el-descriptions-item>
                  </el-descriptions>
                </el-card>
              </el-col>
            </el-row>
          </div>
          
          <el-alert v-else type="warning" :title="routePreview.error || '无法获取路线推荐'" :closable="false" />
        </div>
        
        <el-divider />
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="发货人">
              <el-input v-model="orderForm.sender_name" placeholder="发货人姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="发货电话">
              <el-input v-model="orderForm.sender_phone" placeholder="发货人电话" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="收货人">
              <el-input v-model="orderForm.receiver_name" placeholder="收货人姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="收货电话">
              <el-input v-model="orderForm.receiver_phone" placeholder="收货人电话" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="备注">
          <el-input v-model="orderForm.notes" type="textarea" :rows="2" placeholder="订单备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
    
    <!-- 路线推荐详情对话框 -->
    <el-dialog v-model="routeDialogVisible" title="路线推荐" width="900px">
      <div v-if="routeRecommendLoading" style="text-align: center; padding: 40px">
        <el-icon class="is-loading" :size="30"><Loading /></el-icon>
        <div style="margin-top: 15px; color: #909399">正在计算最优路线...</div>
      </div>
      
      <div v-else-if="currentRouteRecommend" class="route-recommend-dialog">
        <!-- 推荐理由 -->
        <el-alert 
          :title="currentRouteRecommend.recommendation_reason" 
          type="success" 
          :closable="false" 
          show-icon 
          style="margin-bottom: 20px"
        />
        
        <!-- 路线对比 -->
        <el-row :gutter="20">
          <!-- 高德地图路线 -->
          <el-col :span="12" v-if="currentRouteRecommend.amap_route">
            <el-card shadow="hover" :class="['route-card', currentRouteRecommend.recommended_route?.source === 'amap' ? 'recommended' : '']">
              <template #header>
                <div class="route-card-header">
                  <span>高德地图</span>
                  <el-tag v-if="currentRouteRecommend.recommended_route?.source === 'amap'" type="success" effect="dark" size="small">推荐</el-tag>
                </div>
              </template>
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item label="距离">{{ currentRouteRecommend.amap_route.distance_km }} 公里</el-descriptions-item>
                <el-descriptions-item label="时长">{{ currentRouteRecommend.amap_route.duration_minutes }} 分钟</el-descriptions-item>
                <el-descriptions-item label="预估成本">{{ currentRouteRecommend.amap_route.cost }} 元</el-descriptions-item>
                <el-descriptions-item label="过路费">{{ currentRouteRecommend.amap_route.tolls || 0 }} 元</el-descriptions-item>
              </el-descriptions>
              
              <!-- 多路线选项 -->
              <div v-if="currentRouteRecommend.amap_route.routes?.length > 1" style="margin-top: 15px">
                <div style="font-size: 13px; color: #606266; margin-bottom: 8px">备选路线：</div>
                <el-radio-group v-model="selectedAmapRouteIndex" size="small">
                  <el-radio-button 
                    v-for="(route, index) in currentRouteRecommend.amap_route.routes.slice(0, 3)" 
                    :key="index"
                    :value="index"
                    :label="index"
                  >
                    方案{{ index + 1 }}: {{ route.distance_km }}km / {{ route.duration_minutes }}分钟
                  </el-radio-button>
                </el-radio-group>
              </div>
              
              <el-button 
                type="primary" 
                size="small" 
                style="margin-top: 15px"
                @click="applyRoute(currentRouteRecommend.amap_route)"
                :disabled="currentRouteRecommend.recommended_route?.source === 'amap'"
              >
                应用此路线
              </el-button>
            </el-card>
          </el-col>
          
          <!-- 本地算法路线 -->
          <el-col :span="12" v-if="currentRouteRecommend.local_route">
            <el-card shadow="hover" :class="['route-card', currentRouteRecommend.recommended_route?.source === 'local' ? 'recommended' : '']">
              <template #header>
                <div class="route-card-header">
                  <span>本地算法</span>
                  <el-tag v-if="currentRouteRecommend.recommended_route?.source === 'local'" type="success" effect="dark" size="small">推荐</el-tag>
                </div>
              </template>
              <el-descriptions :column="1" size="small" border>
                <el-descriptions-item label="距离">{{ currentRouteRecommend.local_route.distance_km }} 公里</el-descriptions-item>
                <el-descriptions-item label="时长">{{ currentRouteRecommend.local_route.duration_minutes }} 分钟</el-descriptions-item>
                <el-descriptions-item label="预估成本">{{ currentRouteRecommend.local_route.cost }} 元</el-descriptions-item>
              </el-descriptions>
              
              <!-- 途经节点 -->
              <div v-if="currentRouteRecommend.local_route.path?.length" style="margin-top: 15px">
                <div style="font-size: 13px; color: #606266; margin-bottom: 8px">途经节点：</div>
                <el-tag v-for="(node, i) in currentRouteRecommend.local_route.path" :key="i" size="small" style="margin: 2px">
                  {{ node.name }}
                </el-tag>
              </div>
              
              <el-button 
                type="primary" 
                size="small" 
                style="margin-top: 15px"
                @click="applyRoute(currentRouteRecommend.local_route)"
                :disabled="currentRouteRecommend.recommended_route?.source === 'local'"
              >
                应用此路线
              </el-button>
            </el-card>
          </el-col>
        </el-row>
      </div>
      
      <template #footer>
        <el-button @click="routeDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
    
    <!-- 分配车辆对话框 -->
    <el-dialog v-model="assignDialogVisible" title="分配车辆" width="400px">
      <el-form label-width="80px">
        <el-form-item label="选择车辆">
          <el-select v-model="selectedVehicleId" placeholder="选择车辆" style="width: 100%">
            <el-option v-for="vehicle in availableVehicles" :key="vehicle.id"
                       :label="`${vehicle.plate_number} - ${vehicle.vehicle_type}`" 
                       :value="vehicle.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAssign">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { getOrders, createOrder, updateOrder, deleteOrder, assignVehicle, recommendOrderRoute, recommendRouteForNodes, applyRouteToOrder } from '@/api/orders'
import { getNodes } from '@/api/nodes'
import { getVehicles } from '@/api/vehicles'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Guide, Loading } from '@element-plus/icons-vue'
import { canEdit as checkCanEdit } from '@/utils/permission'

// 权限控制
const canEdit = computed(() => checkCanEdit())

// 状态映射
const statusMap = {
  pending: '待分配',
  assigned: '已分配',
  in_transit: '运输中',
  delivered: '已送达',
  cancelled: '已取消'
}

const priorityMap = {
  low: '低',
  normal: '普通',
  high: '高',
  urgent: '紧急'
}

// 数据
const orders = ref([])
const nodes = ref([])
const vehicles = ref([])
const availableVehicles = ref([])
const loading = ref(false)
const submitLoading = ref(false)

// 搜索
const searchForm = reactive({
  status: '',
  priority: ''
})

// 分页
const pagination = reactive({
  page: 1,
  perPage: 20,
  total: 0
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('新增订单')
const assignDialogVisible = ref(false)
const routeDialogVisible = ref(false)
const selectedVehicleId = ref(null)
const currentOrder = ref(null)

// 路线推荐
const routePreview = ref(null)
const routePreviewLoading = ref(false)
const currentRouteRecommend = ref(null)
const routeRecommendLoading = ref(false)
const selectedAmapRouteIndex = ref(0)

// 表单
const formRef = ref(null)
const orderForm = reactive({
  cargo_name: '',
  cargo_type: '',
  pickup_node_id: null,
  delivery_node_id: null,
  weight: 0,
  volume: 0,
  priority: 'normal',
  sender_name: '',
  sender_phone: '',
  receiver_name: '',
  receiver_phone: '',
  notes: ''
})

const rules = {
  cargo_name: [{ required: true, message: '请输入货物名称', trigger: 'blur' }],
  pickup_node_id: [{ required: true, message: '请选择起点', trigger: 'change' }],
  delivery_node_id: [{ required: true, message: '请选择终点', trigger: 'change' }]
}

// 加载订单
const loadOrders = async () => {
  loading.value = true
  try {
    const res = await getOrders({
      page: pagination.page,
      per_page: pagination.perPage,
      status: searchForm.status,
      priority: searchForm.priority
    })
    orders.value = res.orders || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('加载订单失败:', error)
    ElMessage.error('加载订单失败')
  } finally {
    loading.value = false
  }
}

// 加载节点
const loadNodes = async () => {
  try {
    const res = await getNodes({ per_page: 100 })
    nodes.value = res.nodes || []
  } catch (error) {
    console.error('加载节点失败:', error)
  }
}

// 加载车辆
const loadVehicles = async () => {
  try {
    const res = await getVehicles({ per_page: 100 })
    vehicles.value = res.vehicles || []
    availableVehicles.value = vehicles.value.filter(v => v.status === 'available')
  } catch (error) {
    console.error('加载车辆失败:', error)
  }
}

// 重置搜索
const resetSearch = () => {
  searchForm.status = ''
  searchForm.priority = ''
  pagination.page = 1
  loadOrders()
}

// 显示新增对话框
const showAddDialog = () => {
  dialogTitle.value = '新增订单'
  Object.assign(orderForm, {
    cargo_name: '',
    cargo_type: '',
    pickup_node_id: null,
    delivery_node_id: null,
    weight: 0,
    volume: 0,
    priority: 'normal',
    sender_name: '',
    sender_phone: '',
    receiver_name: '',
    receiver_phone: '',
    notes: ''
  })
  routePreview.value = null
  dialogVisible.value = true
}

// 节点变化时获取路线预览
const onNodeChange = async () => {
  if (orderForm.pickup_node_id && orderForm.delivery_node_id) {
    await fetchRoutePreview()
  } else {
    routePreview.value = null
  }
}

// 获取路线预览
const fetchRoutePreview = async () => {
  routePreviewLoading.value = true
  routePreview.value = null
  
  try {
    const res = await recommendRouteForNodes(
      orderForm.pickup_node_id,
      orderForm.delivery_node_id,
      orderForm.weight
    )
    
    if (res.success) {
      routePreview.value = res.data
    } else {
      routePreview.value = { success: false, error: res.error }
    }
  } catch (error) {
    console.error('获取路线预览失败:', error)
    routePreview.value = { success: false, error: '获取路线预览失败' }
  } finally {
    routePreviewLoading.value = false
  }
}

// 显示路线推荐对话框
const showRouteRecommend = async (row) => {
  currentOrder.value = row
  routeRecommendLoading.value = true
  routeDialogVisible.value = true
  currentRouteRecommend.value = null
  
  try {
    const res = await recommendOrderRoute(row.id)
    if (res.success) {
      currentRouteRecommend.value = res.data
    } else {
      ElMessage.error(res.error || '获取路线推荐失败')
    }
  } catch (error) {
    console.error('获取路线推荐失败:', error)
    ElMessage.error('获取路线推荐失败')
  } finally {
    routeRecommendLoading.value = false
  }
}

// 应用路线
const applyRoute = async (routeData) => {
  if (!currentOrder.value) return
  
  try {
    const res = await applyRouteToOrder(currentOrder.value.id, routeData)
    if (res.success) {
      ElMessage.success('路线已应用到订单')
      routeDialogVisible.value = false
      loadOrders()
    } else {
      ElMessage.error(res.error || '应用路线失败')
    }
  } catch (error) {
    console.error('应用路线失败:', error)
    ElMessage.error('应用路线失败')
  }
}

// 显示详情
const showDetail = (row) => {
  ElMessage.info('订单详情功能开发中')
}

// 显示分配对话框
const showAssignDialog = (row) => {
  currentOrder.value = row
  selectedVehicleId.value = null
  assignDialogVisible.value = true
}

// 分配车辆
const handleAssign = async () => {
  if (!selectedVehicleId.value) {
    ElMessage.warning('请选择车辆')
    return
  }
  
  try {
    await assignVehicle(currentOrder.value.id, selectedVehicleId.value)
    ElMessage.success('分配成功')
    assignDialogVisible.value = false
    loadOrders()
    loadVehicles()
  } catch (error) {
    ElMessage.error('分配失败')
  }
}

// 提交表单
const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitLoading.value = true
    
    // 转换字段名
    const submitData = {
      cargo_name: orderForm.cargo_name,
      cargo_type: orderForm.cargo_type,
      pickup_node_id: orderForm.pickup_node_id,
      delivery_node_id: orderForm.delivery_node_id,
      weight: orderForm.weight,
      volume: orderForm.volume,
      priority: orderForm.priority,
      notes: orderForm.notes,
      // 添加客户信息
      customer_name: orderForm.sender_name || '未知',
      customer_phone: orderForm.sender_phone || '未知'
    }
    
    await createOrder(submitData)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    loadOrders()
  } catch (error) {
    if (error !== false) {
      ElMessage.error('创建失败')
    }
  } finally {
    submitLoading.value = false
  }
}

// 删除订单
const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该订单吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await deleteOrder(row.id)
      ElMessage.success('删除成功')
      loadOrders()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// 获取状态类型
const getStatusType = (status) => {
  const types = {
    pending: 'info',
    assigned: 'warning',
    in_transit: 'primary',
    delivered: 'success',
    cancelled: 'danger'
  }
  return types[status] || 'info'
}

// 获取优先级类型
const getPriorityType = (priority) => {
  const types = {
    low: 'info',
    normal: 'info',
    high: 'warning',
    urgent: 'danger'
  }
  return types[priority] || 'info'
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadOrders()
  loadNodes()
  loadVehicles()
})
</script>

<style scoped>
.orders-page {
  padding: 20px;
}

.search-card, .toolbar-card {
  margin-bottom: 20px;
}

.table-card {
  margin-bottom: 20px;
}

.route-preview {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
  margin: 15px 0;
}

.route-preview-content {
  margin-top: 10px;
}

.route-card {
  height: 100%;
}

.route-card.recommended {
  border: 2px solid #67C23A;
}

.route-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.route-recommend-dialog {
  padding: 10px 0;
}
</style>
