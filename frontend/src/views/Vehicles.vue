<template>
  <div class="vehicles-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>车辆管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            添加车辆
          </el-button>
        </div>
      </template>
      
      <el-table :data="vehicles" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="plate_number" label="车牌号" />
        <el-table-column prop="vehicle_type" label="车辆类型" />
        <el-table-column prop="brand" label="品牌" />
        <el-table-column prop="capacity_weight" label="载重(吨)" />
        <el-table-column prop="driver_name" label="司机" />
        <el-table-column prop="driver_phone" label="司机电话" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
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
      <el-form :model="vehicleForm" :rules="rules" ref="vehicleFormRef" label-width="100px">
        <el-form-item label="车牌号" prop="plate_number">
          <el-input v-model="vehicleForm.plate_number" />
        </el-form-item>
        <el-form-item label="车辆类型">
          <el-input v-model="vehicleForm.vehicle_type" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="品牌">
              <el-input v-model="vehicleForm.brand" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="型号">
              <el-input v-model="vehicleForm.model" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="载重(吨)">
              <el-input-number v-model="vehicleForm.capacity_weight" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="容积(m³)">
              <el-input-number v-model="vehicleForm.capacity_volume" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="司机姓名">
              <el-input v-model="vehicleForm.driver_name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="司机电话">
              <el-input v-model="vehicleForm.driver_phone" />
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
import { getVehicles, createVehicle, updateVehicle, deleteVehicle } from '@/api/vehicles'

const vehicles = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('添加车辆')
const vehicleFormRef = ref(null)

const vehicleForm = reactive({
  id: null,
  plate_number: '',
  vehicle_type: '',
  brand: '',
  model: '',
  capacity_weight: 0,
  capacity_volume: 0,
  driver_name: '',
  driver_phone: ''
})

const rules = {
  plate_number: [{ required: true, message: '请输入车牌号', trigger: 'blur' }]
}

const getStatusType = (status) => {
  const map = { available: 'success', in_use: 'warning', maintenance: 'danger' }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = { available: '空闲', in_use: '使用中', maintenance: '维修中' }
  return map[status] || status
}

const loadVehicles = async () => {
  loading.value = true
  try {
    const res = await getVehicles()
    vehicles.value = res.vehicles
  } catch (error) {
    ElMessage.error('加载车辆失败')
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  dialogTitle.value = '添加车辆'
  Object.assign(vehicleForm, {
    id: null, plate_number: '', vehicle_type: '', brand: '', model: '',
    capacity_weight: 0, capacity_volume: 0, driver_name: '', driver_phone: ''
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑车辆'
  Object.assign(vehicleForm, row)
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!vehicleFormRef.value) return
  
  await vehicleFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (vehicleForm.id) {
          await updateVehicle(vehicleForm.id, vehicleForm)
          ElMessage.success('更新成功')
        } else {
          await createVehicle(vehicleForm)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadVehicles()
      } catch (error) {
        ElMessage.error('操作失败')
      }
    }
  })
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除该车辆吗？', '提示', { type: 'warning' })
    .then(async () => {
      await deleteVehicle(row.id)
      ElMessage.success('删除成功')
      loadVehicles()
    })
}

onMounted(() => {
  loadVehicles()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
