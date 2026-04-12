<template>
  <div class="network-design-container">
    <!-- 页面标题 -->
    <el-page-header @back="goBack" class="page-header">
      <template #content>
        <span class="text-large font-600 mr-3">物流网络设计</span>
        <el-tag type="success" size="small">设施选址优化</el-tag>
      </template>
      <template #extra>
        <el-button-group>
          <el-button type="success" @click="showSaveDialog = true" :disabled="!result">
            <el-icon><FolderAdd /></el-icon>
            保存场景
          </el-button>
          <el-button type="info" @click="loadScenarios">
            <el-icon><FolderOpened /></el-icon>
            我的场景
          </el-button>
        </el-button-group>
        <el-button type="primary" @click="showHelp = true">
          <el-icon><QuestionFilled /></el-icon>
        </el-button>
      </template>
    </el-page-header>

    <!-- 主要内容区 -->
    <el-row :gutter="20" class="main-content">
      <!-- 左侧：配置面板 -->
      <el-col :span="8">
        <el-card class="config-card">
          <template #header>
            <div class="card-header">
              <span>📐 选址配置</span>
            </div>
          </template>

          <!-- 算法选择 -->
          <el-form :model="config" label-width="120px" class="config-form">
            <el-form-item label="算法类型">
              <el-select v-model="config.algorithm" placeholder="选择算法">
                <el-option label="P-中位选址" value="p-median" />
                <el-option label="集合覆盖" value="covering" />
                <el-option label="容量受限选址" value="cflp" />
                <el-option label="多目标选址" value="multi-objective" />
              </el-select>
            </el-form-item>

            <el-divider content-position="left">测试数据生成</el-divider>

            <el-form-item label="客户数量">
              <el-slider v-model="config.numCustomers" :min="5" :max="50" show-input />
            </el-form-item>

            <el-form-item label="候选位置数">
              <el-slider v-model="config.numCandidates" :min="3" :max="15" show-input />
            </el-form-item>

            <el-form-item label="区域">
              <el-select v-model="config.region">
                <el-option label="中国" value="china" />
                <el-option label="欧洲" value="europe" />
                <el-option label="美国" value="usa" />
              </el-select>
            </el-form-item>

            <el-divider content-position="left">数据来源</el-divider>

            <el-form-item>
              <el-radio-group v-model="config.dataSource">
                <el-radio label="test">测试数据</el-radio>
                <el-radio label="sync">同步节点</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item v-if="config.dataSource === 'test'">
              <el-button type="primary" @click="generateData" :loading="generating">
                生成测试数据
              </el-button>
            </el-form-item>

            <el-form-item v-if="config.dataSource === 'sync'">
              <el-button type="warning" @click="syncFromNodes" :loading="syncing">
                从节点同步
              </el-button>
            </el-form-item>

            <el-divider content-position="left">求解参数</el-divider>

            <!-- P-中位参数 -->
            <template v-if="config.algorithm === 'p-median'">
              <el-form-item label="设施数量">
                <el-input-number v-model="config.numFacilities" :min="1" :max="10" />
              </el-form-item>
              <el-form-item label="求解器">
                <el-select v-model="config.solver">
                  <el-option label="CBC (免费)" value="CBC" />
                  <el-option label="CPLEX (商业)" value="CPLEX" />
                </el-select>
              </el-form-item>
            </template>

            <!-- 集合覆盖参数 -->
            <template v-if="config.algorithm === 'covering'">
              <el-form-item label="服务半径(km)">
                <el-input-number v-model="config.serviceRadius" :min="10" :max="200" :step="10" />
              </el-form-item>
            </template>

            <!-- CFLP 参数 -->
            <template v-if="config.algorithm === 'cflp'">
              <el-form-item label="运输成本/km">
                <el-input-number v-model="config.transportCostPerKm" :min="0.5" :max="10" :step="0.5" :precision="1" />
              </el-form-item>
            </template>

            <!-- 多目标选址参数 -->
            <template v-if="config.algorithm === 'multi-objective'">
              <el-form-item label="设施数量">
                <el-input-number v-model="config.numFacilities" :min="1" :max="10" />
              </el-form-item>
              <el-form-item label="成本权重">
                <el-slider v-model="config.weights.cost" :min="0" :max="1" :step="0.1" show-input />
              </el-form-item>
              <el-form-item label="距离权重">
                <el-slider v-model="config.weights.distance" :min="0" :max="1" :step="0.1" show-input />
              </el-form-item>
              <el-form-item label="均衡性权重">
                <el-slider v-model="config.weights.balance" :min="0" :max="1" :step="0.1" show-input />
              </el-form-item>
              <el-form-item label="求解器">
                <el-select v-model="config.solver">
                  <el-option label="CBC (免费)" value="CBC" />
                  <el-option label="CPLEX (商业)" value="CPLEX" />
                </el-select>
              </el-form-item>
            </template>

            <el-form-item>
              <el-button 
                type="success" 
                size="large" 
                @click="solveProblem" 
                :loading="solving"
                :disabled="!hasData"
              >
                <el-icon><CaretRight /></el-icon>
                开始求解
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 数据统计 -->
        <el-card class="stats-card" v-if="hasData">
          <template #header>
            <span>📊 数据统计</span>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="客户数量">{{ customers.length }}</el-descriptions-item>
            <el-descriptions-item label="候选位置">{{ candidates.length }}</el-descriptions-item>
            <el-descriptions-item label="总需求">{{ totalDemand }}</el-descriptions-item>
            <el-descriptions-item label="平均需求">{{ avgDemand.toFixed(1) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 右侧：结果展示 -->
      <el-col :span="16">
        <!-- 地图可视化 -->
        <el-card class="map-card">
          <template #header>
            <div class="card-header">
              <span>🗺️ 网络可视化</span>
              <el-button-group v-if="result">
                <el-button size="small" :type="viewMode === '2d' ? 'primary' : ''" @click="viewMode = '2d'">2D 地图</el-button>
                <el-button size="small" :type="viewMode === '3d' ? 'primary' : ''" @click="viewMode = '3d'">3D 视图</el-button>
              </el-button-group>
            </div>
          </template>

          <!-- 2D 地图 -->
          <div v-show="viewMode === '2d'" ref="chartRef" class="chart-container"></div>
          
          <!-- 3D 视图 -->
          <div v-show="viewMode === '3d'" class="chart-container">
            <Network3DVisualization
              :customers="customers"
              :candidates="candidates"
              :selectedFacilities="result?.selected_facilities || []"
              :assignments="result?.assignments || {}"
            />
          </div>
        </el-card>

        <!-- 求解结果 -->
        <el-card class="result-card" v-if="result">
          <template #header>
            <div class="card-header">
              <span>✅ 求解结果</span>
              <el-tag type="success">求解耗时: {{ result.solve_time }}s</el-tag>
            </div>
          </template>

          <!-- 关键指标 -->
          <el-row :gutter="20" class="metrics-row">
            <el-col :span="6">
              <el-statistic title="选中设施数" :value="result.selected_facilities?.length || 0">
                <template #suffix>个</template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="总距离" :value="result.total_distance || result.objectives?.total_distance || 0">
                <template #suffix>km</template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="总成本" :value="result.total_cost || result.objectives?.total_cost || 0">
                <template #prefix>¥</template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="运输成本" :value="result.transport_cost || 0">
                <template #prefix>¥</template>
              </el-statistic>
            </el-col>
          </el-row>

          <!-- 多目标选址额外指标 -->
          <el-row :gutter="20" class="metrics-row" v-if="result.objectives && config.algorithm === 'multi-objective'">
            <el-col :span="6">
              <el-statistic title="平均服务距离" :value="result.objectives.avg_service_distance?.toFixed(1) || 0">
                <template #suffix>km</template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="最大服务距离" :value="result.objectives.max_service_distance?.toFixed(1) || 0">
                <template #suffix>km</template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="服务水平" :value="((result.objectives.service_level || 0) * 100).toFixed(1)">
                <template #suffix>%</template>
              </el-statistic>
            </el-col>
            <el-col :span="6">
              <el-statistic title="权重配置" :value="'成本' + ((result.weights_used?.cost || 0) * 100).toFixed(0) + '%'"></el-statistic>
            </el-col>
          </el-row>

          <el-divider />

          <!-- 选中的设施 -->
          <el-table :data="result.selected_facilities" border stripe>
            <el-table-column prop="name" label="设施名称" />
            <el-table-column prop="lat" label="纬度" width="100" />
            <el-table-column prop="lon" label="经度" width="100" />
            <el-table-column prop="capacity" label="容量" width="100" v-if="config.algorithm === 'cflp'" />
            <el-table-column prop="utilization" label="利用率%" width="100" v-if="config.algorithm === 'cflp'">
              <template #default="{ row }">
                <el-progress :percentage="row.utilization" :stroke-width="10" />
              </template>
            </el-table-column>
            <el-table-column prop="fixed_cost" label="固定成本" width="120">
              <template #default="{ row }">
                ¥{{ row.fixed_cost?.toLocaleString() }}
              </template>
            </el-table-column>
          </el-table>

          <el-divider content-position="left">客户-设施分配</el-divider>

          <!-- 分配结果 -->
          <el-table :data="assignmentTable" border stripe max-height="300">
            <el-table-column prop="customerName" label="客户" />
            <el-table-column prop="facilityName" label="分配设施" />
            <el-table-column prop="demand" label="需求量" width="100" />
            <el-table-column prop="distance" label="距离(km)" width="120">
              <template #default="{ row }">
                {{ row.distance?.toFixed(2) }}
              </template>
            </el-table-column>
          </el-table>

          <!-- 雷达图：方案评估 -->
          <el-divider content-position="left">📊 方案评估雷达图</el-divider>
          <div ref="radarChartRef" class="radar-chart-container"></div>

          <!-- 热力图：服务覆盖分析 -->
          <el-divider content-position="left">🔥 服务覆盖热力图</el-divider>
          <div class="heatmap-legend">
            <span>服务距离：</span>
            <span class="legend-item" style="background: #67C23A">优秀(&lt;30km)</span>
            <span class="legend-item" style="background: #E6A23C">良好(30-50km)</span>
            <span class="legend-item" style="background: #F56C6C">较远(50-100km)</span>
            <span class="legend-item" style="background: #909399">偏远(&gt;100km)</span>
          </div>
          <div ref="heatmapChartRef" class="heatmap-chart-container"></div>
        </el-card>

        <!-- 数据预览 -->
        <el-card class="data-card" v-if="hasData && !result">
          <template #header>
            <span>📋 数据预览</span>
          </template>

          <el-tabs>
            <el-tab-pane label="客户数据">
              <el-table :data="customers" border stripe max-height="400">
                <el-table-column prop="id" label="ID" width="60" />
                <el-table-column prop="name" label="名称" />
                <el-table-column prop="lat" label="纬度" width="100" />
                <el-table-column prop="lon" label="经度" width="100" />
                <el-table-column prop="demand" label="需求量" width="100" />
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="候选位置">
              <el-table :data="candidates" border stripe max-height="400">
                <el-table-column prop="id" label="ID" width="60" />
                <el-table-column prop="name" label="名称" />
                <el-table-column prop="lat" label="纬度" width="100" />
                <el-table-column prop="lon" label="经度" width="100" />
                <el-table-column prop="capacity" label="容量" width="100" />
                <el-table-column prop="fixed_cost" label="固定成本" width="120" />
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>
    </el-row>

    <!-- 使用说明对话框 -->
    <el-dialog v-model="showHelp" title="使用说明" width="600px">
      <el-collapse>
        <el-collapse-item title="P-中位选址问题" name="1">
          <p>目标：选择 p 个设施位置，使所有客户到其最近设施的总加权距离最小。</p>
          <p>适用场景：已知需要建设的设施数量，寻找最优位置。</p>
          <p>数学模型：min Σ wᵢ × dᵢⱼ × yᵢⱼ</p>
        </el-collapse-item>
        <el-collapse-item title="集合覆盖问题" name="2">
          <p>目标：选择最少的设施位置，使所有客户都在服务范围内。</p>
          <p>适用场景：需要覆盖所有客户，希望最小化设施数量。</p>
          <p>参数：服务半径（客户到设施的最大允许距离）。</p>
        </el-collapse-item>
        <el-collapse-item title="容量受限选址(CFLP)" name="3">
          <p>目标：在考虑设施容量限制的情况下，最小化总成本（固定成本+运输成本）。</p>
          <p>适用场景：设施有容量限制，需要合理分配客户需求。</p>
          <p>特点：自动决定设施数量，考虑容量约束。</p>
        </el-collapse-item>
      </el-collapse>
    </el-dialog>

    <!-- 保存场景对话框 -->
    <el-dialog v-model="showSaveDialog" title="保存场景" width="500px">
      <el-form :model="saveForm" label-width="100px">
        <el-form-item label="场景名称">
          <el-input v-model="saveForm.name" placeholder="输入场景名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="saveForm.description" type="textarea" :rows="3" placeholder="场景描述（可选）" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="saveForm.status">
            <el-radio label="draft">草稿</el-radio>
            <el-radio label="active">激活</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSaveDialog = false">取消</el-button>
        <el-button type="primary" @click="saveScenario" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 场景列表对话框 -->
    <el-dialog v-model="showScenariosDialog" title="我的场景" width="800px">
      <el-table :data="scenarios" border stripe style="cursor: pointer">
        <el-table-column prop="name" label="名称" width="150" />
        <el-table-column prop="algorithm" label="算法" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.algorithm }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_cost" label="总成本" width="120">
          <template #default="{ row }">
            ¥{{ row.total_cost?.toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column prop="service_level" label="服务水平" width="100">
          <template #default="{ row }">
            {{ (row.service_level * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button-group>
              <el-button size="small" type="primary" @click.stop="loadScenario(row)">加载</el-button>
              <el-button size="small" type="danger" @click.stop="deleteScenario(row.id)">删除</el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { QuestionFilled, CaretRight, FolderAdd, FolderOpened } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import Network3DVisualization from '@/components/Network3DVisualization.vue'

const router = useRouter()

// 配置
const config = reactive({
  algorithm: 'p-median',
  numCustomers: 20,
  numCandidates: 8,
  region: 'china',
  numFacilities: 3,
  solver: 'CBC',
  serviceRadius: 50,
  transportCostPerKm: 2.0,
  weights: {
    cost: 0.4,
    distance: 0.4,
    balance: 0.2
  },
  dataSource: 'test'
})

// 数据
const customers = ref([])
const candidates = ref([])
const result = ref(null)
const generating = ref(false)
const syncing = ref(false)
const solving = ref(false)
const showHelp = ref(false)
const viewMode = ref('2d')
const chartRef = ref(null)
const radarChartRef = ref(null)
const heatmapChartRef = ref(null)
let chartInstance = null
let radarChartInstance = null
let heatmapChartInstance = null

// 场景管理
const showSaveDialog = ref(false)
const showScenariosDialog = ref(false)
const saving = ref(false)
const scenarios = ref([])
const saveForm = reactive({
  name: '',
  description: '',
  status: 'draft'
})

// 计算属性
const hasData = computed(() => customers.value.length > 0 && candidates.value.length > 0)
const totalDemand = computed(() => customers.value.reduce((sum, c) => sum + c.demand, 0))
const avgDemand = computed(() => hasData.value ? totalDemand.value / customers.value.length : 0)

// 分配结果表格
const assignmentTable = computed(() => {
  if (!result.value || !result.value.assignments) return []
  
  return Object.entries(result.value.assignments).map(([custId, facId]) => {
    // 统一转为字符串进行比较，避免类型不匹配（后端返回字符串，前端可能是数字）
    const customer = customers.value.find(c => String(c.id) === String(custId)) || {}
    const facility = candidates.value.find(f => String(f.id) === String(facId)) || {}
    
    // 计算距离
    const lat1 = customer.lat || customer.latitude || 0
    const lon1 = customer.lon || customer.longitude || 0
    const lat2 = facility.lat || facility.latitude || 0
    const lon2 = facility.lon || facility.longitude || 0
    
    const R = 6371
    const dLat = (lat2 - lat1) * Math.PI / 180
    const dLon = (lon2 - lon1) * Math.PI / 180
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2)
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
    const distance = R * c
    
    return {
      customerId: custId,
      customerName: customer.name || `客户${custId}`,
      facilityId: facId,
      facilityName: facility.name || `设施${facId}`,
      demand: customer.demand || 0,
      distance: distance || 0
    }
  })
})

// 生成测试数据
async function generateData() {
  generating.value = true
  result.value = null
  
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch('http://localhost:5000/api/network/test-data/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        num_customers: config.numCustomers,
        num_candidates: config.numCandidates,
        region: config.region
      })
    })
    
    const data = await response.json()
    
    if (data.status === 'success') {
      customers.value = data.customers
      candidates.value = data.candidates
      ElMessage.success(`已生成 ${data.customers.length} 个客户和 ${data.candidates.length} 个候选位置`)
      
      // 更新图表
      await nextTick()
      renderChart()
    } else {
      ElMessage.error(data.error || '生成失败')
    }
  } catch (error) {
    ElMessage.error('生成数据失败: ' + error.message)
  } finally {
    generating.value = false
  }
}

// 从现有节点同步数据
async function syncFromNodes() {
  syncing.value = true
  result.value = null
  
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch('http://localhost:5000/api/network/import/nodes', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        customer_types: ['customer'],
        candidate_types: ['warehouse', 'distribution'],
        default_fixed_cost: 100000,
        default_capacity: 500
      })
    })
    
    const data = await response.json()
    
    if (data.status === 'success') {
      if (data.customers.length === 0 || data.candidates.length === 0) {
        ElMessage.warning('节点数据不足，请先在「节点管理」中添加仓库和客户节点')
        // 自动切换回测试数据
        config.dataSource = 'test'
        return
      }
      
      customers.value = data.customers
      candidates.value = data.candidates
      ElMessage.success(`已同步 ${data.customers.length} 个客户和 ${data.candidates.length} 个候选位置`)
      
      // 更新图表
      await nextTick()
      renderChart()
    } else {
      ElMessage.error(data.message || '同步失败')
    }
  } catch (error) {
    ElMessage.error('同步数据失败: ' + error.message)
  } finally {
    syncing.value = false
  }
}

// 求解问题
async function solveProblem() {
  solving.value = true
  
  try {
    const token = localStorage.getItem('access_token')
    let endpoint = ''
    let body = {}
    
    if (config.algorithm === 'p-median') {
      endpoint = 'location/p-median'
      body = {
        customers: customers.value,
        candidates: candidates.value,
        num_facilities: config.numFacilities,
        solver: config.solver
      }
    } else if (config.algorithm === 'covering') {
      endpoint = 'location/covering'
      body = {
        customers: customers.value,
        candidates: candidates.value,
        service_radius: config.serviceRadius
      }
    } else if (config.algorithm === 'cflp') {
      endpoint = 'location/cflp'
      body = {
        customers: customers.value,
        candidates: candidates.value,
        transport_cost_per_km: config.transportCostPerKm
      }
    } else if (config.algorithm === 'multi-objective') {
      endpoint = 'location/multi-objective'
      body = {
        customers: customers.value,
        candidates: candidates.value,
        num_facilities: config.numFacilities,
        weights: config.weights,
        solver: config.solver
      }
    }
    
    const response = await fetch(`http://localhost:5000/api/network/${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(body)
    })
    
    const data = await response.json()
    
    if (data.status === 'success') {
      result.value = data
      ElMessage.success(`求解成功！耗时 ${data.solve_time}s`)
      
      // 更新图表
      await nextTick()
      renderChart()
      renderRadarChart()
      renderHeatmapChart()
    } else {
      ElMessage.error(data.error || '求解失败')
    }
  } catch (error) {
    ElMessage.error('求解失败: ' + error.message)
  } finally {
    solving.value = false
  }
}

// 渲染图表
function renderChart() {
  if (!chartRef.value) return
  
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  
  const chartData = []
  const links = []
  
  // 客户点（确保唯一名称）
  customers.value.forEach((c, idx) => {
    chartData.push({
      name: `客户_${c.id}_${c.name}`,
      displayName: c.name,
      value: [c.lon, c.lat],
      symbolSize: Math.max(8, (c.demand || 100) / 20),
      itemStyle: { color: '#91CC75' },
      category: 0
    })
  })
  
  // 候选/选中设施
  const selectedIds = result.value?.selected_facilities?.map(f => f.id) || []
  candidates.value.forEach((c, idx) => {
    const isSelected = selectedIds.includes(c.id)
    chartData.push({
      name: `设施_${c.id}_${c.name}`,
      displayName: c.name,
      value: [c.lon, c.lat],
      symbolSize: isSelected ? 25 : 15,
      itemStyle: { 
        color: isSelected ? '#EE6666' : '#999999',
        borderColor: isSelected ? '#FF0000' : '#666666',
        borderWidth: isSelected ? 3 : 1
      },
      category: isSelected ? 1 : 2
    })
  })
  
  // 分配连线
  if (result.value?.assignments) {
    Object.entries(result.value.assignments).forEach(([custId, facId]) => {
      const cust = customers.value.find(c => String(c.id) === String(custId))
      const fac = candidates.value.find(c => String(c.id) === String(facId))
      if (cust && fac) {
        links.push({
          source: `客户_${cust.id}_${cust.name}`,
          target: `设施_${fac.id}_${fac.name}`,
          value: cust.demand || 100,
          lineStyle: {
            color: '#5470C6',
            width: 2,
            curveness: 0.2
          }
        })
      }
    })
  }
  
  const option = {
    title: {
      text: '物流网络可视化',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        if (params.dataType === 'node') {
          const displayName = params.data.displayName || params.name
          return `${displayName}<br/>坐标: ${params.value[1].toFixed(2)}, ${params.value[0].toFixed(2)}`
        }
        return params.name
      }
    },
    legend: {
      data: ['客户', '选中设施', '候选位置'],
      bottom: 10
    },
    geo: {
      map: 'china',
      roam: true,
      emphasis: {
        label: { show: true }
      },
      itemStyle: {
        areaColor: '#f3f3f3',
        borderColor: '#999'
      }
    },
    series: [{
      type: 'graph',
      coordinateSystem: 'geo',
      data: chartData,
      links: links,
      layout: 'none',
      symbolSize: 10,
      label: {
        show: true,
        position: 'right',
        fontSize: 10
      },
      lineStyle: {
        color: '#5470C6',
        width: 2,
        curveness: 0.2
      },
      emphasis: {
        focus: 'adjacency'
      },
      categories: [
        { name: '客户' },
        { name: '选中设施' },
        { name: '候选位置' }
      ]
    }]
  }
  
  chartInstance.setOption(option, true)
}

// 渲染雷达图
function renderRadarChart() {
  if (!radarChartRef.value || !result.value) return
  
  if (!radarChartInstance) {
    radarChartInstance = echarts.init(radarChartRef.value)
  }
  
  // 计算雷达图指标
  const metrics = result.value.objectives || {}
  
  // 标准化指标（0-100分）
  // 成本越低越好，所以用反向计算
  const maxCost = 1000000 // 假设最大成本
  const maxDistance = 5000 // 假设最大平均距离
  
  const costScore = Math.max(0, 100 - (result.value.total_cost || metrics.total_cost || 0) / maxCost * 100)
  const distanceScore = Math.max(0, 100 - (result.value.total_distance || metrics.total_distance || 0) / maxDistance * 100)
  const serviceScore = (metrics.service_level || 0) * 100
  const balanceScore = Math.max(0, 100 - (metrics.max_service_distance || 500) / 5)
  
  // 覆盖率 = 服务水平
  const coverageScore = serviceScore
  
  const radarData = {
    dimensions: ['成本', '距离', '服务水平', '均衡性', '覆盖率'],
    values: [costScore, distanceScore, serviceScore, balanceScore, coverageScore]
  }
  
  const option = {
    title: {
      text: '方案综合评估',
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        return params.name + '<br/>' + 
          radarData.dimensions.map((d, i) => 
            `${d}: ${radarData.values[i].toFixed(1)}分`
          ).join('<br/>')
      }
    },
    radar: {
      indicator: radarData.dimensions.map(name => ({
        name,
        max: 100
      })),
      shape: 'polygon',
      splitNumber: 5,
      axisName: {
        color: '#333',
        fontSize: 12
      },
      splitLine: {
        lineStyle: { color: '#ddd' }
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['rgba(64, 158, 255, 0.1)', 'rgba(64, 158, 255, 0.2)', 
                  'rgba(64, 158, 255, 0.3)', 'rgba(64, 158, 255, 0.4)', 
                  'rgba(64, 158, 255, 0.5)']
        }
      }
    },
    series: [{
      type: 'radar',
      data: [{
        value: radarData.values,
        name: '当前方案',
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: {
          color: '#409EFF',
          width: 2
        },
        areaStyle: {
          color: 'rgba(64, 158, 255, 0.3)'
        },
        itemStyle: {
          color: '#409EFF'
        }
      }]
    }]
  }
  
  radarChartInstance.setOption(option, true)
}

// 渲染热力图
function renderHeatmapChart() {
  if (!heatmapChartRef.value || !result.value || !result.value.assignments) return
  
  if (!heatmapChartInstance) {
    heatmapChartInstance = echarts.init(heatmapChartRef.value)
  }
  
  // 构建热力图数据
  const heatmapData = []
  const distances = []
  
  // 计算每个客户的服务距离
  Object.entries(result.value.assignments).forEach(([custId, facId]) => {
    const cust = customers.value.find(c => String(c.id) === String(custId))
    const fac = candidates.value.find(c => String(c.id) === String(facId))
    
    if (cust && fac) {
      // 计算距离
      const R = 6371
      const dLat = (fac.lat - cust.lat) * Math.PI / 180
      const dLon = (fac.lon - cust.lon) * Math.PI / 180
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(cust.lat * Math.PI / 180) * Math.cos(fac.lat * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2)
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
      const distance = R * c
      
      distances.push(distance)
      
      // 根据距离确定颜色
      let color
      if (distance < 30) {
        color = '#67C23A' // 绿色 - 优秀
      } else if (distance < 50) {
        color = '#E6A23C' // 橙色 - 良好
      } else if (distance < 100) {
        color = '#F56C6C' // 红色 - 较远
      } else {
        color = '#909399' // 灰色 - 偏远
      }
      
      heatmapData.push({
        name: cust.name,
        value: [cust.lon, cust.lat, distance],
        symbolSize: Math.max(10, cust.demand / 15),
        itemStyle: {
          color: color,
          borderColor: '#fff',
          borderWidth: 2
        }
      })
    }
  })
  
  // 统计信息
  const avgDistance = distances.length > 0 ? distances.reduce((a, b) => a + b, 0) / distances.length : 0
  const maxDistance = distances.length > 0 ? Math.max(...distances) : 0
  const excellentCount = distances.filter(d => d < 30).length
  const goodCount = distances.filter(d => d >= 30 && d < 50).length
  const fairCount = distances.filter(d => d >= 50 && d < 100).length
  const poorCount = distances.filter(d => d >= 100).length
  
  const option = {
    title: {
      text: `服务覆盖分析 (平均: ${avgDistance.toFixed(1)}km, 最大: ${maxDistance.toFixed(1)}km)`,
      left: 'center',
      textStyle: { fontSize: 14 }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        return `${params.name}<br/>服务距离: ${params.value[2].toFixed(1)} km`
      }
    },
    legend: {
      data: ['优秀(<30km)', '良好(30-50km)', '较远(50-100km)', '偏远(>100km)'],
      bottom: 10
    },
    geo: {
      map: 'china',
      roam: true,
      emphasis: {
        label: { show: true }
      },
      itemStyle: {
        areaColor: '#f5f5f5',
        borderColor: '#ccc'
      }
    },
    series: [{
      type: 'scatter',
      coordinateSystem: 'geo',
      data: heatmapData,
      symbolSize: function(val) {
        return Math.max(8, val[2] / 5)
      },
      label: {
        show: true,
        position: 'right',
        fontSize: 9,
        formatter: '{b}'
      },
      emphasis: {
        focus: 'self'
      }
    }],
    graphic: [
      {
        type: 'text',
        right: 20,
        top: 60,
        style: {
          text: [
            `✅ 优秀: ${excellentCount} 个`,
            `🟡 良好: ${goodCount} 个`,
            `🔴 较远: ${fairCount} 个`,
            `⚫ 偏远: ${poorCount} 个`
          ].join('\n'),
          font: '12px Microsoft YaHei',
          fill: '#666',
          lineHeight: 20
        }
      }
    ]
  }
  
  heatmapChartInstance.setOption(option, true)
}

async function loadScenarios() {
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch('http://localhost:5000/api/network/scenarios', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await response.json()
    
    if (data.status === 'success') {
      scenarios.value = data.scenarios
      showScenariosDialog.value = true
    }
  } catch (error) {
    ElMessage.error('加载场景失败: ' + error.message)
  }
}

async function saveScenario() {
  if (!saveForm.name) {
    ElMessage.warning('请输入场景名称')
    return
  }
  
  saving.value = true
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch('http://localhost:5000/api/network/scenarios', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        name: saveForm.name,
        description: saveForm.description,
        status: saveForm.status,
        algorithm: config.algorithm,
        customers: customers.value,
        candidates: candidates.value,
        parameters: {
          numFacilities: config.numFacilities,
          serviceRadius: config.serviceRadius,
          transportCostPerKm: config.transportCostPerKm
        },
        selected_facilities: result.value?.selected_facilities || [],
        assignments: result.value?.assignments || {},
        total_cost: result.value?.total_cost || 0,
        total_distance: result.value?.total_distance || 0,
        total_fixed_cost: result.value?.total_fixed_cost || 0,
        transport_cost: result.value?.transport_cost || 0,
        solve_time: result.value?.solve_time || 0,
        solver: result.value?.solver || 'CBC'
      })
    })
    
    const data = await response.json()
    
    if (data.status === 'success') {
      ElMessage.success('场景保存成功！')
      showSaveDialog.value = false
      saveForm.name = ''
      saveForm.description = ''
    } else {
      ElMessage.error(data.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存场景失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

function loadScenario(scenario) {
  // 加载场景数据
  customers.value = scenario.customers || []
  candidates.value = scenario.candidates || []
  result.value = {
    selected_facilities: scenario.selected_facilities || [],
    assignments: scenario.assignments || {},
    total_cost: scenario.total_cost,
    total_distance: scenario.total_distance,
    total_fixed_cost: scenario.total_fixed_cost,
    transport_cost: scenario.transport_cost,
    solve_time: scenario.solve_time,
    solver: scenario.solver,
    // 添加服务指标用于雷达图
    objectives: {
      total_cost: scenario.total_cost,
      total_distance: scenario.total_distance,
      avg_service_distance: scenario.avg_distance,
      max_service_distance: scenario.max_distance,
      service_level: scenario.service_level
    }
  }
  
  // 加载参数
  if (scenario.parameters) {
    config.numFacilities = scenario.parameters.numFacilities || 3
    config.serviceRadius = scenario.parameters.serviceRadius || 50
    config.transportCostPerKm = scenario.parameters.transportCostPerKm || 2.0
  }
  config.algorithm = scenario.algorithm
  
  showScenariosDialog.value = false
  ElMessage.success(`已加载场景: ${scenario.name}`)
  
  // 更新图表
  nextTick(() => {
    renderChart()
    renderRadarChart()
    renderHeatmapChart()
  })
}

async function deleteScenario(scenarioId) {
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(`http://localhost:5000/api/network/scenarios/${scenarioId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    
    const data = await response.json()
    
    if (data.status === 'success') {
      ElMessage.success('场景已删除')
      scenarios.value = scenarios.value.filter(s => s.id !== scenarioId)
    }
  } catch (error) {
    ElMessage.error('删除失败: ' + error.message)
  }
}

// 返回
function goBack() {
  router.push('/')
}

// 初始化
onMounted(async () => {
  // 注册中国地图
  try {
    const chinaJson = await fetch('/china.json').then(res => res.json())
    echarts.registerMap('china', chinaJson)
  } catch (e) {
    console.warn('加载中国地图失败:', e)
  }
  
  // 根据数据来源初始化
  if (config.dataSource === 'test') {
    await generateData()
  } else {
    // 同步模式下尝试同步，失败则生成测试数据
    await syncFromNodes()
    if (customers.value.length === 0) {
      config.dataSource = 'test'
      await generateData()
    }
  }
})
</script>

<style scoped>
.network-design-container {
  padding: 20px;
  background: #f5f7fa;
  min-height: 100vh;
}

.page-header {
  margin-bottom: 20px;
  background: white;
  padding: 15px 20px;
  border-radius: 8px;
}

.main-content {
  margin-top: 10px;
}

.config-card,
.stats-card,
.map-card,
.result-card,
.data-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-form {
  padding: 10px 0;
}

.chart-container {
  width: 100%;
  height: 500px;
}

.radar-chart-container {
  width: 100%;
  height: 350px;
  margin-top: 10px;
}

.heatmap-chart-container {
  width: 100%;
  height: 400px;
  margin-top: 10px;
}

.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.legend-item {
  padding: 2px 8px;
  border-radius: 4px;
  color: white;
  font-size: 12px;
}

.metrics-row {
  margin-bottom: 20px;
  text-align: center;
}

:deep(.el-statistic__content) {
  font-size: 24px;
  font-weight: bold;
}
</style>
