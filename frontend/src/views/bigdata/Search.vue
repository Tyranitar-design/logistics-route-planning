<template>
  <div class="search-page">
    <!-- 搜索框 -->
    <div class="search-header">
      <h2>🔍 订单全文搜索</h2>
      <p class="subtitle">Elasticsearch 驱动 · 毫秒级响应 · 智能补全</p>
    </div>
    
    <div class="search-box">
      <el-input
        v-model="searchQuery"
        placeholder="搜索订单号、客户名、城市、货物类型..."
        size="large"
        clearable
        @keyup.enter="handleSearch"
        @input="handleInput"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
        <template #append>
          <el-button type="primary" @click="handleSearch" :loading="loading">
            搜索
          </el-button>
        </template>
      </el-input>
      
      <!-- 搜索建议 -->
      <div v-if="suggestions.length > 0 && showSuggestions" class="suggestions">
        <div 
          v-for="item in suggestions" 
          :key="item.text" 
          class="suggestion-item"
          @click="selectSuggestion(item.text)"
        >
          <el-icon><Search /></el-icon>
          <span>{{ item.text }}</span>
          <el-tag size="small" type="info">{{ item.field }}</el-tag>
        </div>
      </div>
    </div>

    <!-- 搜索结果 -->
    <div v-if="searchResults.length > 0" class="results">
      <div class="results-header">
        <span>找到 <strong>{{ totalResults }}</strong> 条结果</span>
        <span class="source-info" v-if="dataSource">
          <el-tag size="small" :type="dataSource === 'elasticsearch' ? 'success' : 'warning'">
            {{ dataSource === 'elasticsearch' ? 'ES 实时搜索' : '数据库搜索' }}
          </el-tag>
        </span>
      </div>
      
      <el-table 
        :data="searchResults" 
        stripe 
        style="width: 100%"
        @row-click="viewOrder"
      >
        <el-table-column prop="order_id" label="订单号" width="150">
          <template #default="{ row }">
            <span class="order-id">{{ row.order_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="customer_name" label="客户" width="120" />
        <el-table-column label="路线" width="200">
          <template #default="{ row }">
            <span class="route">
              {{ row.origin_city || '-' }} → {{ row.destination_city || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="cargo_type" label="货物类型" width="100" />
        <el-table-column prop="weight" label="重量(kg)" width="100">
          <template #default="{ row }">
            {{ row.weight?.toFixed(1) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="totalResults"
          layout="prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </div>
    
    <!-- 空状态 -->
    <el-empty 
      v-else-if="hasSearched" 
      description="没有找到匹配的订单"
    >
      <el-button type="primary" @click="clearSearch">清空搜索</el-button>
    </el-empty>
    
    <!-- 初始状态 -->
    <div v-else class="initial-state">
      <el-icon :size="64" color="#00d4ff"><Search /></el-icon>
      <h3>开始搜索</h3>
      <p>输入订单号、客户名、城市或货物类型进行搜索</p>
      <div class="quick-search">
        <span>快速搜索：</span>
        <el-tag 
          v-for="tag in quickTags" 
          :key="tag" 
          class="quick-tag"
          @click="quickSearch(tag)"
        >
          {{ tag }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const searchQuery = ref('')
const searchResults = ref([])
const suggestions = ref([])
const showSuggestions = ref(false)
const loading = ref(false)
const hasSearched = ref(false)
const totalResults = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const dataSource = ref('')

const quickTags = ['北京', '上海', '电子产品', '服装', '食品']

let debounceTimer = null

const handleInput = () => {
  // 防抖
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    if (searchQuery.value.length >= 2) {
      fetchSuggestions()
    } else {
      suggestions.value = []
      showSuggestions.value = false
    }
  }, 300)
}

const fetchSuggestions = async () => {
  try {
    const res = await fetch(`/api/es/suggestions?q=${encodeURIComponent(searchQuery.value)}`)
    const data = await res.json()
    if (data.success) {
      suggestions.value = data.suggestions
      showSuggestions.value = data.suggestions.length > 0
    }
  } catch (e) {
    console.error('获取建议失败:', e)
  }
}

const selectSuggestion = (text) => {
  searchQuery.value = text
  showSuggestions.value = false
  handleSearch()
}

const handleSearch = async () => {
  if (!searchQuery.value.trim()) return
  
  showSuggestions.value = false
  loading.value = true
  hasSearched.value = true
  
  try {
    const res = await fetch(
      `/api/es/search?q=${encodeURIComponent(searchQuery.value)}&page=${currentPage.value}&size=${pageSize.value}`
    )
    const data = await res.json()
    
    if (data.success) {
      searchResults.value = data.data.orders
      totalResults.value = data.data.total
      dataSource.value = data.data.source || 'elasticsearch'
    }
  } catch (e) {
    console.error('搜索失败:', e)
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page) => {
  currentPage.value = page
  handleSearch()
}

const quickSearch = (tag) => {
  searchQuery.value = tag
  handleSearch()
}

const clearSearch = () => {
  searchQuery.value = ''
  searchResults.value = []
  hasSearched.value = false
  suggestions.value = []
}

const viewOrder = (row) => {
  router.push(`/orders?id=${row.order_id}`)
}

const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    in_transit: 'primary',
    delivered: 'success',
    cancelled: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    pending: '待处理',
    in_transit: '运输中',
    delivered: '已送达',
    cancelled: '已取消'
  }
  return texts[status] || status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  // 页面加载时可以执行一些初始化
})
</script>

<style scoped>
.search-page {
  max-width: 1200px;
  margin: 0 auto;
}

.search-header {
  text-align: center;
  margin-bottom: 24px;
}

.search-header h2 {
  margin: 0;
  color: #00d4ff;
  font-size: 24px;
}

.subtitle {
  color: #666;
  font-size: 14px;
  margin-top: 8px;
}

.search-box {
  position: relative;
  margin-bottom: 24px;
}

.suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #1a1a2e;
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  margin-top: 4px;
  z-index: 100;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.suggestion-item:hover {
  background: rgba(0, 212, 255, 0.1);
}

.results {
  background: #1a1a2e;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(0, 212, 255, 0.1);
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  color: #888;
}

.results-header strong {
  color: #00d4ff;
}

.order-id {
  color: #00d4ff;
  font-family: monospace;
}

.route {
  color: #a0a0a0;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.initial-state {
  text-align: center;
  padding: 60px 20px;
}

.initial-state h3 {
  color: #00d4ff;
  margin: 16px 0 8px;
}

.initial-state p {
  color: #666;
}

.quick-search {
  margin-top: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-tag {
  cursor: pointer;
  transition: all 0.2s;
}

.quick-tag:hover {
  background: #00d4ff;
  color: #000;
}
</style>
