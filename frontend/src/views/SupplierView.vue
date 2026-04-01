<template>
  <div class="supplier-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1>供应商管理</h1>
      <div class="header-actions">
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon>
          新增供应商
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ statistics.total || 0 }}</div>
          <div class="stat-label">供应商总数</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card active">
          <div class="stat-value">{{ statistics.active || 0 }}</div>
          <div class="stat-label">合作中</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card warning">
          <div class="stat-value">{{ statistics.by_risk?.high || 0 }}</div>
          <div class="stat-label">高风险</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card info">
          <div class="stat-value">{{ expiringContracts.length }}</div>
          <div class="stat-label">合同即将到期</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 主内容区 -->
    <el-tabs v-model="activeTab" class="main-tabs">
      <!-- 供应商列表 -->
      <el-tab-pane label="供应商列表" name="list">
        <!-- 筛选条件 -->
        <el-form :inline="true" class="filter-form">
          <el-form-item label="关键词">
            <el-input v-model="filters.keyword" placeholder="名称/编码/联系人" clearable @keyup.enter="loadSuppliers" />
          </el-form-item>
          <el-form-item label="类型">
            <el-select v-model="filters.type" placeholder="全部" clearable>
              <el-option v-for="item in supplierTypes" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="卡拉杰克分类">
            <el-select v-model="filters.kraljic_category" placeholder="全部" clearable>
              <el-option v-for="item in kraljicCategories" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="风险等级">
            <el-select v-model="filters.risk_level" placeholder="全部" clearable>
              <el-option v-for="item in riskLevels" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="loadSuppliers">查询</el-button>
            <el-button @click="resetFilters">重置</el-button>
          </el-form-item>
        </el-form>

        <!-- 表格 -->
        <el-table :data="suppliers" v-loading="loading" stripe>
          <el-table-column prop="code" label="编码" width="100" />
          <el-table-column prop="name" label="供应商名称" min-width="150">
            <template #default="{ row }">
              <el-link type="primary" @click="showDetail(row)">{{ row.name }}</el-link>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="contact_person" label="联系人" width="100" />
          <el-table-column prop="phone" label="电话" width="120" />
          <el-table-column label="卡拉杰克分类" width="120">
            <template #default="{ row }">
              <el-tag :type="getKraljicTagType(row.kraljic_category)" v-if="row.kraljic_category">
                {{ getKraljicLabel(row.kraljic_category) }}
              </el-tag>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="综合评分" width="100">
            <template #default="{ row }">
              <span :class="getScoreClass(row.total_score)">
                {{ row.total_score ? row.total_score.toFixed(1) : '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="风险等级" width="100">
            <template #default="{ row }">
              <el-tag :type="getRiskTagType(row.risk_level)" v-if="row.risk_level">
                {{ getRiskLabel(row.risk_level) }}
              </el-tag>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'">
                {{ row.status === 'active' ? '合作中' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button size="small" @click="showDetail(row)">详情</el-button>
              <el-button size="small" type="primary" @click="showEditDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.per_page"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadSuppliers"
          @current-change="loadSuppliers"
          class="pagination"
        />
      </el-tab-pane>

      <!-- 卡拉杰克矩阵 -->
      <el-tab-pane label="绩效矩阵" name="matrix">
        <div class="matrix-container">
          <div class="matrix-grid">
            <!-- 战略型 -->
            <div class="matrix-cell strategic">
              <div class="cell-header">
                <span class="cell-title">战略型</span>
                <el-tag type="danger">{{ matrixCounts.strategic }}</el-tag>
              </div>
              <div class="cell-desc">高价值 · 高风险</div>
              <div class="cell-suppliers">
                <div v-for="s in matrixData.strategic" :key="s.id" class="supplier-chip strategic" @click="showDetail(s)">
                  {{ s.name }}
                </div>
              </div>
            </div>
            <!-- 杠杆型 -->
            <div class="matrix-cell leverage">
              <div class="cell-header">
                <span class="cell-title">杠杆型</span>
                <el-tag type="success">{{ matrixCounts.leverage }}</el-tag>
              </div>
              <div class="cell-desc">高价值 · 低风险</div>
              <div class="cell-suppliers">
                <div v-for="s in matrixData.leverage" :key="s.id" class="supplier-chip leverage" @click="showDetail(s)">
                  {{ s.name }}
                </div>
              </div>
            </div>
            <!-- 瓶颈型 -->
            <div class="matrix-cell bottleneck">
              <div class="cell-header">
                <span class="cell-title">瓶颈型</span>
                <el-tag type="warning">{{ matrixCounts.bottleneck }}</el-tag>
              </div>
              <div class="cell-desc">低价值 · 高风险</div>
              <div class="cell-suppliers">
                <div v-for="s in matrixData.bottleneck" :key="s.id" class="supplier-chip bottleneck" @click="showDetail(s)">
                  {{ s.name }}
                </div>
              </div>
            </div>
            <!-- 常规型 -->
            <div class="matrix-cell routine">
              <div class="cell-header">
                <span class="cell-title">常规型</span>
                <el-tag>{{ matrixCounts.routine }}</el-tag>
              </div>
              <div class="cell-desc">低价值 · 低风险</div>
              <div class="cell-suppliers">
                <div v-for="s in matrixData.routine" :key="s.id" class="supplier-chip routine" @click="showDetail(s)">
                  {{ s.name }}
                </div>
              </div>
            </div>
          </div>
          <div class="matrix-legend">
            <div class="axis-x">
              <span class="axis-label">供应风险 →</span>
            </div>
            <div class="axis-y">
              <span class="axis-label">价<br/>值<br/>↑</span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 风险监控 -->
      <el-tab-pane label="风险监控" name="risk">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card shadow="hover" class="risk-stat-card low">
              <div class="risk-value">{{ riskDashboard.by_level?.low || 0 }}</div>
              <div class="risk-label">低风险</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="risk-stat-card medium">
              <div class="risk-value">{{ riskDashboard.by_level?.medium || 0 }}</div>
              <div class="risk-label">中风险</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="risk-stat-card high">
              <div class="risk-value">{{ riskDashboard.by_level?.high || 0 }}</div>
              <div class="risk-label">高风险</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="risk-stat-card critical">
              <div class="risk-value">{{ riskDashboard.by_level?.critical || 0 }}</div>
              <div class="risk-label">严重风险</div>
            </el-card>
          </el-col>
        </el-row>

        <h3 style="margin-top: 20px;">高风险供应商</h3>
        <el-table :data="riskDashboard.high_risk_suppliers || []" stripe>
          <el-table-column prop="code" label="编码" width="100" />
          <el-table-column prop="name" label="供应商名称" />
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column label="风险等级" width="100">
            <template #default="{ row }">
              <el-tag :type="getRiskTagType(row.risk_level)">{{ getRiskLabel(row.risk_level) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button size="small" @click="showDetail(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 即将到期合同 -->
      <el-tab-pane label="到期提醒" name="expiring">
        <el-alert v-if="expiringContracts.length === 0" type="success" title="暂无即将到期的合同" :closable="false" />
        <el-table v-else :data="expiringContracts" stripe>
          <el-table-column prop="contract_no" label="合同编号" width="150" />
          <el-table-column prop="supplier_name" label="供应商" />
          <el-table-column prop="title" label="合同名称" />
          <el-table-column label="到期日期" width="120">
            <template #default="{ row }">
              <span class="text-warning">{{ row.end_date }}</span>
            </template>
          </el-table-column>
          <el-table-column label="金额" width="120">
            <template #default="{ row }">
              ¥{{ row.amount?.toLocaleString() }}
            </template>
          </el-table-column>
          <el-table-column label="剩余天数" width="100">
            <template #default="{ row }">
              <el-tag :type="getDaysTagType(getDaysRemaining(row.end_date))">
                {{ getDaysRemaining(row.end_date) }} 天
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 新增/编辑供应商对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="800px" destroy-on-close>
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="供应商编码" prop="code">
              <el-input v-model="formData.code" placeholder="请输入编码" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="供应商名称" prop="name">
              <el-input v-model="formData.name" placeholder="请输入名称" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="类型">
              <el-select v-model="formData.type" placeholder="请选择类型" style="width: 100%;">
                <el-option v-for="item in supplierTypes" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属行业">
              <el-input v-model="formData.industry" placeholder="请输入行业" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider>联系信息</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="联系人">
              <el-input v-model="formData.contact_person" placeholder="请输入联系人" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="电话">
              <el-input v-model="formData.phone" placeholder="请输入电话" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="邮箱">
              <el-input v-model="formData.email" placeholder="请输入邮箱" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="地址">
              <el-input v-model="formData.address" placeholder="请输入地址" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider>资质信息</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="营业执照号">
              <el-input v-model="formData.license_no" placeholder="请输入营业执照号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="执照到期日">
              <el-date-picker v-model="formData.license_expire" type="date" placeholder="选择日期" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="资质等级">
              <el-input v-model="formData.qualification_level" placeholder="请输入资质等级" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="合作开始日期">
              <el-date-picker v-model="formData.cooperation_start" type="date" placeholder="选择日期" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider>银行信息</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="开户行">
              <el-input v-model="formData.bank_name" placeholder="请输入开户行" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="银行账号">
              <el-input v-model="formData.bank_account" placeholder="请输入银行账号" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 供应商详情对话框 -->
    <el-dialog v-model="detailVisible" title="供应商详情" width="900px" destroy-on-close>
      <el-tabs v-model="detailTab">
        <el-tab-pane label="基本信息" name="info">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="编码">{{ currentSupplier.code }}</el-descriptions-item>
            <el-descriptions-item label="名称">{{ currentSupplier.name }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ currentSupplier.type }}</el-descriptions-item>
            <el-descriptions-item label="行业">{{ currentSupplier.industry }}</el-descriptions-item>
            <el-descriptions-item label="联系人">{{ currentSupplier.contact_person }}</el-descriptions-item>
            <el-descriptions-item label="电话">{{ currentSupplier.phone }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ currentSupplier.email }}</el-descriptions-item>
            <el-descriptions-item label="地址" :span="2">{{ currentSupplier.address }}</el-descriptions-item>
            <el-descriptions-item label="营业执照号">{{ currentSupplier.license_no }}</el-descriptions-item>
            <el-descriptions-item label="执照到期日">{{ currentSupplier.license_expire }}</el-descriptions-item>
            <el-descriptions-item label="开户行">{{ currentSupplier.bank_name }}</el-descriptions-item>
            <el-descriptions-item label="银行账号">{{ currentSupplier.bank_account }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <el-tab-pane label="绩效评估" name="performance">
          <div class="performance-section">
            <el-row :gutter="20" class="score-cards">
              <el-col :span="6">
                <div class="score-card">
                  <div class="score-value">{{ currentSupplier.quality_score?.toFixed(1) || '-' }}</div>
                  <div class="score-label">质量评分</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="score-card">
                  <div class="score-value">{{ currentSupplier.delivery_score?.toFixed(1) || '-' }}</div>
                  <div class="score-label">交付评分</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="score-card">
                  <div class="score-value">{{ currentSupplier.cost_score?.toFixed(1) || '-' }}</div>
                  <div class="score-label">成本评分</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="score-card">
                  <div class="score-value">{{ currentSupplier.service_score?.toFixed(1) || '-' }}</div>
                  <div class="score-label">服务评分</div>
                </div>
              </el-col>
            </el-row>
            <div class="total-score">
              <span>综合评分：</span>
              <span class="score" :class="getScoreClass(currentSupplier.total_score)">
                {{ currentSupplier.total_score?.toFixed(1) || '-' }}
              </span>
            </div>
            <el-button type="primary" @click="showEvaluateDialog">执行评估</el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="合同管理" name="contracts">
          <el-button type="primary" size="small" style="margin-bottom: 15px;" @click="showContractDialog">新增合同</el-button>
          <el-table :data="supplierContracts" stripe size="small">
            <el-table-column prop="contract_no" label="合同编号" width="120" />
            <el-table-column prop="title" label="合同名称" />
            <el-table-column label="有效期" width="200">
              <template #default="{ row }">
                {{ row.start_date }} ~ {{ row.end_date }}
              </template>
            </el-table-column>
            <el-table-column label="金额" width="100">
              <template #default="{ row }">
                ¥{{ row.amount?.toLocaleString() }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
                  {{ row.status === 'active' ? '生效中' : row.status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="对账结算" name="settlements">
          <el-table :data="supplierSettlements" stripe size="small">
            <el-table-column prop="settlement_no" label="结算单号" width="150" />
            <el-table-column label="金额" width="120">
              <template #default="{ row }">
                ¥{{ row.amount?.toLocaleString() }}
              </template>
            </el-table-column>
            <el-table-column label="已付" width="120">
              <template #default="{ row }">
                ¥{{ row.paid_amount?.toLocaleString() }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getSettlementTagType(row.status)" size="small">
                  {{ getSettlementLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="160" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="风险记录" name="risks">
          <el-table :data="supplierRisks" stripe size="small">
            <el-table-column prop="risk_type" label="风险类型" width="100">
              <template #default="{ row }">
                {{ getRiskTypeLabel(row.risk_type) }}
              </template>
            </el-table-column>
            <el-table-column label="风险等级" width="100">
              <template #default="{ row }">
                <el-tag :type="getRiskTagType(row.risk_level)" size="small">
                  {{ getRiskLabel(row.risk_level) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="风险描述" />
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'danger' : 'success'" size="small">
                  {{ row.status === 'active' ? '待处理' : '已处置' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="reported_at" label="上报时间" width="160" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- 绩效评估对话框 -->
    <el-dialog v-model="evaluateVisible" title="绩效评估" width="500px">
      <el-form :model="evaluateForm" label-width="100px">
        <el-form-item label="质量评分">
          <el-slider v-model="evaluateForm.quality_score" :min="0" :max="100" show-input />
        </el-form-item>
        <el-form-item label="交付评分">
          <el-slider v-model="evaluateForm.delivery_score" :min="0" :max="100" show-input />
        </el-form-item>
        <el-form-item label="成本评分">
          <el-slider v-model="evaluateForm.cost_score" :min="0" :max="100" show-input />
        </el-form-item>
        <el-form-item label="服务评分">
          <el-slider v-model="evaluateForm.service_score" :min="0" :max="100" show-input />
        </el-form-item>
        <el-form-item label="战略价值">
          <el-slider v-model="evaluateForm.strategic_value" :min="0" :max="1" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="供应风险">
          <el-slider v-model="evaluateForm.supply_risk" :min="0" :max="1" :step="0.1" show-input />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="evaluateVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEvaluate">评估</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getSuppliers, getSupplierStatistics, getSupplier, createSupplier, updateSupplier, deleteSupplier,
  getPerformanceMatrix, evaluateSupplier,
  getContracts, createContract, getExpiringContracts,
  getSettlements,
  getRisks,
  getRiskDashboard,
  getSupplierTypes, getKraljicCategories, getRiskTypes, getRiskLevels
} from '@/api/supplier'

// 数据
const loading = ref(false)
const suppliers = ref([])
const statistics = ref({})
const matrixData = ref({ strategic: [], leverage: [], bottleneck: [], routine: [] })
const matrixCounts = ref({ strategic: 0, leverage: 0, bottleneck: 0, routine: 0 })
const riskDashboard = ref({})
const expiringContracts = ref([])

// 选项
const supplierTypes = ref([])
const kraljicCategories = ref([])
const riskTypes = ref([])
const riskLevels = ref([])

// 筛选和分页
const activeTab = ref('list')
const filters = reactive({
  keyword: '',
  type: '',
  kraljic_category: '',
  risk_level: ''
})
const pagination = reactive({
  page: 1,
  per_page: 20,
  total: 0
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('新增供应商')
const formRef = ref(null)
const formData = reactive({
  code: '',
  name: '',
  type: '',
  industry: '',
  contact_person: '',
  phone: '',
  email: '',
  address: '',
  license_no: '',
  license_expire: '',
  qualification_level: '',
  cooperation_start: '',
  bank_name: '',
  bank_account: ''
})
const formRules = {
  code: [{ required: true, message: '请输入编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }]
}
const submitting = ref(false)
const editingId = ref(null)

// 详情
const detailVisible = ref(false)
const detailTab = ref('info')
const currentSupplier = ref({})
const supplierContracts = ref([])
const supplierSettlements = ref([])
const supplierRisks = ref([])

// 评估
const evaluateVisible = ref(false)
const evaluateForm = reactive({
  quality_score: 80,
  delivery_score: 80,
  cost_score: 80,
  service_score: 80,
  strategic_value: 0.5,
  supply_risk: 0.5
})

// 加载数据
const loadSuppliers = async () => {
  loading.value = true
  try {
    const res = await getSuppliers({
      page: pagination.page,
      per_page: pagination.per_page,
      ...filters
    })
    if (res.data.code === 0) {
      suppliers.value = res.data.data.items
      pagination.total = res.data.data.total
    }
  } catch (error) {
    console.error('加载供应商失败:', error)
  } finally {
    loading.value = false
  }
}

const loadStatistics = async () => {
  try {
    const res = await getSupplierStatistics()
    if (res.data.code === 0) {
      statistics.value = res.data.data
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

const loadMatrix = async () => {
  try {
    const res = await getPerformanceMatrix()
    if (res.data.code === 0) {
      matrixData.value = res.data.data.matrix
      matrixCounts.value = res.data.data.counts
    }
  } catch (error) {
    console.error('加载矩阵失败:', error)
  }
}

const loadRiskDashboard = async () => {
  try {
    const res = await getRiskDashboard()
    if (res.data.code === 0) {
      riskDashboard.value = res.data.data
    }
  } catch (error) {
    console.error('加载风险仪表盘失败:', error)
  }
}

const loadExpiringContracts = async () => {
  try {
    const res = await getExpiringContracts(30)
    if (res.data.code === 0) {
      expiringContracts.value = res.data.data
    }
  } catch (error) {
    console.error('加载到期合同失败:', error)
  }
}

const loadOptions = async () => {
  try {
    const [typesRes, kraljicRes, riskTypesRes, riskLevelsRes] = await Promise.all([
      getSupplierTypes(),
      getKraljicCategories(),
      getRiskTypes(),
      getRiskLevels()
    ])
    if (typesRes.data.code === 0) supplierTypes.value = typesRes.data.data
    if (kraljicRes.data.code === 0) kraljicCategories.value = kraljicRes.data.data
    if (riskTypesRes.data.code === 0) riskTypes.value = riskTypesRes.data.data
    if (riskLevelsRes.data.code === 0) riskLevels.value = riskLevelsRes.data.data
  } catch (error) {
    console.error('加载选项失败:', error)
  }
}

// 显示详情
const showDetail = async (row) => {
  try {
    const res = await getSupplier(row.id)
    if (res.data.code === 0) {
      currentSupplier.value = res.data.data
      detailVisible.value = true
      detailTab.value = 'info'

      // 加载子数据
      loadSupplierContracts(row.id)
      loadSupplierSettlements(row.id)
      loadSupplierRisks(row.id)
    }
  } catch (error) {
    console.error('加载详情失败:', error)
  }
}

const loadSupplierContracts = async (supplierId) => {
  try {
    const res = await getContracts(supplierId)
    if (res.data.code === 0) {
      supplierContracts.value = res.data.data.items
    }
  } catch (error) {
    console.error('加载合同失败:', error)
  }
}

const loadSupplierSettlements = async (supplierId) => {
  try {
    const res = await getSettlements(supplierId)
    if (res.data.code === 0) {
      supplierSettlements.value = res.data.data.items
    }
  } catch (error) {
    console.error('加载结算失败:', error)
  }
}

const loadSupplierRisks = async (supplierId) => {
  try {
    const res = await getRisks(supplierId)
    if (res.data.code === 0) {
      supplierRisks.value = res.data.data.items
    }
  } catch (error) {
    console.error('加载风险失败:', error)
  }
}

// 新增/编辑
const showCreateDialog = () => {
  dialogTitle.value = '新增供应商'
  editingId.value = null
  Object.assign(formData, {
    code: '',
    name: '',
    type: '',
    industry: '',
    contact_person: '',
    phone: '',
    email: '',
    address: '',
    license_no: '',
    license_expire: '',
    qualification_level: '',
    cooperation_start: '',
    bank_name: '',
    bank_account: ''
  })
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  dialogTitle.value = '编辑供应商'
  editingId.value = row.id
  Object.assign(formData, row)
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitting.value = true

    if (editingId.value) {
      const res = await updateSupplier(editingId.value, formData)
      if (res.data.code === 0) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        loadSuppliers()
      }
    } else {
      const res = await createSupplier(formData)
      if (res.data.code === 0) {
        ElMessage.success('创建成功')
        dialogVisible.value = false
        loadSuppliers()
        loadStatistics()
      }
    }
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该供应商吗？', '提示', { type: 'warning' })
    const res = await deleteSupplier(row.id)
    if (res.data.code === 0) {
      ElMessage.success('删除成功')
      loadSuppliers()
      loadStatistics()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

// 评估
const showEvaluateDialog = () => {
  evaluateForm.quality_score = currentSupplier.value.quality_score || 80
  evaluateForm.delivery_score = currentSupplier.value.delivery_score || 80
  evaluateForm.cost_score = currentSupplier.value.cost_score || 80
  evaluateForm.service_score = currentSupplier.value.service_score || 80
  evaluateVisible.value = true
}

const handleEvaluate = async () => {
  try {
    const res = await evaluateSupplier(currentSupplier.value.id, evaluateForm)
    if (res.data.code === 0) {
      ElMessage.success('评估完成')
      evaluateVisible.value = false
      // 刷新详情
      const detailRes = await getSupplier(currentSupplier.value.id)
      if (detailRes.data.code === 0) {
        currentSupplier.value = detailRes.data.data
      }
      loadSuppliers()
      loadMatrix()
    }
  } catch (error) {
    console.error('评估失败:', error)
  }
}

// 重置筛选
const resetFilters = () => {
  filters.keyword = ''
  filters.type = ''
  filters.kraljic_category = ''
  filters.risk_level = ''
  loadSuppliers()
}

// 辅助函数
const getKraljicLabel = (value) => {
  const item = kraljicCategories.value.find(c => c.value === value)
  return item ? item.label : value
}

const getKraljicTagType = (value) => {
  const types = {
    strategic: 'danger',
    leverage: 'success',
    bottleneck: 'warning',
    routine: ''
  }
  return types[value] || ''
}

const getRiskLabel = (value) => {
  const item = riskLevels.value.find(l => l.value === value)
  return item ? item.label : value
}

const getRiskTagType = (value) => {
  const types = {
    low: 'success',
    medium: 'warning',
    high: 'danger',
    critical: 'info'
  }
  return types[value] || ''
}

const getRiskTypeLabel = (value) => {
  const item = riskTypes.value.find(t => t.value === value)
  return item ? item.label : value
}

const getScoreClass = (score) => {
  if (!score) return ''
  if (score >= 80) return 'score-high'
  if (score >= 60) return 'score-medium'
  return 'score-low'
}

const getSettlementTagType = (status) => {
  const types = {
    pending: 'warning',
    confirmed: 'primary',
    paid: 'success'
  }
  return types[status] || ''
}

const getSettlementLabel = (status) => {
  const labels = {
    pending: '待确认',
    confirmed: '已确认',
    paid: '已付款'
  }
  return labels[status] || status
}

const getDaysRemaining = (endDate) => {
  const end = new Date(endDate)
  const now = new Date()
  const diff = end - now
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

const getDaysTagType = (days) => {
  if (days <= 7) return 'danger'
  if (days <= 15) return 'warning'
  return 'success'
}

const showContractDialog = () => {
  ElMessage.info('合同创建功能开发中')
}

// 初始化
onMounted(() => {
  loadSuppliers()
  loadStatistics()
  loadMatrix()
  loadRiskDashboard()
  loadExpiringContracts()
  loadOptions()
})
</script>

<style scoped>
.supplier-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  padding: 20px 0;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #409EFF;
}

.stat-card.active .stat-value { color: #67C23A; }
.stat-card.warning .stat-value { color: #E6A23C; }
.stat-card.info .stat-value { color: #909399; }

.stat-label {
  color: #909399;
  margin-top: 5px;
}

.main-tabs {
  background: #fff;
  padding: 20px;
  border-radius: 4px;
}

.filter-form {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}

/* 卡拉杰克矩阵 */
.matrix-container {
  position: relative;
  padding: 20px;
}

.matrix-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 15px;
}

.matrix-cell {
  padding: 20px;
  border-radius: 8px;
  min-height: 200px;
}

.matrix-cell.strategic { background: linear-gradient(135deg, #fff5f5 0%, #ffe0e0 100%); border: 1px solid #ffc0c0; }
.matrix-cell.leverage { background: linear-gradient(135deg, #f0fff4 0%, #d0f0dd 100%); border: 1px solid #90EE90; }
.matrix-cell.bottleneck { background: linear-gradient(135deg, #fffbf0 0%, #ffe8c0 100%); border: 1px solid #FFD700; }
.matrix-cell.routine { background: linear-gradient(135deg, #f5f5ff 0%, #e0e0ff 100%); border: 1px solid #c0c0ff; }

.cell-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.cell-title {
  font-weight: bold;
  font-size: 16px;
}

.cell-desc {
  color: #909399;
  font-size: 12px;
  margin-bottom: 15px;
}

.cell-suppliers {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.supplier-chip {
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.supplier-chip:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.supplier-chip.strategic { background: #ffebee; color: #c62828; }
.supplier-chip.leverage { background: #e8f5e9; color: #2e7d32; }
.supplier-chip.bottleneck { background: #fff8e1; color: #f57f17; }
.supplier-chip.routine { background: #e3f2fd; color: #1565c0; }

.matrix-legend {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
}

.axis-x {
  text-align: center;
  margin-top: 10px;
}

.axis-y {
  position: absolute;
  left: -10px;
  top: 50%;
  transform: translateY(-50%);
}

.axis-label {
  font-size: 12px;
  color: #909399;
}

/* 风险统计卡片 */
.risk-stat-card {
  text-align: center;
  padding: 20px 0;
}

.risk-stat-card .risk-value {
  font-size: 28px;
  font-weight: bold;
}

.risk-stat-card.low .risk-value { color: #67C23A; }
.risk-stat-card.medium .risk-value { color: #E6A23C; }
.risk-stat-card.high .risk-value { color: #F56C6C; }
.risk-stat-card.critical .risk-value { color: #909399; }

.risk-stat-card .risk-label {
  color: #909399;
  margin-top: 5px;
}

/* 绩效评分 */
.performance-section {
  padding: 20px 0;
}

.score-cards {
  margin-bottom: 20px;
}

.score-card {
  text-align: center;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.score-card .score-value {
  font-size: 24px;
  font-weight: bold;
  color: #409EFF;
}

.score-card .score-label {
  color: #909399;
  font-size: 12px;
  margin-top: 5px;
}

.total-score {
  margin-bottom: 20px;
  font-size: 16px;
}

.total-score .score {
  font-size: 24px;
  font-weight: bold;
}

.score-high { color: #67C23A; }
.score-medium { color: #E6A23C; }
.score-low { color: #F56C6C; }

.text-muted {
  color: #c0c4cc;
}

.text-warning {
  color: #E6A23C;
  font-weight: bold;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .supplier-container {
    padding: 10px;
  }

  .stats-row .el-col {
    margin-bottom: 10px;
  }

  .matrix-grid {
    grid-template-columns: 1fr;
  }

  .matrix-cell {
    min-height: 150px;
  }
}
</style>