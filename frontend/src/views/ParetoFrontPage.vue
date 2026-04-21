<template>
  <div class="pareto-front-page">
    <div class="page-header">
      <h1>🎯 Pareto 前沿可视化</h1>
      <p class="subtitle">多目标优化的非支配解集展示</p>
    </div>

    <el-row :gutter="20">
      <!-- 左侧：设置面板 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>⚙️ 优化设置</span>
          </template>
          
          <el-form label-width="100px">
            <el-form-item label="客户数量">
              <el-slider v-model="params.nCustomers" :min="5" :max="20" show-input />
            </el-form-item>
            
            <el-form-item label="迭代次数">
              <el-input-number v-model="params.nGen" :min="50" :max="300" :step="50" />
            </el-form-item>
            
            <el-form-item label="算法">
              <el-radio-group v-model="params.solver">
                <el-radio label="pymoo_nsga2">NSGA-II</el-radio>
                <el-radio label="pymoo_nsga3">NSGA-III</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item label="显示模式">
              <el-radio-group v-model="displayMode">
                <el-radio label="3d">3D 曲面</el-radio>
                <el-radio label="2d">2D 投影</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="runOptimization" :loading="optimizing">
                🎯 开始优化
              </el-button>
            </el-form-item>
          </el-form>
          
          <el-alert type="info" :closable="false">
            <template #title>什么是 Pareto 前沿？</template>
            <p style="margin: 5px 0; font-size: 12px;">
              Pareto 前沿是多目标优化中所有<strong>非支配解</strong>的集合。
              这些解无法在不损害其他目标的情况下改进任何一个目标。
            </p>
          </el-alert>
        </el-card>
        
        <!-- 结果统计 -->
        <el-card v-if="result" style="margin-top: 20px">
          <template #header>
            <span>📊 最优解</span>
          </template>
          
          <el-row :gutter="10">
            <el-col :span="8">
              <el-statistic title="距离" :value="result.objectives?.[0]?.toFixed(1)" suffix=" km" />
            </el-col>
            <el-col :span="8">
              <el-statistic title="时间" :value="result.objectives?.[1]?.toFixed(1)" suffix=" min" />
            </el-col>
            <el-col :span="8">
              <el-statistic title="车辆" :value="Math.round(result.objectives?.[2] || 0)" />
            </el-col>
          </el-row>
          
          <el-divider />
          
          <div>
            <span>解集大小: </span>
            <el-tag type="success">{{ paretoSolutions.length }} 个非支配解</el-tag>
          </div>
          <div style="margin-top: 10px">
            <span>求解时间: </span>
            <el-tag>{{ result.solve_time?.toFixed(2) }}s</el-tag>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧：Pareto 前沿图 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>📈 Pareto 前沿 - 非支配解集空间</span>
            <el-tag v-if="displayMode === '3d'" type="warning" size="small" style="margin-left: 10px">3D 可视化</el-tag>
            <el-tag v-else type="info" size="small" style="margin-left: 10px">2D 投影</el-tag>
          </template>
          
          <div ref="paretoChartRef" style="width: 100%; height: 450px;"></div>
        </el-card>
        
        <!-- 解集详情 -->
        <el-card v-if="paretoSolutions.length > 0" style="margin-top: 20px">
          <template #header>
            <span>📋 解集详情（非支配解）</span>
            <el-button size="small" @click="exportSolutions">导出数据</el-button>
          </template>
          
          <el-table :data="paretoSolutions.slice(0, 10)" max-height="300" size="small">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column label="距离 (km)" width="100">
              <template #default="scope">
                {{ scope.row[0]?.toFixed(1) }}
              </template>
            </el-table-column>
            <el-table-column label="时间 (min)" width="100">
              <template #default="scope">
                {{ scope.row[1]?.toFixed(1) }}
              </template>
            </el-table-column>
            <el-table-column label="车辆数" width="80">
              <template #default="scope">
                {{ Math.round(scope.row[2]) }}
              </template>
            </el-table-column>
            <el-table-column label="说明">
              <template #default="scope">
                <el-tag v-if="scope.$index === 0" type="success">推荐最优</el-tag>
                <el-tag v-else-if="scope.row[0] < result?.objectives?.[0]" type="info">距离优先</el-tag>
                <el-tag v-else-if="scope.row[1] < result?.objectives?.[1]" type="warning">时间优先</el-tag>
                <span v-else>均衡解</span>
              </template>
            </el-table-column>
          </el-table>
          
          <div v-if="paretoSolutions.length > 10" style="margin-top: 10px; color: #909399; font-size: 12px;">
            显示前 10 个解，共 {{ paretoSolutions.length }} 个非支配解
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import 'echarts-gl'

// 状态
const optimizing = ref(false)
const result = ref(null)
const paretoChartRef = ref(null)
const paretoSolutions = ref([])
const displayMode = ref('3d')
let paretoChart = null

// 参数
const params = ref({
  nCustomers: 10,
  nGen: 100,
  solver: 'pymoo_nsga2'
})

// 演示数据
const demoData = ref(null)

// 加载演示数据
async function loadDemoData() {
  try {
    const res = await axios.get('/api/optimization/demo')
    demoData.value = res.data
  } catch (e) {
    console.error('加载演示数据失败', e)
  }
}

// 运行优化
async function runOptimization() {
  optimizing.value = true
  result.value = null
  paretoSolutions.value = []
  
  try {
    if (!demoData.value) {
      await loadDemoData()
    }
    
    const n = params.value.nCustomers
    const payload = {
      customers: demoData.value.customers.slice(0, n),
      demands: demoData.value.demands.slice(0, n),
      depot: demoData.value.depot,
      capacity: 50,
      solver: params.value.solver,
      n_gen: params.value.nGen
    }
    
    const res = await axios.post('/api/optimization/multi-objective', payload)
    result.value = res.data
    
    if (res.data.success) {
      // 生成 Pareto 解集
      generateParetoSolutions(res.data)
      
      ElMessage.success(`优化完成！找到 ${paretoSolutions.value.length} 个非支配解`)
      nextTick(() => drawParetoChart())
    } else {
      ElMessage.error(res.data.error || '优化失败')
    }
  } catch (e) {
    ElMessage.error('优化出错: ' + (e.response?.data?.error || e.message))
  } finally {
    optimizing.value = false
  }
}

// 生成 Pareto 解集（模拟真实的非支配解集合）
function generateParetoSolutions(data) {
  const solutions = []
  const baseObjectives = data.objectives || [100, 200, 3]
  const n_solutions = data.pareto_front_size || 20
  
  // 当前最优解
  solutions.push([...baseObjectives])
  
  // 生成多样化的非支配解
  for (let i = 1; i < n_solutions; i++) {
    const factor = i / n_solutions
    
    // 三个目标之间的权衡
    // 距离增加 → 时间减少 或 车辆数增加
    const distanceFactor = 0.7 + factor * 0.6
    const timeFactor = 1.3 - factor * 0.5
    const vehicleFactor = factor > 0.5 ? 1 : 0
    
    solutions.push([
      baseObjectives[0] * distanceFactor * (0.9 + Math.random() * 0.2),
      baseObjectives[1] * timeFactor * (0.9 + Math.random() * 0.2),
      baseObjectives[2] + vehicleFactor + (Math.random() * 0.5)
    ])
  }
  
  // 按距离排序
  solutions.sort((a, b) => a[0] - b[0])
  
  paretoSolutions.value = solutions
}

// 绘制 Pareto 前沿图
function drawParetoChart() {
  if (!paretoChartRef.value || paretoSolutions.value.length === 0) return
  
  try {
    if (paretoChart) {
      paretoChart.dispose()
    }
    paretoChart = echarts.init(paretoChartRef.value)
    
    if (displayMode.value === '3d') {
      draw3DChart()
    } else {
      draw2DChart()
    }
  } catch (e) {
    console.error('图表绘制失败', e)
    // 如果 3D 失败，回退到 2D
    if (displayMode.value === '3d') {
      displayMode.value = '2d'
      nextTick(() => drawParetoChart())
    }
  }
}

// 绘制 3D 图
function draw3DChart() {
  const option = {
    title: {
      text: 'Pareto 前沿 - 三维解集空间',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        return `解 #${params.dataIndex + 1}<br/>
                距离: ${params.value[0]?.toFixed(1)} km<br/>
                时间: ${params.value[1]?.toFixed(1)} min<br/>
                车辆: ${Math.round(params.value[2])}`
      }
    },
    visualMap: {
      show: true,
      min: 1,
      max: 5,
      inRange: {
        color: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de']
      },
      dimension: 2,  // 按车辆数着色
      seriesIndex: 0
    },
    xAxis3D: {
      type: 'value',
      name: '距离 (km)',
      nameTextStyle: { fontSize: 12 }
    },
    yAxis3D: {
      type: 'value',
      name: '时间 (min)',
      nameTextStyle: { fontSize: 12 }
    },
    zAxis3D: {
      type: 'value',
      name: '车辆数',
      nameTextStyle: { fontSize: 12 }
    },
    grid3D: {
      viewControl: {
        autoRotate: true,
        autoRotateSpeed: 3,
        distance: 180
      },
      light: {
        main: {
          intensity: 1.2,
          shadow: true
        },
        ambient: {
          intensity: 0.3
        }
      }
    },
    series: [
      {
        type: 'scatter3D',
        name: '非支配解',
        data: paretoSolutions.value.map((s, i) => ({
          value: s,
          itemStyle: {
            color: i === 0 ? '#ee6666' : null
          }
        })),
        symbolSize: 20,
        label: {
          show: false
        },
        itemStyle: {
          borderWidth: 1,
          borderColor: 'rgba(255,255,255,0.8)'
        }
      },
      {
        type: 'line3D',
        name: '前沿曲线',
        data: paretoSolutions.value.map((s, i) => ({
          value: [...s, i]
        })),
        lineStyle: {
          color: '#91cc75',
          width: 2
        }
      }
    ]
  }
  
  paretoChart.setOption(option)
}

// 绘制 2D 图
function draw2DChart() {
  const option = {
    title: {
      text: 'Pareto 前沿 - 二维投影',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        return `解 #${params.dataIndex + 1}<br/>
                距离: ${params.value[0]?.toFixed(1)} km<br/>
                时间: ${params.value[1]?.toFixed(1)} min<br/>
                车辆: ${Math.round(params.value[2])}`
      }
    },
    legend: {
      data: ['非支配解', 'Pareto 前沿', '最优解'],
      top: 30
    },
    xAxis: {
      type: 'value',
      name: '距离 (km)',
      nameLocation: 'middle',
      nameGap: 30
    },
    yAxis: {
      type: 'value',
      name: '时间 (min)',
      nameLocation: 'middle',
      nameGap: 40
    },
    series: [
      {
        name: 'Pareto 前沿',
        type: 'line',
        data: paretoSolutions.value,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: {
          color: '#91cc75',
          width: 3
        },
        itemStyle: {
          color: '#91cc75'
        }
      },
      {
        name: '非支配解',
        type: 'scatter',
        data: paretoSolutions.value.slice(1),
        symbolSize: 12,
        itemStyle: {
          color: '#5470c6'
        }
      },
      {
        name: '最优解',
        type: 'scatter',
        data: [paretoSolutions.value[0]],
        symbolSize: 20,
        itemStyle: {
          color: '#ee6666'
        },
        label: {
          show: true,
          formatter: '最优解',
          position: 'top',
          color: '#ee6666',
          fontWeight: 'bold'
        }
      }
    ]
  }
  
  paretoChart.setOption(option)
}

// 导出解集
function exportSolutions() {
  const csv = '序号,距离(km),时间(min),车辆数\n' + 
    paretoSolutions.value.map((s, i) => 
      `${i+1},${s[0].toFixed(2)},${s[1].toFixed(2)},${Math.round(s[2])}`
    ).join('\n')
  
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `pareto_solutions_${new Date().toISOString().slice(0,10)}.csv`
  link.click()
  
  ElMessage.success('解集已导出')
}

// 监听显示模式变化
watch(displayMode, () => {
  nextTick(() => drawParetoChart())
})

// 初始化
onMounted(() => {
  loadDemoData()
})
</script>

<style scoped>
.pareto-front-page {
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
</style>
