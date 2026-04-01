<template>
  <el-card class="oil-price-card" v-loading="loading">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon class="icon"><Coin /></el-icon>
          <span class="title">实时油价</span>
        </div>
        <div class="header-right">
          <el-select v-model="selectedProvince" size="small" style="width: 100px" @change="fetchPrices">
            <el-option v-for="p in provinces" :key="p" :label="p" :value="p" />
          </el-select>
          <el-button type="primary" link size="small" @click="refreshData" :loading="refreshing">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </div>
    </template>

    <div class="price-list">
      <div 
        v-for="item in priceItems" 
        :key="item.code" 
        class="price-item"
        :class="{ 'selected': selectedFuel === item.code }"
        @click="selectedFuel = item.code"
      >
        <div class="fuel-icon" :style="{ background: item.color }">
          {{ item.icon }}
        </div>
        <div class="fuel-info">
          <div class="fuel-name">{{ item.name }}</div>
          <div class="fuel-price">
            <span class="price-value">{{ item.price }}</span>
            <span class="price-unit">元/升</span>
          </div>
        </div>
        <el-icon v-if="selectedFuel === item.code" class="check-icon"><Check /></el-icon>
      </div>
    </div>

    <div class="update-info">
      <el-icon><Clock /></el-icon>
      <span>更新时间：{{ updateTime }}</span>
      <el-tag size="small" :type="dataSource === 'tianapi' ? 'success' : 'info'">
        {{ dataSource === 'tianapi' ? '实时数据' : '参考数据' }}
      </el-tag>
    </div>

    <!-- 油价趋势图 -->
    <div class="trend-chart" v-if="showTrend">
      <div class="trend-header">
        <span>近30天趋势</span>
        <el-button type="primary" link size="small" @click="showTrend = false">收起</el-button>
      </div>
      <div ref="chartRef" class="chart-container"></div>
    </div>
    <div class="trend-toggle" v-else @click="showTrend = true">
      <el-icon><TrendCharts /></el-icon>
      <span>查看趋势</span>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { Coin, Refresh, Check, Clock, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { getCurrentPrices, getPriceHistory, getProvinces, refreshCache } from '@/api/oilPrice'

const loading = ref(false)
const refreshing = ref(false)
const showTrend = ref(false)
const chartRef = ref(null)
const chart = ref(null)

const selectedProvince = ref('湖北')
const selectedFuel = ref('0') // 默认选择柴油
const provinces = ref(['北京', '上海', '广东', '湖北', '江苏', '浙江', '山东', '四川'])

const priceData = ref({
  '92': 7.65,
  '95': 8.18,
  '98': 9.98,
  '0': 7.29
})

const updateTime = ref('')
const dataSource = ref('tianapi')

const priceItems = computed(() => [
  { 
    code: '92', 
    name: '92号汽油', 
    price: priceData.value['92'], 
    icon: '92',
    color: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  },
  { 
    code: '95', 
    name: '95号汽油', 
    price: priceData.value['95'], 
    icon: '95',
    color: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
  },
  { 
    code: '98', 
    name: '98号汽油', 
    price: priceData.value['98'], 
    icon: '98',
    color: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'
  },
  { 
    code: '0', 
    name: '0号柴油', 
    price: priceData.value['0'], 
    icon: '柴',
    color: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
  }
])

// 获取当前油价
async function fetchPrices() {
  loading.value = true
  try {
    const res = await getCurrentPrices(selectedProvince.value)
    if (res.success && res.data) {
      // 兼容新的数据格式
      const prices = res.data.prices || res.data
      priceData.value = {
        '92': prices['92']?.price || prices['92'] || 7.82,
        '95': prices['95']?.price || prices['95'] || 8.33,
        '98': prices['98']?.price || prices['98'] || 9.50,
        '0': prices['0']?.price || prices['0'] || 7.45
      }
      updateTime.value = res.data.update_time || '刚刚'
      dataSource.value = prices['0']?.source || res.data.source || 'simulated'
    }
  } catch (error) {
    console.error('获取油价失败:', error)
    // 使用默认值
    priceData.value = {
      '92': 7.82,
      '95': 8.33,
      '98': 9.50,
      '0': 7.45
    }
  } finally {
    loading.value = false
  }
}

// 刷新数据
async function refreshData() {
  refreshing.value = true
  try {
    await refreshCache()
    await fetchPrices()
    ElMessage.success('油价已刷新')
  } catch (error) {
    console.error('刷新失败:', error)
  } finally {
    refreshing.value = false
  }
}

// 获取省份列表
async function fetchProvinces() {
  try {
    const res = await getProvinces()
    if (res.success) {
      provinces.value = res.data
    }
  } catch (error) {
    console.error('获取省份失败:', error)
  }
}

// 初始化趋势图
async function initChart() {
  if (!chartRef.value) return
  
  await nextTick()
  
  if (chart.value) {
    chart.value.dispose()
  }
  
  chart.value = echarts.init(chartRef.value)
  
  try {
    const res = await getPriceHistory(selectedProvince.value, 30)
    if (res.success && res.data && res.data.length > 0) {
      // 兼容新的数据格式
      const dates = res.data.map(d => d.date?.substring(5) || d.date)
      const p0 = res.data.map(d => d.price || d.p0 || 7.5)
      const p92 = res.data.map(d => (d.price || 7.8) + 0.35) // 模拟92号
      const p95 = res.data.map(d => (d.price || 8.0) + 0.85) // 模拟95号
      
      chart.value.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            let result = params[0].axisValue + '<br/>'
            params.forEach(p => {
              result += `${p.marker} ${p.seriesName}: ¥${p.value.toFixed(2)}/升<br/>`
            })
            return result
          }
        },
        legend: {
          data: ['92号汽油', '95号汽油', '0号柴油'],
          bottom: 0,
          textStyle: { fontSize: 10 }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '5%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: dates,
          axisLabel: { fontSize: 10, rotate: 45 }
        },
        yAxis: {
          type: 'value',
          axisLabel: { fontSize: 10, formatter: '¥{value}' }
        },
        series: [
          {
            name: '92号汽油',
            type: 'line',
            data: p92,
            smooth: true,
            lineStyle: { width: 2 },
            itemStyle: { color: '#667eea' }
          },
          {
            name: '95号汽油',
            type: 'line',
            data: p95,
            smooth: true,
            lineStyle: { width: 2 },
            itemStyle: { color: '#f5576c' }
          },
          {
            name: '0号柴油',
            type: 'line',
            data: p0,
            smooth: true,
            lineStyle: { width: 2 },
            itemStyle: { color: '#43e97b' }
          }
        ]
      })
    }
  } catch (error) {
    console.error('获取趋势失败:', error)
    // 显示空图表
    chart.value.setOption({
      title: {
        text: '暂无趋势数据',
        left: 'center',
        top: 'center',
        textStyle: { color: '#999', fontSize: 14 }
      }
    })
  }
}

// 监听显示趋势
watch(showTrend, (val) => {
  if (val) {
    nextTick(() => {
      initChart()
    })
  }
})

// 监听省份变化
watch(selectedProvince, () => {
  if (showTrend.value) {
    initChart()
  }
})

// 暴露选中的油价
defineExpose({
  selectedFuel,
  selectedProvince,
  priceData,
  getCurrentPrice: () => priceData.value[selectedFuel.value]
})

onMounted(() => {
  fetchPrices()
  fetchProvinces()
})
</script>

<style scoped>
.oil-price-card {
  border-radius: 12px;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-left .icon {
  font-size: 24px;
  color: #409eff;
}

.header-left .title {
  font-size: 16px;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.price-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.price-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-radius: 10px;
  background: #f8f9fa;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
}

.price-item:hover {
  background: #e9ecef;
  transform: translateY(-2px);
}

.price-item.selected {
  background: #e3f2fd;
  border: 2px solid #409eff;
}

.fuel-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  color: white;
  margin-right: 12px;
}

.fuel-info {
  flex: 1;
}

.fuel-name {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.fuel-price {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.price-value {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}

.price-unit {
  font-size: 10px;
  color: #999;
}

.check-icon {
  position: absolute;
  right: 8px;
  top: 8px;
  color: #409eff;
}

.update-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #999;
  margin-bottom: 12px;
}

.trend-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px;
  background: #f0f9ff;
  border-radius: 8px;
  cursor: pointer;
  color: #409eff;
  font-size: 13px;
}

.trend-toggle:hover {
  background: #e0f2fe;
}

.trend-chart {
  margin-top: 12px;
}

.trend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: #666;
}

.chart-container {
  height: 200px;
  width: 100%;
}
</style>
