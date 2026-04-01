<template>
  <div class="multi-objective-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>🎯 多目标路径优化</h1>
      <p class="subtitle">智能平衡距离、时间、成本、路况和天气风险</p>
    </div>
    
    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：起终点选择 -->
      <div class="left-panel">
        <el-card class="location-card">
          <template #header>
            <div class="card-header">
              <span>📍 起终点选择</span>
            </div>
          </template>
          
          <el-form label-width="60px">
            <el-form-item label="起点">
              <el-select
                v-model="originId"
                placeholder="选择起点"
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="node in nodes"
                  :key="node.id"
                  :label="node.name"
                  :value="node.id"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="终点">
              <el-select
                v-model="destinationId"
                placeholder="选择终点"
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="node in nodes"
                  :key="node.id"
                  :label="node.name"
                  :value="node.id"
                />
              </el-select>
            </el-form-item>
          </el-form>
        </el-card>
        
        <!-- 多目标优化面板 -->
        <MultiObjectivePanel
          :origin-id="originId"
          :destination-id="destinationId"
          @result="handleResult"
          @select="handleSelectRoute"
        />
      </div>
      
      <!-- 右侧：可视化对比 -->
      <div class="right-panel">
        <el-card v-if="result">
          <RouteCompareChart
            :routes="result.recommendations"
            :selected-indices="selectedIndices"
          />
        </el-card>
        
        <el-empty v-else description="请选择起终点并开始优化" />
      </div>
    </div>
    
    <!-- 底部：地图预览 -->
    <div v-if="selectedRoute" class="map-preview">
      <el-card>
        <template #header>
          <span>🗺️ 路线预览</span>
        </template>
        <div ref="mapRef" class="map-container"></div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import MultiObjectivePanel from '../components/MultiObjectivePanel.vue'
import RouteCompareChart from '../components/RouteCompareChart.vue'
import { getAllNodes } from '../api/nodes'
import * as echarts from 'echarts'

// 状态
const nodes = ref([])
const originId = ref(null)
const destinationId = ref(null)
const result = ref(null)
const selectedRoute = ref(null)
const selectedIndices = ref([])
const mapRef = ref(null)
let mapChart = null

// 获取节点列表
async function fetchNodes() {
  try {
    const res = await getAllNodes()
    // 后端返回 { nodes: [...] }
    nodes.value = res.nodes || []
  } catch (error) {
    console.error('获取节点失败:', error)
  }
}

// 处理优化结果
function handleResult(res) {
  result.value = res
  selectedIndices.value = []
}

// 选择路线
function handleSelectRoute(route) {
  selectedRoute.value = route
  nextTick(() => {
    renderMap(route)
  })
}

// 渲染地图
function renderMap(route) {
  if (!mapRef.value || !route?.path?.length) return
  
  if (mapChart) {
    mapChart.dispose()
  }
  
  mapChart = echarts.init(mapRef.value)
  
  // 提取路径坐标
  const pathCoords = route.path.map(node => [
    node.longitude || node.lng || 116.4,
    node.latitude || node.lat || 39.9
  ])
  
  const option = {
    backgroundColor: 'transparent',
    geo: {
      map: 'china',
      roam: true,
      zoom: 5,
      center: pathCoords[0] || [116.4, 39.9],
      itemStyle: {
        areaColor: '#f3f3f3',
        borderColor: '#999'
      },
      emphasis: {
        itemStyle: {
          areaColor: '#e0e0e0'
        }
      }
    },
    series: [
      {
        type: 'lines',
        coordinateSystem: 'geo',
        data: [{
          coords: pathCoords,
          lineStyle: {
            color: '#409EFF',
            width: 3,
            curveness: 0.2
          }
        }],
        effect: {
          show: true,
          period: 4,
          trailLength: 0.2,
          color: '#F56C6C',
          symbolSize: 8
        }
      },
      {
        type: 'scatter',
        coordinateSystem: 'geo',
        data: pathCoords.map((coord, i) => ({
          name: route.path[i]?.name || `节点${i + 1}`,
          value: coord,
          itemStyle: {
            color: i === 0 ? '#67C23A' : (i === pathCoords.length - 1 ? '#F56C6C' : '#409EFF')
          }
        })),
        symbolSize: 12,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}'
        }
      }
    ]
  }
  
  mapChart.setOption(option)
}

onMounted(() => {
  fetchNodes()
})
</script>

<style scoped>
.multi-objective-page {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
}

.subtitle {
  color: #909399;
  margin: 0;
}

.main-content {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.location-card {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.right-panel {
  min-height: 500px;
}

.map-preview {
  margin-top: 20px;
}

.map-container {
  width: 100%;
  height: 400px;
}

@media (max-width: 1200px) {
  .main-content {
    grid-template-columns: 1fr;
  }
}
</style>
tyle>
