<template>
  <div class="dc-page">
    <h2 class="page-title">📊 数据采集中心</h2>

    <!-- 数据源状态概览 -->
    <div class="source-cards">
      <div class="source-card" v-for="source in sources" :key="source.name">
        <div class="source-icon">{{ source.icon }}</div>
        <div class="source-info">
          <div class="source-name">{{ source.name }}</div>
          <div class="source-status" :class="source.status">
            {{ source.status === 'available' ? '✅ 可用' : '❌ 不可用' }}
          </div>
          <div class="source-type">{{ source.type }}</div>
        </div>
      </div>
    </div>

    <!-- 功能 Tab -->
    <el-tabs v-model="activeTab" class="func-tabs" type="border-card">
      <!-- 天气查询 -->
      <el-tab-pane label="🌤️ 天气查询" name="weather">
        <div class="query-bar">
          <el-input v-model="weatherCity" placeholder="输入城市名称" style="width: 260px"
            @keyup.enter="fetchWeather" clearable>
            <template #prefix>📍</template>
          </el-input>
          <el-button type="primary" @click="fetchWeather" :loading="weatherLoading">查询天气</el-button>
          <div class="quick-cities">
            <el-tag v-for="city in quickCities" :key="city" size="small" effect="plain"
              @click="weatherCity = city; fetchWeather()" class="city-tag">{{ city }}</el-tag>
          </div>
        </div>
        <div v-if="weatherData" class="weather-result">
          <div class="weather-current">
            <div class="weather-main">
              <div class="weather-city">{{ weatherData.city }}</div>
              <div class="weather-temp">{{ weatherData.temperature }}°C</div>
              <div class="weather-desc">{{ weatherData.weather }}</div>
            </div>
            <div class="weather-details">
              <div class="detail-item"><span class="detail-label">🌬️ 风向</span><span class="detail-value">{{ weatherData.windDirection }} {{ weatherData.windPower }}</span></div>
              <div class="detail-item"><span class="detail-label">💧 湿度</span><span class="detail-value">{{ weatherData.humidity }}</span></div>
              <div class="detail-item"><span class="detail-label">🌡️ 温度范围</span><span class="detail-value">{{ weatherData.tempRange }}</span></div>
            </div>
          </div>
          <div v-if="weatherData.forecast?.length" class="weather-forecast">
            <h4>📅 未来预报</h4>
            <div class="forecast-list">
              <div class="forecast-item" v-for="(day, i) in weatherData.forecast" :key="i">
                <div class="forecast-date">{{ day.date }}</div>
                <div class="forecast-weather">{{ day.weather }}</div>
                <div class="forecast-temp">{{ day.tempRange }}</div>
                <div class="forecast-wind">{{ day.wind }}</div>
              </div>
            </div>
          </div>
        </div>
        <el-empty v-else-if="weatherSearched && !weatherLoading" description="暂无天气数据" />
      </el-tab-pane>

      <!-- 油价查询 -->
      <el-tab-pane label="⛽ 油价查询" name="oil">
        <div class="query-bar">
          <el-button type="primary" @click="fetchOilPrices" :loading="oilLoading">🔄 刷新全国油价</el-button>
          <el-input v-model="oilSearch" placeholder="搜索省份..." style="width: 200px" clearable>
            <template #prefix>🔍</template>
          </el-input>
          <span class="data-source-tag">📊 {{ oilSource }}</span>
        </div>
        <div v-if="oilList.length" class="oil-table-wrap">
          <el-table :data="filteredOilList" stripe style="width: 100%"
            :header-cell-style="{ background: '#0d1b2a', color: '#00d4ff', borderColor: '#1b2838' }"
            :cell-style="{ borderColor: '#1b2838' }">
            <el-table-column prop="province" label="📍 省份" width="120" />
            <el-table-column prop="p92" label="92#汽油" align="center"><template #default="{ row }"><span class="oil-price">¥{{ row.p92 }}</span></template></el-table-column>
            <el-table-column prop="p95" label="95#汽油" align="center"><template #default="{ row }"><span class="oil-price">¥{{ row.p95 }}</span></template></el-table-column>
            <el-table-column prop="p98" label="98#汽油" align="center"><template #default="{ row }"><span class="oil-price">¥{{ row.p98 }}</span></template></el-table-column>
            <el-table-column prop="p0" label="0#柴油" align="center"><template #default="{ row }"><span class="oil-price diesel">¥{{ row.p0 }}</span></template></el-table-column>
          </el-table>
          <div class="oil-summary">共 {{ oilList.length }} 个省份<span v-if="oilSearch">，筛选出 {{ filteredOilList.length }} 个</span></div>
        </div>
        <el-empty v-else-if="oilSearched && !oilLoading" description="暂无油价数据" />
      </el-tab-pane>

      <!-- 路况查询 -->
      <el-tab-pane label="🚗 路况查询" name="traffic">
        <div class="query-bar">
          <el-select v-model="trafficCity" style="width: 160px" @change="fetchTraffic">
            <el-option v-for="city in trafficCities" :key="city" :label="city" :value="city" />
          </el-select>
          <el-button type="primary" @click="fetchTraffic" :loading="trafficLoading">查询路况</el-button>
          <span class="data-source-tag">📊 高德地图API</span>
        </div>
        <div v-if="trafficInfo" class="traffic-result">
          <div class="traffic-overview">
            <div class="traffic-metric"><div class="metric-label">🟢 畅通</div><div class="metric-value green">{{ trafficInfo.smooth }}</div></div>
            <div class="traffic-metric"><div class="metric-label">🟡 缓行</div><div class="metric-value yellow">{{ trafficInfo.slow }}</div></div>
            <div class="traffic-metric"><div class="metric-label">🟠 拥堵</div><div class="metric-value orange">{{ trafficInfo.congested }}</div></div>
            <div class="traffic-metric"><div class="metric-label">🔴 严重</div><div class="metric-value red">{{ trafficInfo.blocked }}</div></div>
          </div>
          <div v-if="trafficInfo.roads?.length" class="traffic-roads">
            <h4>📋 路段详情</h4>
            <div class="road-list">
              <div class="road-item" v-for="(road, i) in trafficInfo.roads.slice(0, 10)" :key="i">
                <span class="road-name">{{ road.name }}</span>
                <span class="road-status" :class="road.statusClass">{{ road.status }}</span>
              </div>
            </div>
          </div>
          <div v-if="trafficInfo.evaluation" class="traffic-eval"><p>{{ trafficInfo.evaluation }}</p></div>
        </div>
        <el-empty v-else-if="trafficSearched && !trafficLoading" description="暂无路况数据" />
      </el-tab-pane>

      <!-- 快递比价 -->
      <el-tab-pane label="📦 快递比价" name="express">
        <div class="query-bar">
          <el-input v-model="express.origin" placeholder="寄件城市" style="width: 140px" clearable>
            <template #prefix>📤</template>
          </el-input>
          <span class="arrow-icon">➡️</span>
          <el-input v-model="express.destination" placeholder="收件城市" style="width: 140px" clearable>
            <template #prefix>📥</template>
          </el-input>
          <el-input-number v-model="express.weight" :min="0.1" :max="50" :step="0.5" style="width: 140px" />
          <span style="color: #888; font-size: 13px">kg</span>
          <el-select v-model="express.priority" style="width: 120px">
            <el-option label="💰 最便宜" value="price" />
            <el-option label="🚀 最快" value="speed" />
            <el-option label="⚖️ 均衡" value="balanced" />
          </el-select>
          <el-button type="primary" @click="fetchExpressCompare" :loading="expressLoading">
            🔍 对比价格
          </el-button>
          <div class="quick-routes">
            <el-tag size="small" effect="plain" @click="setRoute('北京','上海')" class="city-tag">北京→上海</el-tag>
            <el-tag size="small" effect="plain" @click="setRoute('广州','北京')" class="city-tag">广州→北京</el-tag>
            <el-tag size="small" effect="plain" @click="setRoute('深圳','成都')" class="city-tag">深圳→成都</el-tag>
          </div>
        </div>

        <!-- 对比结果 -->
        <div v-if="expressResults.length" class="express-result">
          <!-- 最优推荐卡片 -->
          <div class="recommend-card">
            <div class="recommend-badge">🏆 {{ priorityLabel }}推荐</div>
            <div class="recommend-content" v-if="recommendResult">
              <div class="recommend-company">{{ recommendResult.company }}</div>
              <div class="recommend-price">¥{{ recommendResult.total_price }}</div>
              <div class="recommend-detail">{{ recommendResult.delivery_days }}天送达 · {{ recommendResult.weight_limit || express.weight }}kg以内</div>
            </div>
          </div>

          <!-- 全部对比列表 -->
          <div class="express-list">
            <div class="express-item" v-for="(item, i) in expressResults" :key="i">
              <div class="express-rank" :class="{ 'rank-1': i === 0, 'rank-2': i === 1, 'rank-3': i === 2 }">
                {{ i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '#' + (i+1) }}
              </div>
              <div class="express-company">
                <div class="company-name">{{ item.company }}</div>
                <div class="company-detail">{{ item.delivery_days }}天 · 基础运费¥{{ item.base_price }}</div>
              </div>
              <div class="express-price">¥{{ item.total_price }}</div>
              <div class="express-tag" v-if="recommendResult?.company === item.company">推荐</div>
            </div>
          </div>
          <div class="express-summary">共 {{ expressResults.length }} 家快递公司参与对比</div>
        </div>
        <el-empty v-else-if="expressSearched && !expressLoading" description="暂无比价结果" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDataSourceStatus, getCityWeather, getOilPrices, getCityTraffic, compareExpressPrices } from '@/api/dataCollection'

const activeTab = ref('weather')

// === 数据源状态 ===
const sources = ref([
  { name: '油价数据', icon: '⛽', status: 'available', type: '模拟数据' },
  { name: '天气数据', icon: '🌤️', status: 'available', type: '高德API' },
  { name: '路况数据', icon: '🚗', status: 'available', type: '高德API' },
  { name: '快递价格', icon: '📦', status: 'available', type: '模拟数据' }
])

// === 天气 ===
const weatherCity = ref('北京')
const weatherLoading = ref(false)
const weatherSearched = ref(false)
const weatherData = ref(null)
const quickCities = ['北京', '上海', '广州', '深圳', '成都', '武汉']

// === 油价 ===
const oilLoading = ref(false)
const oilSearched = ref(false)
const oilList = ref([])
const oilSearch = ref('')
const oilSource = ref('加载中...')
const filteredOilList = computed(() => {
  if (!oilSearch.value) return oilList.value
  return oilList.value.filter(item => item.province.includes(oilSearch.value))
})

// === 路况 ===
const trafficCity = ref('北京')
const trafficLoading = ref(false)
const trafficSearched = ref(false)
const trafficInfo = ref(null)
const trafficCities = ['北京', '上海', '广州', '深圳', '杭州', '成都', '武汉', '南京', '重庆', '西安']

// === 快递比价 ===
const express = ref({ origin: '北京', destination: '上海', weight: 1, priority: 'balanced' })
const expressLoading = ref(false)
const expressSearched = ref(false)
const expressResults = ref([])
const recommendResult = computed(() => expressResults.value.find(r => r.is_recommended) || expressResults.value[0] || null)
const priorityLabel = computed(() => ({ price: '最便宜', speed: '最快', balanced: '均衡' }[express.value.priority] || '最优'))

function setRoute(from, to) {
  express.value.origin = from
  express.value.destination = to
}

// === 方法 ===
async function loadStatus() {
  try {
    const res = await getDataSourceStatus()
    if (res.success && res.sources) {
      const iconMap = { '油价数据': '⛽', '天气数据': '🌤️', '路况数据': '🚗', '快递价格': '📦' }
      sources.value = res.sources.map(s => ({ ...s, icon: iconMap[s.name] || '📡' }))
    }
  } catch (e) { /* 静默 */ }
}

async function fetchWeather() {
  const city = weatherCity.value.trim()
  if (!city) { ElMessage.warning('请输入城市名称'); return }
  weatherLoading.value = true; weatherSearched.value = true
  try {
    const res = await getCityWeather(city)
    if (res.success) {
      const lives = res.lives || res.data?.lives || []
      const forecasts = res.forecasts || res.data?.forecasts || []
      const live = lives[0] || {}
      weatherData.value = {
        city, weather: live.weather || '未知', temperature: live.temperature || '--',
        windDirection: live.winddirection || '--', windPower: live.windpower || '--',
        humidity: live.humidity || '--',
        tempRange: `${live.temperature_low || '--'}°C ~ ${live.temperature_high || '--'}°C`,
        forecast: forecasts.map(f => ({
          date: f.date, weather: f.dayweather || '--',
          tempRange: `${f.nighttemp || '--'}°C ~ ${f.daytemp || '--'}°C`,
          wind: `${f.daywind || '--'} ${f.daypower || ''}`
        }))
      }
    } else { ElMessage.error(res.error || '查询失败') }
  } catch (e) { ElMessage.error('天气查询失败') }
  finally { weatherLoading.value = false }
}

async function fetchOilPrices() {
  oilLoading.value = true; oilSearched.value = true
  try {
    const res = await getOilPrices()
    if (res.success) { oilList.value = res.data?.list || []; oilSource.value = res.source || '模拟数据' }
    else { ElMessage.error(res.error || '获取失败') }
  } catch (e) { ElMessage.error('油价查询失败') }
  finally { oilLoading.value = false }
}

async function fetchTraffic() {
  trafficLoading.value = true; trafficSearched.value = true
  try {
    const res = await getCityTraffic(trafficCity.value)
    if (res.success) {
      const info = res.trafficinfo || {}
      const ev = info.evaluation || {}
      trafficInfo.value = {
        smooth: ev.expedite || '0%', slow: ev.congested || '0%',
        congested: ev.slow || '0%', blocked: ev.blocked || '0%',
        evaluation: `畅通指数：${ev.expedite || '--'}，平均速度：${info.speed || '--'}km/h`,
        roads: (info.roads || []).map(r => ({
          name: r.name || '未知路段', status: r.status || '未知',
          statusClass: { '畅通': 'st-smooth', '缓行': 'st-slow', '拥堵': 'st-congested', '严重拥堵': 'st-blocked' }[r.status] || 'st-unknown'
        }))
      }
    } else { ElMessage.error(res.error || '查询失败') }
  } catch (e) { ElMessage.error('路况查询失败') }
  finally { trafficLoading.value = false }
}

async function fetchExpressCompare() {
  const { origin, destination, weight } = express.value
  if (!origin || !destination) { ElMessage.warning('请填写寄件和收件城市'); return }
  expressLoading.value = true; expressSearched.value = true
  try {
    const res = await compareExpressPrices(origin, destination, weight)
    if (res.success) { expressResults.value = res.results || [] }
    else { ElMessage.error(res.error || '对比失败') }
  } catch (e) { ElMessage.error('快递比价失败') }
  finally { expressLoading.value = false }
}

onMounted(() => { loadStatus() })
</script>

<style scoped>
.dc-page {
  padding: 24px;
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0e1a 0%, #0d1b2a 40%, #1b2838 100%);
  position: relative;
}

.dc-page::before {
  content: '';
  position: fixed;
  top: -50%; left: -50%;
  width: 200%; height: 200%;
  background: radial-gradient(circle at 30% 20%, rgba(0, 212, 255, 0.03) 0%, transparent 50%),
              radial-gradient(circle at 80% 80%, rgba(0, 255, 136, 0.02) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
}

.dc-page > * { position: relative; z-index: 1; }

.page-title { color: #00d4ff; margin-bottom: 24px; font-size: 22px; text-shadow: 0 0 20px rgba(0,212,255,0.3); }

/* 数据源卡片 */
.source-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }
.source-card {
  background: rgba(13, 27, 42, 0.8); backdrop-filter: blur(10px);
  border-radius: 14px; padding: 20px;
  display: flex; align-items: center; gap: 16px;
  border: 1px solid rgba(0, 212, 255, 0.12);
  transition: all 0.3s ease;
}
.source-card:hover { border-color: rgba(0, 212, 255, 0.4); transform: translateY(-2px); box-shadow: 0 8px 32px rgba(0,0,0,0.3); }
.source-icon { font-size: 32px; }
.source-name { color: #e8e8e8; font-size: 14px; font-weight: 600; }
.source-status.available { color: #00ff88; font-size: 12px; }
.source-status.unavailable { color: #ff4757; font-size: 12px; }
.source-type { color: #666; font-size: 11px; }

/* Tab 样式 */
.func-tabs {
  background: rgba(13, 27, 42, 0.8); backdrop-filter: blur(10px);
  border-radius: 14px; border: 1px solid rgba(0,212,255,0.1);
}
.func-tabs :deep(.el-tabs__header) { background: rgba(0,0,0,0.2); border-radius: 14px 14px 0 0; border: none; }
.func-tabs :deep(.el-tabs__item) { color: #888; font-size: 14px; }
.func-tabs :deep(.el-tabs__item.is-active) { color: #00d4ff; font-weight: 600; }
.func-tabs :deep(.el-tabs__item:hover) { color: #aaa; }
.func-tabs :deep(.el-tabs__content) { padding: 24px; color: #ddd; }

/* 查询栏 */
.query-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.quick-cities { display: flex; align-items: center; gap: 4px; }
.quick-routes { display: flex; align-items: center; gap: 4px; }
.city-tag { cursor: pointer !important; margin-right: 2px; transition: all 0.2s; }
.city-tag:hover { color: #00d4ff !important; border-color: #00d4ff !important; }
.arrow-icon { font-size: 18px; }
.data-source-tag { background: rgba(0,212,255,0.08); padding: 4px 14px; border-radius: 20px; font-size: 12px; color: #00d4ff; border: 1px solid rgba(0,212,255,0.15); }

/* 天气 */
.weather-result { animation: fadeUp 0.4s ease; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
.weather-current {
  background: linear-gradient(135deg, rgba(0,100,200,0.15) 0%, rgba(0,212,255,0.08) 100%);
  border-radius: 14px; padding: 28px; margin-bottom: 20px;
  display: flex; justify-content: space-between; align-items: center;
  border: 1px solid rgba(0,212,255,0.12);
}
.weather-city { font-size: 18px; color: #00d4ff; margin-bottom: 8px; }
.weather-temp { font-size: 52px; font-weight: 700; color: #fff; line-height: 1.1; margin-bottom: 4px; text-shadow: 0 0 30px rgba(255,255,255,0.1); }
.weather-desc { font-size: 16px; color: #aaa; }
.weather-details { display: flex; flex-direction: column; gap: 12px; }
.detail-item { display: flex; justify-content: space-between; gap: 24px; font-size: 14px; padding: 6px 12px; background: rgba(0,0,0,0.15); border-radius: 8px; }
.detail-label { color: #888; }
.detail-value { color: #e8e8e8; }
.weather-forecast h4 { color: #00d4ff; margin-bottom: 12px; font-size: 15px; }
.forecast-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 10px; }
.forecast-item { background: rgba(0,0,0,0.2); border-radius: 10px; padding: 14px 10px; text-align: center; border: 1px solid rgba(255,255,255,0.03); transition: all 0.2s; }
.forecast-item:hover { border-color: rgba(0,212,255,0.2); }
.forecast-date { color: #00d4ff; font-size: 12px; margin-bottom: 4px; }
.forecast-weather { color: #fff; font-size: 14px; margin-bottom: 4px; }
.forecast-temp { color: #ff6b6b; font-size: 13px; margin-bottom: 2px; }
.forecast-wind { color: #666; font-size: 11px; }

/* 油价 */
.oil-table-wrap { animation: fadeUp 0.4s ease; }
.oil-table-wrap :deep(.el-table) { background: transparent; --el-table-bg-color: transparent; --el-table-tr-bg-color: rgba(0,0,0,0.15); --el-table-row-hover-bg-color: rgba(0,212,255,0.06); --el-table-border-color: rgba(255,255,255,0.05); --el-table-text-color: #ccc; --el-table-header-bg-color: rgba(0,0,0,0.3); --el-table-header-text-color: #00d4ff; }
.oil-price { color: #ffa502; font-weight: 700; font-size: 15px; }
.oil-price.diesel { color: #2ed573; }
.oil-summary { margin-top: 12px; color: #666; font-size: 13px; display: flex; gap: 16px; }

/* 路况 */
.traffic-result { animation: fadeUp 0.4s ease; }
.traffic-overview { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
.traffic-metric { background: rgba(0,0,0,0.2); border-radius: 12px; padding: 18px; text-align: center; border: 1px solid rgba(255,255,255,0.04); }
.metric-label { color: #888; font-size: 13px; margin-bottom: 8px; }
.metric-value { font-size: 26px; font-weight: 700; }
.metric-value.green { color: #2ed573; } .metric-value.yellow { color: #ffa502; }
.metric-value.orange { color: #ff6348; } .metric-value.red { color: #ff4757; }
.traffic-roads h4 { color: #00d4ff; margin-bottom: 12px; }
.road-list { display: flex; flex-direction: column; gap: 8px; }
.road-item { display: flex; justify-content: space-between; background: rgba(0,0,0,0.15); padding: 10px 16px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.03); }
.road-name { color: #ccc; font-size: 14px; }
.road-status { font-size: 12px; padding: 3px 12px; border-radius: 12px; font-weight: 600; }
.st-smooth { background: rgba(46,213,115,0.12); color: #2ed573; } .st-slow { background: rgba(255,165,2,0.12); color: #ffa502; }
.st-congested { background: rgba(255,99,72,0.12); color: #ff6348; } .st-blocked { background: rgba(255,71,87,0.12); color: #ff4757; }
.st-unknown { background: rgba(255,255,255,0.08); color: #888; }
.traffic-eval p { color: #888; font-size: 13px; line-height: 1.8; background: rgba(0,0,0,0.15); padding: 12px 16px; border-radius: 8px; }

/* 快递比价 */
.express-result { animation: fadeUp 0.4s ease; }
.recommend-card {
  background: linear-gradient(135deg, rgba(0,212,255,0.1) 0%, rgba(0,255,136,0.05) 100%);
  border-radius: 14px; padding: 24px; margin-bottom: 20px;
  border: 1px solid rgba(0,212,255,0.2);
  display: flex; align-items: center; gap: 20px;
}
.recommend-badge { background: linear-gradient(135deg, #ffa502, #ff6348); color: #fff; font-size: 14px; font-weight: 700; padding: 8px 16px; border-radius: 10px; white-space: nowrap; }
.recommend-company { font-size: 18px; color: #fff; font-weight: 600; margin-bottom: 4px; }
.recommend-price { font-size: 32px; color: #2ed573; font-weight: 700; margin-bottom: 2px; }
.recommend-detail { color: #888; font-size: 13px; }
.express-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.express-item {
  display: flex; align-items: center; gap: 14px;
  background: rgba(0,0,0,0.15); padding: 14px 18px; border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.03); transition: all 0.2s;
}
.express-item:hover { border-color: rgba(0,212,255,0.15); background: rgba(0,0,0,0.2); }
.express-rank { font-size: 18px; width: 36px; text-align: center; }
.rank-1 { filter: drop-shadow(0 0 6px rgba(255,215,0,0.5)); }
.express-company { flex: 1; }
.company-name { color: #e8e8e8; font-size: 14px; font-weight: 600; margin-bottom: 2px; }
.company-detail { color: #666; font-size: 12px; }
.express-price { font-size: 20px; font-weight: 700; color: #ffa502; }
.express-tag { background: rgba(0,212,255,0.12); color: #00d4ff; font-size: 11px; padding: 2px 10px; border-radius: 10px; font-weight: 600; }
.express-summary { color: #666; font-size: 13px; }
</style>
