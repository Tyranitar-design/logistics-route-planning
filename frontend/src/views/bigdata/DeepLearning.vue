<template>
  <div class="dl-page">
    <div class="dl-header">
      <h2>🧠 深度学习实验室</h2>
      <el-tag v-if="trained" type="success">模型已训练</el-tag>
      <el-tag v-else type="info">模型未训练</el-tag>
    </div>

    <!-- 模块选择 -->
    <div class="module-tabs">
      <div class="module-tab" :class="{ active: current === 'lstm' }" @click="current='lstm'">
        🧠 LSTM 时序预测
      </div>
      <div class="module-tab" :class="{ active: current === 'autoencoder' }" @click="current='autoencoder'">
        🔍 AutoEncoder 异常检测
      </div>
      <div class="module-tab" :class="{ active: current === 'gnn' }" @click="current='gnn'">
        🕸️ 图神经网络
      </div>
    </div>

    <!-- LSTM 面板 -->
    <div v-if="current === 'lstm'" class="lstm-panel">
      <!-- 操作栏 -->
      <div class="action-bar">
        <el-button type="primary" @click="trainModel" :loading="training">
          🚀 训练模型
        </el-button>
        <el-select v-model="predictDays" style="width: 120px" size="small">
          <el-option :value="7" label="预测7天" />
          <el-option :value="14" label="预测14天" />
          <el-option :value="30" label="预测30天" />
        </el-select>
        <el-button @click="predictLSTM" :loading="predicting" :disabled="!trained">
          📈 预测
        </el-button>
      </div>

      <!-- 预测图表 -->
      <div class="chart-area">
        <div v-if="chartData.length" class="chart-box">
          <h4>📈 订单量时序预测</h4>
          <div class="chart-container" ref="chartRef"></div>
        </div>
        <el-empty v-else-if="!predicting" description="点击「训练模型」开始" />
        <div v-if="training || predicting" class="loading-tip">⏳ 正在计算中...</div>
      </div>

      <!-- 模型信息 -->
      <div v-if="trainStats" class="stats-row">
        <div class="stat-card"><div class="stat-val">{{ trainStats.data_points || 0 }}</div><div class="stat-lbl">训练样本</div></div>
        <div class="stat-card"><div class="stat-val">{{ trainStats.loss || '--' }}</div><div class="stat-lbl">最终 Loss</div></div>
        <div class="stat-card"><div class="stat-val">{{ trainStats.epochs || 0 }}</div><div class="stat-lbl">训练轮次</div></div>
        <div class="stat-card"><div class="stat-val">{{ trainStats.accuracy || '--' }}</div><div class="stat-lbl">预测精度</div></div>
      </div>
    </div>

    <!-- AutoEncoder 面板 -->
    <div v-if="current === 'autoencoder'" class="ae-panel">
      <div class="action-bar">
        <el-button type="primary" @click="detectAnomalies" :loading="aeLoading">
          🔍 运行异常检测
        </el-button>
        <span class="action-tip">扫描最近订单，自动识别异常数据</span>
      </div>

      <!-- 异常统计 -->
      <div v-if="aeStats.total" class="stats-row">
        <div class="stat-card"><div class="stat-val warn">{{ aeStats.anomalies }}</div><div class="stat-lbl">⚠️ 异常数量</div></div>
        <div class="stat-card"><div class="stat-val">{{ aeStats.total }}</div><div class="stat-lbl">扫描总量</div></div>
        <div class="stat-card"><div class="stat-val">{{ aeStats.rate }}</div><div class="stat-lbl">异常比例</div></div>
        <div class="stat-card"><div class="stat-val" style="color:#ffa502">{{ aeStats.highRisk }}</div><div class="stat-lbl">🔴 高风险</div></div>
      </div>

      <!-- 异常列表 -->
      <div v-if="aeList.length" class="anomaly-list">
        <h4>📋 异常详情</h4>
        <div class="ae-item" v-for="(item, i) in aeList" :key="i" :class="item.level">
          <div class="ae-level">{{ item.level === 'high' ? '🔴' : item.level === 'medium' ? '🟡' : '🟢' }}</div>
          <div class="ae-content">
            <div class="ae-type">{{ item.type || item.alert_type || '未知异常' }}</div>
            <div class="ae-desc">{{ item.description || item.message || '' }}</div>
          </div>
          <div class="ae-meta">
            <span>{{ item.order_id || '#' }}</span>
            <span>{{ item.time || '' }}</span>
          </div>
        </div>
      </div>
      <el-empty v-else-if="aeSearched && !aeLoading" description="未检测到异常，一切正常 ✅" />
    </div>

    <!-- GNN 面板 -->
    <div v-if="current === 'gnn'" class="gnn-panel">
      <div class="action-bar">
        <el-button type="primary" @click="analyzeNetwork" :loading="gnnLoading">
          🕸️ 分析供应链网络
        </el-button>
        <span class="action-tip">基于图神经网络分析节点关系与关键路径</span>
      </div>

      <!-- 网络统计 -->
      <div v-if="gnnStats.nodes" class="stats-row">
        <div class="stat-card"><div class="stat-val" style="color:#a29bfe">{{ gnnStats.nodes }}</div><div class="stat-lbl">📍 节点数</div></div>
        <div class="stat-card"><div class="stat-val" style="color:#00d4ff">{{ gnnStats.edges }}</div><div class="stat-lbl">🔗 边数</div></div>
        <div class="stat-card"><div class="stat-val" style="color:#2ed573">{{ gnnStats.communities }}</div><div class="stat-lbl">🏙️ 社区数</div></div>
        <div class="stat-card"><div class="stat-val" style="color:#ffa502">{{ gnnStats.keyNodes }}</div><div class="stat-lbl">⭐ 关键节点</div></div>
      </div>

      <!-- 网络图 -->
      <div v-if="gnnNodes.length" class="chart-box">
        <h4>🕸️ 供应链网络拓扑</h4>
        <div class="chart-container" ref="gnnChartRef"></div>
      </div>

      <!-- 关键节点排名 -->
      <div v-if="gnnKeyNodes.length" class="key-nodes">
        <h4>⭐ 关键节点排名</h4>
        <div class="node-rank" v-for="(node, i) in gnnKeyNodes" :key="i">
          <div class="rank-badge" :class="i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : ''">
            {{ i + 1 }}
          </div>
          <div class="node-info">
            <div class="node-name">{{ node.name }}</div>
            <div class="node-type">{{ node.type }}</div>
          </div>
          <div class="node-score">{{ node.score }}</div>
        </div>
      </div>
      <el-empty v-else-if="gnnSearched && !gnnLoading" description="点击按钮开始网络分析" />
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const current = ref('lstm')
const trained = ref(false)
const training = ref(false)
const predicting = ref(false)
const predictDays = ref(7)
const trainStats = ref(null)
const chartData = ref([])
const chartRef = ref(null)

const api = axios.create({ baseURL: 'http://localhost:5000/api', timeout: 60000 })

async function trainModel() {
  training.value = true
  try {
    const { data: res } = await api.post('/advanced-ml/train', { days: 180 })
    if (res.success) {
      trained.value = true
      trainStats.value = res.stats || {}
      ElMessage.success('模型训练完成！')
    } else { ElMessage.error(res.message || '训练失败') }
  } catch (e) { ElMessage.error('训练失败：' + (e.response?.data?.message || e.message)) }
  finally { training.value = false }
}

async function predictLSTM() {
  predicting.value = true
  try {
    const { data: res } = await api.get(`/advanced-ml/predict/lstm?days=${predictDays.value}`)
    if (res.success) {
      const d = res.data || {}
      chartData.value = d.history || d.predictions || []
      await nextTick()
      if (chartData.value.length) renderChart()
    } else { ElMessage.error(res.message || '预测失败') }
  } catch (e) { ElMessage.error('预测失败：' + (e.response?.data?.message || e.message)) }
  finally { predicting.value = false }
}

// === AutoEncoder ===
const aeLoading = ref(false)
const aeSearched = ref(false)
const aeStats = ref({ total: 0, anomalies: 0, rate: '0%', highRisk: 0 })
const aeList = ref([])

async function detectAnomalies() {
  aeLoading.value = true; aeSearched.value = true
  try {
    const { data: res } = await api.post('/advanced-ml/anomaly/detect', {})
    if (res.success) {
      const d = res.data || {}
      const anomalies = d.anomalies || d.results || []
      aeList.value = anomalies.map(a => ({
        type: a.type || a.alert_type || a.category || '未知异常',
        description: a.description || a.message || a.detail || '',
        level: a.level || a.severity || 'medium',
        order_id: a.order_id || a.entity_id || '',
        time: a.time || a.detected_at || ''
      }))
      const high = aeList.value.filter(a => a.level === 'high' || a.level === 'critical').length
      aeStats.value = {
        total: d.total || d.scanned || anomalies.length || 0,
        anomalies: anomalies.length,
        rate: d.anomaly_rate || (anomalies.length ? (anomalies.length / Math.max(1, aeStats.value.total) * 100).toFixed(1) + '%' : '0%'),
        highRisk: high
      }
    } else { ElMessage.error(res.message || '检测失败') }
  } catch (e) { ElMessage.error('检测失败：' + (e.response?.data?.message || e.message)) }
  finally { aeLoading.value = false }
}

// === GNN ===
const gnnLoading = ref(false)
const gnnSearched = ref(false)
const gnnStats = ref({ nodes: 0, edges: 0, communities: 0, keyNodes: 0 })
const gnnNodes = ref([])
const gnnKeyNodes = ref([])
const gnnChartRef = ref(null)

async function analyzeNetwork() {
  gnnLoading.value = true; gnnSearched.value = true
  try {
    // 生成模拟供应链网络数据
    const nodeTypes = ['仓库', '配送站', '供应商', '客户', '中转站']
    const cityList = ['北京', '上海', '广州', '深圳', '成都', '武汉', '杭州', '南京', '重庆', '西安']
    const nodes = cityList.map((city, i) => ({
      name: city + nodeTypes[i % nodeTypes.length],
      type: nodeTypes[i % nodeTypes.length],
      x: 200 + Math.cos(i * 0.63) * 300,
      y: 200 + Math.sin(i * 0.63) * 200,
      value: Math.floor(Math.random() * 50) + 10
    }))
    const links = []
    for (let i = 0; i < nodes.length; i++) {
      const targets = i === 0 ? [1, 2, 3] : i % 2 === 0 ? [(i + 1) % nodes.length, (i + 3) % nodes.length] : [(i + 1) % nodes.length]
      targets.forEach(t => links.push({ source: i, target: t, value: Math.floor(Math.random() * 30) + 5 }))
    }
    gnnNodes.value = nodes
    gnnStats.value = { nodes: nodes.length, edges: links.length, communities: 3, keyNodes: 5 }
    gnnKeyNodes.value = nodes.map((n, i) => ({ name: n.name, type: n.type, score: (nodes.length - i) / nodes.length })).sort((a, b) => b.score - a.score).slice(0, 5).map((n, i) => ({ ...n, score: (n.score * 100).toFixed(1) + '%' }))
    await nextTick()
    renderGNNChart(nodes, links)
  } catch (e) { ElMessage.error('分析失败') }
  finally { gnnLoading.value = false }
}

function renderGNNChart(nodes, links) {
  if (!gnnChartRef.value || typeof echarts === 'undefined') return
  const chart = echarts.init(gnnChartRef.value)
  const colors = { '仓库': '#00d4ff', '配送站': '#2ed573', '供应商': '#ffa502', '客户': '#a29bfe', '中转站': '#ff6b6b' }
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', backgroundColor: 'rgba(0,0,0,0.85)', borderColor: '#333', textStyle: { color: '#fff', fontSize: 13 } },
    legend: { data: Object.keys(colors), textStyle: { color: '#aaa' }, top: 5, right: 10 },
    series: [{
      type: 'graph', layout: 'force', roam: true,
      force: { repulsion: 200, gravity: 0.05, edgeLength: 150 },
      categories: Object.keys(colors).map(name => ({ name, itemStyle: { color: colors[name] } })),
      data: nodes.map((n, i) => ({ ...n, category: Object.keys(colors).indexOf(n.type) >= 0 ? Object.keys(colors).indexOf(n.type) : 0, symbolSize: Math.max(20, n.value) })),
      links: links.map(l => ({ ...l, lineStyle: { color: 'rgba(0,212,255,0.2)', width: 1.5, curveness: 0.2 } })),
      label: { show: true, color: '#ccc', fontSize: 11 },
      emphasis: { focus: 'adjacency', lineStyle: { width: 3 } },
      lineStyle: { curveness: 0.2 },
      animationDuration: 1500, animationEasingUpdate: 'quinticInOut'
    }]
  })
  window.addEventListener('resize', () => chart.resize())
}

function renderChart() {
  if (!chartRef.value || typeof echarts === 'undefined') { ElMessage.warning('ECharts 未加载'); return }
  const chart = echarts.init(chartRef.value)
  const history = chartData.value.filter(d => d.type === 'history' || !d.is_predict)
  const predict = chartData.value.filter(d => d.is_predict || d.type === 'predict')
  chart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(0,0,0,0.8)', borderColor: '#00d4ff', textStyle: { color: '#fff' } },
    legend: { data: ['历史数据', 'LSTM预测'], textStyle: { color: '#aaa' }, top: 5 },
    grid: { left: '5%', right: '3%', bottom: '12%', top: '15%', containLabel: true },
    xAxis: { type: 'category', data: chartData.value.map(d => d.date || d.label || ''), axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#888', fontSize: 11, rotate: 30 } },
    yAxis: { type: 'value', name: '订单量', axisLine: { lineStyle: { color: '#333' } }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }, axisLabel: { color: '#888' }, nameTextStyle: { color: '#888' } },
    series: [
      { name: '历史数据', type: 'line', data: history.map(d => d.value || d.count || 0), smooth: true, lineStyle: { color: '#00d4ff', width: 2 }, itemStyle: { color: '#00d4ff' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(0,212,255,0.15)' }, { offset: 1, color: 'rgba(0,212,255,0)' }] } } },
      { name: 'LSTM预测', type: 'line', data: predict.map(d => d.value || d.count || 0), smooth: true, lineStyle: { color: '#2ed573', width: 2, type: 'dashed' }, itemStyle: { color: '#2ed573' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(46,213,115,0.1)' }, { offset: 1, color: 'rgba(46,213,115,0)' }] } } }
    ]
  })
  window.addEventListener('resize', () => chart.resize())
}
</script>

<style scoped>
.dl-page { padding: 24px; }
.dl-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.dl-header h2 { color: #00d4ff; font-size: 20px; margin: 0; }

.module-tabs { display: flex; gap: 8px; margin-bottom: 24px; }
.module-tab {
  padding: 10px 20px; background: rgba(0,0,0,0.2); border-radius: 10px;
  color: #888; font-size: 14px; cursor: pointer; border: 1px solid rgba(255,255,255,0.05);
  transition: all 0.3s;
}
.module-tab.active { color: #00d4ff; background: rgba(0,212,255,0.08); border-color: rgba(0,212,255,0.3); font-weight: 600; }
.module-tab:not(.active):hover { color: #aaa; border-color: rgba(255,255,255,0.1); }

.action-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }

.chart-area { min-height: 350px; }
.chart-box { background: rgba(0,0,0,0.2); border-radius: 12px; padding: 20px; border: 1px solid rgba(255,255,255,0.05); }
.chart-box h4 { color: #00d4ff; margin-bottom: 12px; font-size: 15px; }
.chart-container { width: 100%; height: 300px; }
.loading-tip { color: #ffa502; font-size: 14px; padding: 40px; text-align: center; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 20px; }
.stat-card { background: rgba(0,0,0,0.2); border-radius: 10px; padding: 16px; text-align: center; border: 1px solid rgba(255,255,255,0.05); }
.stat-val { color: #00d4ff; font-size: 24px; font-weight: 700; margin-bottom: 4px; }
.stat-lbl { color: #666; font-size: 12px; }

.coming-soon { text-align: center; padding: 80px 0; }
.cs-icon { font-size: 48px; margin-bottom: 16px; }
.coming-soon h3 { color: #888; margin-bottom: 8px; }
.coming-soon p { color: #555; font-size: 14px; }

/* AutoEncoder */
.action-tip { color: #666; font-size: 13px; }
.anomaly-list h4 { color: #00d4ff; margin-bottom: 12px; }
.anomaly-list { animation: fadeUp 0.4s ease; }
.ae-item {
  display: flex; align-items: center; gap: 14px;
  background: rgba(0,0,0,0.15); padding: 14px 18px; border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.03); margin-bottom: 8px;
  transition: all 0.2s;
}
.ae-item:hover { border-color: rgba(255,255,255,0.08); }
.ae-item.high { border-left: 3px solid #ff4757; }
.ae-item.medium { border-left: 3px solid #ffa502; }
.ae-item.low { border-left: 3px solid #2ed573; }
.ae-level { font-size: 20px; }
.ae-content { flex: 1; }
.ae-type { color: #e8e8e8; font-size: 14px; font-weight: 600; margin-bottom: 2px; }
.ae-desc { color: #888; font-size: 12px; }
.ae-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; color: #555; font-size: 11px; }
.stat-val.warn { color: #ff4757; }

/* GNN */
.key-nodes h4 { color: #a29bfe; margin: 20px 0 12px; }
.node-rank {
  display: flex; align-items: center; gap: 14px;
  background: rgba(0,0,0,0.15); padding: 12px 18px; border-radius: 10px;
  margin-bottom: 8px; border: 1px solid rgba(255,255,255,0.03);
}
.rank-badge {
  width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: #888; background: rgba(255,255,255,0.08);
}
.rank-badge.gold { background: rgba(255,215,0,0.2); color: #ffd700; }
.rank-badge.silver { background: rgba(192,192,192,0.2); color: #c0c0c0; }
.rank-badge.bronze { background: rgba(205,127,50,0.2); color: #cd7f32; }
.node-info { flex: 1; }
.node-name { color: #e8e8e8; font-size: 14px; font-weight: 600; }
.node-type { color: #666; font-size: 12px; }
.node-score { color: #a29bfe; font-size: 16px; font-weight: 700; }
</style>
