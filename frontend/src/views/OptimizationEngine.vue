<template>
  <div class="optimization-engine">
    <div class="page-header">
      <h1>🚀 优化引擎</h1>
      <p class="subtitle">多求解器对比 · 智能推荐 · 多目标优化</p>
    </div>

    <!-- 求解器状态卡片 -->
    <el-row :gutter="20" class="solver-cards">
      <el-col :span="6" v-for="solver in solvers" :key="solver.type">
        <el-card :class="{'solver-available': solver.available, 'solver-unavailable': !solver.available}">
          <div class="solver-info">
            <div class="solver-name">{{ solver.name }}</div>
            <div class="solver-status">
              <el-tag :type="solver.available ? 'success' : 'danger'" size="small">
                {{ solver.available ? '可用' : '不可用' }}
              </el-tag>
            </div>
            <div class="solver-desc">{{ solver.description }}</div>
            <div class="solver-best" v-if="solver.best_for">
              <el-tag type="info" size="small">适用: {{ solver.best_for }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 主要内容区 -->
    <el-tabs v-model="activeTab" class="main-tabs">
      <!-- 快速求解 -->
      <el-tab-pane label="快速求解" name="solve">
        <el-row :gutter="20">
          <!-- 左侧：参数设置 -->
          <el-col :span="8">
            <el-card>
              <template #header>
                <span>📝 参数设置</span>
              </template>
              
              <el-form label-width="100px">
                <el-form-item label="客户数量">
                  <el-slider v-model="solveParams.nCustomers" :min="5" :max="30" show-input />
                </el-form-item>
                
                <el-form-item label="车辆容量">
                  <el-input-number v-model="solveParams.capacity" :min="20" :max="200" :step="10" />
                </el-form-item>
                
                <el-form-item label="求解器">
                  <el-select v-model="solveParams.solver" placeholder="选择求解器">
                    <el-option 
                      v-for="s in availableSolvers" 
                      :key="s.type" 
                      :label="s.name" 
                      :value="s.type"
                    />
                  </el-select>
                </el-form-item>
                
                <el-form-item label="时间限制">
                  <el-input-number v-model="solveParams.timeLimit" :min="10" :max="120" :step="10" />
                  <span style="margin-left: 10px">秒</span>
                </el-form-item>
                
                <el-form-item>
                  <el-button type="primary" @click="runSolve" :loading="solving">
                    🚀 开始求解
                  </el-button>
                  <el-button @click="loadDemoData">加载演示数据</el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>
          
          <!-- 右侧：结果展示 -->
          <el-col :span="16">
            <el-card v-if="solveResult">
              <template #header>
                <span>📊 求解结果</span>
              </template>
              
              <el-row :gutter="20">
                <el-col :span="6">
                  <el-statistic title="求解器" :value="solveResult.solver" />
                </el-col>
                <el-col :span="6">
                  <el-statistic title="总距离" :value="solveResult.total_distance?.toFixed(2)" suffix=" km" />
                </el-col>
                <el-col :span="6">
                  <el-statistic title="求解时间" :value="solveResult.solve_time?.toFixed(2)" suffix=" s" />
                </el-col>
                <el-col :span="6">
                  <el-statistic title="路线数量" :value="solveResult.routes?.length || 0" />
                </el-col>
              </el-row>
              
              <el-divider />
              
              <!-- 路线可视化 -->
              <h4>🗺️ 路线可视化</h4>
              <div ref="routeChartRef" style="width: 100%; height: 300px;"></div>
              
              <el-divider />
              
              <h4>📋 路线详情</h4>
              <el-table :data="routeTableData" max-height="300">
                <el-table-column prop="index" label="路线" width="80" />
                <el-table-column prop="customers" label="客户顺序" />
                <el-table-column prop="load" label="负载" width="80" />
              </el-table>
            </el-card>
            
            <el-empty v-else description="请先设置参数并开始求解" />
          </el-col>
        </el-row>
      </el-tab-pane>
      
      <!-- 求解器对比 -->
      <el-tab-pane label="求解器对比" name="compare">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card>
              <template #header>
                <span>⚙️ 对比设置</span>
              </template>
              
              <el-form label-width="100px">
                <el-form-item label="客户数量">
                  <el-slider v-model="compareParams.nCustomers" :min="5" :max="20" show-input />
                </el-form-item>
                
                <el-form-item label="参与对比">
                  <el-checkbox-group v-model="compareParams.solvers">
                    <el-checkbox 
                      v-for="s in availableSolvers" 
                      :key="s.type" 
                      :label="s.type"
                    >
                      {{ s.name }}
                    </el-checkbox>
                  </el-checkbox-group>
                </el-form-item>
                
                <el-form-item>
                  <el-button type="primary" @click="runCompare" :loading="comparing">
                    📊 开始对比
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>
          
          <el-col :span="16">
            <el-card v-if="compareResult">
              <template #header>
                <span>📈 对比结果</span>
                <el-tag v-if="compareResult.best_solver" type="success" style="margin-left: 10px">
                  最佳: {{ compareResult.best_solver }}
                </el-tag>
              </template>
              
              <el-table :data="compareTableData" style="width: 100%">
                <el-table-column prop="solver" label="求解器" width="150" />
                <el-table-column prop="distance" label="总距离" width="120">
                  <template #default="scope">
                    {{ scope.row.distance?.toFixed(2) }} km
                  </template>
                </el-table-column>
                <el-table-column prop="time" label="求解时间" width="120">
                  <template #default="scope">
                    {{ scope.row.time?.toFixed(2) }} s
                  </template>
                </el-table-column>
                <el-table-column label="评分">
                  <template #default="scope">
                    <el-rate :model-value="scope.row.score" disabled :max="5" />
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
            
            <el-empty v-else description="请先选择求解器并开始对比" />
          </el-col>
        </el-row>
      </el-tab-pane>
      
      <!-- 多目标优化 -->
      <el-tab-pane label="多目标优化" name="multiObjective">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card>
              <template #header>
                <span>🎯 多目标设置</span>
              </template>
              
              <el-form label-width="100px">
                <el-form-item label="客户数量">
                  <el-slider v-model="moParams.nCustomers" :min="5" :max="15" show-input />
                </el-form-item>
                
                <el-form-item label="迭代次数">
                  <el-input-number v-model="moParams.nGen" :min="30" :max="200" :step="10" />
                </el-form-item>
                
                <el-form-item label="算法">
                  <el-radio-group v-model="moParams.solver">
                    <el-radio label="pymoo_nsga2">NSGA-II</el-radio>
                    <el-radio label="pymoo_nsga3">NSGA-III</el-radio>
                  </el-radio-group>
                </el-form-item>
                
                <el-form-item>
                  <el-button type="primary" @click="runMultiObjective" :loading="moOptimizing">
                    🎯 开始优化
                  </el-button>
                </el-form-item>
              </el-form>
              
              <el-alert type="info" :closable="false" style="margin-top: 20px">
                <template #title>
                  优化目标
                </template>
                <ul style="margin: 5px 0; padding-left: 20px;">
                  <li>最小化总距离</li>
                  <li>最小化总时间</li>
                  <li>最小化车辆数</li>
                </ul>
              </el-alert>
            </el-card>
          </el-col>
          
          <el-col :span="16">
            <el-card v-if="moResult">
              <template #header>
                <span>📊 Pareto 最优解</span>
              </template>
              
              <el-row :gutter="20" style="margin-bottom: 20px">
                <el-col :span="8">
                  <el-statistic title="Pareto 前沿大小" :value="moResult.pareto_front_size" />
                </el-col>
                <el-col :span="8">
                  <el-statistic title="求解时间" :value="moResult.solve_time?.toFixed(2)" suffix=" s" />
                </el-col>
              </el-row>
              
              <!-- 目标函数值 -->
              <h4>🎯 目标函数值</h4>
              <el-row :gutter="10">
                <el-col :span="8" v-for="(obj, i) in moResult.objectives" :key="i">
                  <el-card shadow="hover" class="objective-card">
                    <div class="obj-label">{{ objectiveNames[i] }}</div>
                    <div class="obj-value">{{ obj?.toFixed(2) }}</div>
                  </el-card>
                </el-col>
              </el-row>
              
              <el-divider />
              
              <h4>📋 推荐路线</h4>
              <el-table :data="moResult.routes?.map((r, i) => ({index: i+1, customers: r.join(' → '), load: r.length})) || []" max-height="200">
                <el-table-column prop="index" label="路线" width="80" />
                <el-table-column prop="customers" label="客户顺序" />
                <el-table-column prop="load" label="客户数" width="80" />
              </el-table>
            </el-card>
            
            <el-empty v-else description="请先设置参数并开始优化" />
          </el-col>
        </el-row>
      </el-tab-pane>
      
      <!-- 智能推荐 -->
      <el-tab-pane label="智能推荐" name="recommend">
        <el-card>
          <template #header>
            <span>🤖 求解器推荐</span>
          </template>
          
          <el-form :inline="true">
            <el-form-item label="客户数量">
              <el-input-number v-model="recommendParams.nCustomers" :min="5" :max="200" />
            </el-form-item>
            <el-form-item label="目标数量">
              <el-input-number v-model="recommendParams.nObjectives" :min="1" :max="5" />
            </el-form-item>
            <el-form-item label="需要精确解">
              <el-switch v-model="recommendParams.needExact" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="getRecommendation">获取推荐</el-button>
            </el-form-item>
          </el-form>
          
          <el-divider />
          
          <div v-if="recommendation" class="recommendation-result">
            <el-alert :title="`推荐使用: ${recommendation.recommended}`" type="success" :closable="false">
              {{ recommendation.reason }}
            </el-alert>
            
            <div v-if="recommendation.alternatives?.length" style="margin-top: 20px">
              <h4>备选方案</h4>
              <el-tag v-for="alt in recommendation.alternatives" :key="alt" style="margin-right: 10px">
                {{ alt }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

// API 基础路径
const API_BASE = '/api/optimization'

// 状态
const activeTab = ref('solve')
const solvers = ref([])
const solving = ref(false)
const comparing = ref(false)
const moOptimizing = ref(false)

// 图表引用
const routeChartRef = ref(null)
let routeChart = null

// 演示数据
const demoData = ref(null)

// 求解参数
const solveParams = ref({
  nCustomers: 15,
  capacity: 50,
  solver: 'genetic',  // 默认使用遗传算法，稳定可靠
  timeLimit: 30
})

// 对比参数
const compareParams = ref({
  nCustomers: 15,
  solvers: ['genetic', 'ortools']
})

// 多目标参数
const moParams = ref({
  nCustomers: 10,
  nGen: 50,
  solver: 'pymoo_nsga2'
})

// 推荐参数
const recommendParams = ref({
  nCustomers: 20,
  nObjectives: 1,
  needExact: false
})

// 结果
const solveResult = ref(null)
const compareResult = ref(null)
const moResult = ref(null)
const recommendation = ref(null)

// 目标名称
const objectiveNames = ['总距离 (km)', '总时间 (min)', '车辆数']

// 可用求解器（排除 VRPTW 专用求解器）
const availableSolvers = computed(() => {
  return solvers.value.filter(s => s.available && s.type !== 'gurobi_vrptw')
})

// 路线表格数据
const routeTableData = computed(() => {
  if (!solveResult.value?.routes) return []
  
  return solveResult.value.routes.map((route, i) => {
    const load = route.reduce((sum, c) => sum + (demoData.value?.demands[c-1] || 0), 0)
    return {
      index: i + 1,
      customers: `仓库 → ${route.join(' → ')} → 仓库`,
      load: load
    }
  })
})

// 对比表格数据
const compareTableData = computed(() => {
  if (!compareResult.value?.results) return []
  
  const results = compareResult.value.results
  const rankings = compareResult.value.rankings || []
  
  return Object.entries(results).map(([solver, data]) => {
    const rank = rankings.find(r => r[0] === solver)
    return {
      solver,
      distance: data.total_distance,
      time: data.solve_time,
      gap: data.gap,
      score: rank ? Math.max(1, 6 - rankings.indexOf(rank)) : 3
    }
  })
})

// 加载求解器列表
async function loadSolvers() {
  try {
    const res = await axios.get(`${API_BASE}/solvers`)
    solvers.value = res.data.solvers || []
  } catch (e) {
    console.error('加载求解器失败', e)
  }
}

// 加载演示数据
async function loadDemoData() {
  try {
    const res = await axios.get(`${API_BASE}/demo`)
    demoData.value = res.data
    solveParams.value.nCustomers = res.data.n_customers
    ElMessage.success('演示数据加载成功')
  } catch (e) {
    ElMessage.error('加载演示数据失败')
  }
}

// 绘制路线图
function drawRouteChart() {
  if (!routeChartRef.value || !demoData.value || !solveResult.value?.routes) return
  
  try {
    if (routeChart) {
      routeChart.dispose()
    }
    routeChart = echarts.init(routeChartRef.value)
    
    const depot = demoData.value.depot
    const customers = demoData.value.customers
    const routes = solveResult.value.routes
    
    // 节点数据
    const data = [
      { name: '仓库', value: [...depot], symbolSize: 30, itemStyle: { color: '#e74c3c' } }
    ]
    
    customers.slice(0, solveParams.value.nCustomers).forEach((c, i) => {
      data.push({
        name: `${i + 1}`,
        value: [...c],
        symbolSize: 12,
        itemStyle: { color: '#3498db' }
      })
    })
    
    // 路线数据
    const colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#16a085']
    const links = []
    
    routes.forEach((route, routeIdx) => {
      const color = colors[routeIdx % colors.length]
      
      // 仓库到第一个客户
      if (route.length > 0) {
        links.push({
          source: '仓库',
          target: `${route[0]}`,
          lineStyle: { color, width: 2, curveness: 0.1 }
        })
      }
      
      // 客户之间
      for (let i = 0; i < route.length - 1; i++) {
        links.push({
          source: `${route[i]}`,
          target: `${route[i + 1]}`,
          lineStyle: { color, width: 2, curveness: 0.1 }
        })
      }
      
      // 最后一个客户返回仓库
      if (route.length > 0) {
        links.push({
          source: `${route[route.length - 1]}`,
          target: '仓库',
          lineStyle: { color, width: 2, curveness: 0.1 }
        })
      }
    })
    
    const option = {
      title: { text: '路线可视化', left: 'center', top: 10 },
      tooltip: { trigger: 'item' },
      animationDurationUpdate: 1500,
      animationEasingUpdate: 'quinticInOut',
      series: [{
        type: 'graph',
        layout: 'none',
        symbolSize: 12,
        roam: true,
        label: { 
          show: true, 
          position: 'right',
          fontSize: 10
        },
        edgeSymbol: ['circle', 'arrow'],
        edgeSymbolSize: [4, 8],
        cursor: 'pointer',
        data: data,
        links: links,
        lineStyle: { opacity: 0.9 },
        coordinateSystem: 'cartesian2d'
      }],
      xAxis: { 
        type: 'value', 
        min: 0, 
        max: 100,
        show: false
      },
      yAxis: { 
        type: 'value', 
        min: 0, 
        max: 100,
        show: false
      },
      grid: {
        left: '5%',
        right: '5%',
        top: '15%',
        bottom: '5%'
      }
    }
    
    routeChart.setOption(option)
  } catch (e) {
    console.log('图表绘制失败', e)
  }
}

// 运行求解
async function runSolve() {
  solving.value = true
  solveResult.value = null
  
  try {
    if (!demoData.value) {
      await loadDemoData()
    }
    
    const n = solveParams.value.nCustomers
    const payload = {
      customers: demoData.value.customers.slice(0, n),
      demands: demoData.value.demands.slice(0, n),
      depot: demoData.value.depot,
      capacity: solveParams.value.capacity,
      solver: solveParams.value.solver,
      time_limit: solveParams.value.timeLimit
    }
    
    const res = await axios.post(`${API_BASE}/solve`, payload)
    solveResult.value = res.data
    
    if (res.data.success) {
      ElMessage.success('求解成功')
      nextTick(() => drawRouteChart())
    } else {
      ElMessage.error(res.data.error || '求解失败')
    }
  } catch (e) {
    ElMessage.error('求解出错: ' + (e.response?.data?.error || e.message))
  } finally {
    solving.value = false
  }
}

// 运行对比
async function runCompare() {
  comparing.value = true
  compareResult.value = null
  
  try {
    if (!demoData.value) {
      await loadDemoData()
    }
    
    const n = compareParams.value.nCustomers
    const payload = {
      customers: demoData.value.customers.slice(0, n),
      demands: demoData.value.demands.slice(0, n),
      depot: demoData.value.depot,
      capacity: 50,
      solvers: compareParams.value.solvers,
      time_limit: 30
    }
    
    const res = await axios.post(`${API_BASE}/compare`, payload)
    compareResult.value = res.data
    
    if (res.data.success) {
      ElMessage.success('对比完成')
    }
  } catch (e) {
    ElMessage.error('对比出错: ' + (e.response?.data?.error || e.message))
  } finally {
    comparing.value = false
  }
}

// 运行多目标优化
async function runMultiObjective() {
  moOptimizing.value = true
  moResult.value = null
  
  try {
    if (!demoData.value) {
      await loadDemoData()
    }
    
    const n = moParams.value.nCustomers
    const payload = {
      customers: demoData.value.customers.slice(0, n),
      demands: demoData.value.demands.slice(0, n),
      depot: demoData.value.depot,
      capacity: 50,
      solver: moParams.value.solver,
      n_gen: moParams.value.nGen
    }
    
    const res = await axios.post(`${API_BASE}/multi-objective`, payload)
    moResult.value = res.data
    
    if (res.data.success) {
      ElMessage.success('多目标优化完成')
    }
  } catch (e) {
    ElMessage.error('优化出错: ' + (e.response?.data?.error || e.message))
  } finally {
    moOptimizing.value = false
  }
}

// 获取推荐
async function getRecommendation() {
  try {
    const res = await axios.post(`${API_BASE}/recommend`, recommendParams.value)
    recommendation.value = res.data
  } catch (e) {
    ElMessage.error('获取推荐失败')
  }
}

// 初始化
onMounted(() => {
  loadSolvers()
})
</script>

<style scoped>
.optimization-engine {
  padding: 20px;
}

.page-header {
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 28px;
  margin-bottom: 10px;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.solver-cards {
  margin-bottom: 20px;
}

.solver-available {
  border-left: 4px solid #67C23A;
}

.solver-unavailable {
  border-left: 4px solid #F56C6C;
  opacity: 0.6;
}

.solver-info {
  text-align: center;
}

.solver-name {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 8px;
}

.solver-status {
  margin-bottom: 8px;
}

.solver-desc {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.solver-best {
  margin-top: 8px;
}

.main-tabs {
  margin-top: 20px;
}

.objective-card {
  text-align: center;
  padding: 10px;
}

.obj-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 5px;
}

.obj-value {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
}

.recommendation-result {
  padding: 20px 0;
}
</style>
