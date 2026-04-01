<template>
  <div class="nodes-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>节点管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            添加节点
          </el-button>
        </div>
      </template>
      
      <!-- 搜索栏 -->
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="节点类型">
          <el-select v-model="searchForm.type" placeholder="全部" clearable>
            <el-option label="仓库" value="warehouse" />
            <el-option label="配送站" value="station" />
            <el-option label="中转站" value="transfer" />
            <el-option label="客户点" value="customer" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="节点名称" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </el-form-item>
      </el-form>
      
      <!-- 表格 -->
      <el-table :data="nodes" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="节点名称" />
        <el-table-column prop="code" label="节点编码" />
        <el-table-column prop="type" label="类型">
          <template #default="{ row }">
            <el-tag :type="getTypeTag(row.type)">
              {{ getTypeText(row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="address" label="地址" />
        <el-table-column prop="contact_person" label="联系人" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="nodeForm" :rules="rules" ref="nodeFormRef" label-width="100px">
        <el-form-item label="节点名称" prop="name">
          <el-input v-model="nodeForm.name" />
        </el-form-item>
        <el-form-item label="节点编码" prop="code">
          <el-input v-model="nodeForm.code" />
        </el-form-item>
        <el-form-item label="节点类型" prop="type">
          <el-select v-model="nodeForm.type" style="width: 100%">
            <el-option label="仓库" value="warehouse" />
            <el-option label="配送站" value="station" />
            <el-option label="中转站" value="transfer" />
            <el-option label="客户点" value="customer" />
          </el-select>
        </el-form-item>
        <el-form-item label="详细地址">
          <el-input v-model="nodeForm.address" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="经度">
              <el-input-number v-model="nodeForm.longitude" :precision="6" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="纬度">
              <el-input-number v-model="nodeForm.latitude" :precision="6" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="联系人">
          <el-input v-model="nodeForm.contact_person" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="nodeForm.contact_phone" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getNodes, createNode, updateNode, deleteNode } from '@/api/nodes'

const nodes = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('添加节点')
const nodeFormRef = ref(null)

const searchForm = reactive({
  type: '',
  keyword: ''
})

const nodeForm = reactive({
  id: null,
  name: '',
  code: '',
  type: 'warehouse',
  address: '',
  longitude: null,
  latitude: null,
  contact_person: '',
  contact_phone: ''
})

const rules = {
  name: [{ required: true, message: '请输入节点名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择节点类型', trigger: 'change' }]
}

const getTypeTag = (type) => {
  const map = { warehouse: 'primary', station: 'success', transfer: 'warning', customer: 'info' }
  return map[type] || 'info'
}

const getTypeText = (type) => {
  const map = { warehouse: '仓库', station: '配送站', transfer: '中转站', customer: '客户点' }
  return map[type] || type
}

const loadNodes = async () => {
  loading.value = true
  try {
    const res = await getNodes(searchForm)
    nodes.value = res.nodes
  } catch (error) {
    ElMessage.error('加载节点失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  loadNodes()
}

const handleAdd = () => {
  dialogTitle.value = '添加节点'
  Object.assign(nodeForm, {
    id: null, name: '', code: '', type: 'warehouse',
    address: '', longitude: null, latitude: null,
    contact_person: '', contact_phone: ''
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑节点'
  Object.assign(nodeForm, row)
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!nodeFormRef.value) return
  
  await nodeFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (nodeForm.id) {
          await updateNode(nodeForm.id, nodeForm)
          ElMessage.success('更新成功')
        } else {
          await createNode(nodeForm)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadNodes()
      } catch (error) {
        ElMessage.error('操作失败')
      }
    }
  })
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该节点吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    await deleteNode(row.id)
    ElMessage.success('删除成功')
    loadNodes()
  })
}

onMounted(() => {
  loadNodes()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
}
</style>
