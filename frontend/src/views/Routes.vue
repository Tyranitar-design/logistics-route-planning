<template>
  <div class="routes-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>路线管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            添加路线
          </el-button>
        </div>
      </template>
      
      <el-table :data="routes" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="路线名称" />
        <el-table-column label="起点">
          <template #default="{ row }">
            {{ row.start_node?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="终点">
          <template #default="{ row }">
            {{ row.end_node?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="distance" label="距离(km)" />
        <el-table-column prop="duration" label="时长(h)" />
        <el-table-column prop="total_cost" label="成本(元)" />
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
      <el-form :model="routeForm" :rules="rules" ref="routeFormRef" label-width="100px">
        <el-form-item label="路线名称" prop="name">
          <el-input v-model="routeForm.name" />
        </el-form-item>
        <el-form-item label="起点" prop="start_node_id">
          <el-select v-model="routeForm.start_node_id" style="width: 100%">
            <el-option v-for="node in nodes" :key="node.id" :label="node.name" :value="node.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="终点" prop="end_node_id">
          <el-select v-model="routeForm.end_node_id" style="width: 100%">
            <el-option v-for="node in nodes" :key="node.id" :label="node.name" :value="node.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="距离(km)">
              <el-input-number v-model="routeForm.distance" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="时长(h)">
              <el-input-number v-model="routeForm.duration" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="过路费(元)">
              <el-input-number v-model="routeForm.toll_cost" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="油费(元)">
              <el-input-number v-model="routeForm.fuel_cost" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
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
import { getRoutes, createRoute, updateRoute, deleteRoute } from '@/api/routes'
import { getNodes } from '@/api/nodes'

const routes = ref([])
const nodes = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('添加路线')
const routeFormRef = ref(null)

const routeForm = reactive({
  id: null,
  name: '',
  start_node_id: null,
  end_node_id: null,
  distance: 0,
  duration: 0,
  toll_cost: 0,
  fuel_cost: 0
})

const rules = {
  name: [{ required: true, message: '请输入路线名称', trigger: 'blur' }],
  start_node_id: [{ required: true, message: '请选择起点', trigger: 'change' }],
  end_node_id: [{ required: true, message: '请选择终点', trigger: 'change' }]
}

const loadRoutes = async () => {
  loading.value = true
  try {
    const res = await getRoutes()
    routes.value = res.routes
  } catch (error) {
    ElMessage.error('加载路线失败')
  } finally {
    loading.value = false
  }
}

const loadNodes = async () => {
  try {
    const res = await getNodes()
    nodes.value = res.nodes
  } catch (error) {
    console.error('加载节点失败')
  }
}

const handleAdd = () => {
  dialogTitle.value = '添加路线'
  Object.assign(routeForm, {
    id: null, name: '', start_node_id: null, end_node_id: null,
    distance: 0, duration: 0, toll_cost: 0, fuel_cost: 0
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑路线'
  Object.assign(routeForm, {
    id: row.id,
    name: row.name,
    start_node_id: row.start_node_id,
    end_node_id: row.end_node_id,
    distance: row.distance,
    duration: row.duration,
    toll_cost: row.toll_cost,
    fuel_cost: row.fuel_cost
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!routeFormRef.value) return
  
  await routeFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (routeForm.id) {
          await updateRoute(routeForm.id, routeForm)
          ElMessage.success('更新成功')
        } else {
          await createRoute(routeForm)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadRoutes()
      } catch (error) {
        ElMessage.error('操作失败')
      }
    }
  })
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该路线吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    await deleteRoute(row.id)
    ElMessage.success('删除成功')
    loadRoutes()
  })
}

onMounted(() => {
  loadRoutes()
  loadNodes()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
