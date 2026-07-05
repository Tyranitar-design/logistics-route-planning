<template>
  <div class="food-case">
    <section class="food-hero">
      <div>
        <span class="cc-kicker">Case Study</span>
        <h1>食品供应链仓配优化</h1>
        <p>桃类生鲜仓配一体化案例，覆盖果园、仓库、中转场、机场、车辆、无人机与 B/C 端需求。</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" :loading="loading.importing" @click="applyImport">
          导入/刷新案例库
        </el-button>
        <el-button :loading="loading.summary" @click="loadAll">刷新控制台</el-button>
      </div>
    </section>

    <el-alert
      class="truth-strip"
      :type="truthAlertType"
      :closable="false"
      show-icon
    >
      <template #title>
        真实性等级 {{ truthMeta.authenticity_level || '-' }} · 数据源 {{ truthMeta.data_source || '-' }}
      </template>
      <div class="truth-line">
        距离：{{ truthMeta.distance_source || '-' }} · 路径：{{ truthMeta.path_source || '-' }}
        <span v-if="truthMeta.fallback_reason"> · 降级：{{ truthMeta.fallback_reason }}</span>
      </div>
    </el-alert>

    <section class="kpi-grid">
      <div v-for="item in kpis" :key="item.label" class="kpi-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </div>
    </section>

    <el-tabs v-model="activeTab" class="case-tabs" @tab-change="handleTabChange">
      <el-tab-pane label="案例总览" name="overview">
        <div class="two-column">
          <section class="case-panel">
            <div class="panel-title">
              <h2>数据审计</h2>
              <el-tag :type="summaryStatusType">{{ summary?.provider_status || 'loading' }}</el-tag>
            </div>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="源文件">{{ summaryData.source_files_found || 0 }}/{{ summaryData.source_files_expected || 0 }}</el-descriptions-item>
              <el-descriptions-item label="果园">{{ summaryData.orchard_count || 0 }}</el-descriptions-item>
              <el-descriptions-item label="仓/中转">{{ summaryData.facility_count || 0 }}</el-descriptions-item>
              <el-descriptions-item label="B端门店">{{ summaryData.b_store_count || 0 }}</el-descriptions-item>
              <el-descriptions-item label="B端需求">{{ formatNumber(summaryData.b2b_demand_rows) }} 行</el-descriptions-item>
              <el-descriptions-item label="C端需求">{{ formatNumber(summaryData.c2c_demand_rows) }} 行</el-descriptions-item>
              <el-descriptions-item label="车辆类型">{{ summaryData.vehicle_type_count || 0 }}</el-descriptions-item>
              <el-descriptions-item label="无人机">{{ summaryData.drone_type_count || 0 }}</el-descriptions-item>
            </el-descriptions>
          </section>

          <section class="case-panel">
            <div class="panel-title">
              <h2>导入预检</h2>
              <el-button size="small" :loading="loading.validate" @click="validateImport">重新预检</el-button>
            </div>
            <el-table :data="sourceFiles" height="300">
              <el-table-column prop="name" label="文件" min-width="260" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.exists ? 'success' : 'danger'" size="small">
                    {{ row.exists ? '存在' : '缺失' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="size_bytes" label="大小" width="120">
                <template #default="{ row }">{{ formatNumber(row.size_bytes) }}</template>
              </el-table-column>
            </el-table>
          </section>
        </div>

        <section class="case-panel solver-panel">
          <div class="panel-title">
            <div>
              <h2>求解器对比</h2>
              <p class="panel-subtitle">
                对比基线算法与 Gurobi / CPLEX / OR-Tools / pymoo / RL shadow 能力，硬约束仍由求解器层负责。
              </p>
            </div>
            <div class="panel-actions">
              <el-switch v-model="advancedMode" active-text="高级求解" inactive-text="基线" />
              <el-button type="primary" :loading="loading.solverCompare" @click="runSolverCompare">
                刷新求解器对比
              </el-button>
            </div>
          </div>
          <div class="mini-summary solver-summary">
            <span>对比 {{ solverCompare?.summary?.compared_solvers || 0 }}</span>
            <span>可用 {{ solverCompare?.summary?.available_solvers || 0 }}</span>
            <span>模式 {{ solverCompare?.summary?.advanced_mode ? '高级' : '基线' }}</span>
            <span>推荐 {{ solverCompare?.summary?.recommended_solver || '-' }}</span>
          </div>
          <el-table :data="solverRows" height="420">
            <el-table-column prop="solver_name" label="求解器/算法" min-width="170" />
            <el-table-column prop="category" label="类型" width="130" />
            <el-table-column prop="solver_family" label="算法族" min-width="140" />
            <el-table-column prop="execution_mode" label="执行模式" min-width="150" />
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="row.provider_status === 'ok' ? 'success' : 'warning'" size="small">
                  {{ row.provider_status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="可部署" width="90">
              <template #default="{ row }">
                <el-tag :type="row.deployable ? 'success' : 'info'" size="small">
                  {{ row.deployable ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="关键指标" min-width="260">
              <template #default="{ row }">
                <div class="metric-line">
                  <span v-if="row.metrics?.assigned_orders">分配 {{ row.metrics.assigned_orders }} 单</span>
                  <span v-if="row.metrics?.selected_facilities">设施 {{ row.metrics.selected_facilities }} 个</span>
                  <span v-if="row.metrics?.pareto_size">Pareto {{ row.metrics.pareto_size }}</span>
                  <span v-if="row.metrics?.total_cost">成本 {{ formatMoney(row.metrics.total_cost) }}</span>
                  <span v-if="row.metrics?.total_distance_km">距离 {{ row.metrics.total_distance_km }}km</span>
                  <span v-if="row.metrics?.runtime_available !== undefined">运行时 {{ row.metrics.runtime_available ? '可用' : '不可用' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="fallback_reason" label="降级/边界" min-width="260" show-overflow-tooltip />
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane label="GIS 网络" name="network">
        <section class="case-panel">
          <div class="panel-title">
            <div>
              <h2>果园-仓网-门店拓扑</h2>
              <p class="panel-subtitle">路径预览会叠加 provider / OSM GraphML / 本地基线几何，并保留来源标签。</p>
            </div>
            <div class="panel-actions">
              <el-button size="small" :loading="loading.osmCache" @click="loadOsmCacheStatus">缓存状态</el-button>
              <el-button size="small" :loading="loading.osmBuild" @click="buildOsmCache">构建基线 GraphML</el-button>
              <el-button size="small" :loading="loading.network" @click="loadNetwork">刷新网络</el-button>
            </div>
          </div>
          <div class="route-workbench">
            <div class="route-controls">
              <el-form label-position="top">
                <el-form-item label="路径来源">
                  <el-select v-model="routeForm.provider">
                    <el-option label="自动" value="auto" />
                    <el-option label="OSM / GraphML" value="osm" />
                    <el-option label="高德" value="amap" />
                    <el-option label="天地图" value="tianditu" />
                    <el-option label="本地基线" value="haversine" />
                  </el-select>
                </el-form-item>
                <el-form-item label="起点">
                  <el-select v-model="routeForm.source_code" filterable>
                    <el-option
                      v-for="node in routeNodeOptions"
                      :key="`source-${node.node_code}`"
                      :label="node.label"
                      :value="node.node_code"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="终点">
                  <el-select v-model="routeForm.target_code" filterable>
                    <el-option
                      v-for="node in routeNodeOptions"
                      :key="`target-${node.node_code}`"
                      :label="node.label"
                      :value="node.node_code"
                    />
                  </el-select>
                </el-form-item>
                <el-button type="primary" :loading="loading.routePreview" @click="previewRoute">
                  预览路径
                </el-button>
                <el-button :loading="loading.routeCompare" @click="compareRoutes">
                  对比来源
                </el-button>
                <el-button :loading="loading.routeHistory" @click="loadRouteHistory">
                  历史
                </el-button>
              </el-form>
              <div class="route-status">
                <div>
                  <span>GraphML</span>
                  <strong>{{ osmCache?.exists ? '已就绪' : '未建立' }}</strong>
                  <small>{{ osmCache?.cache_kind || osmCache?.fallback_reason || '等待检查' }}</small>
                </div>
                <div v-if="displayRoute">
                  <span>路径真实性</span>
                  <strong>{{ displayRoute.authenticity_level }}</strong>
                  <small>{{ displayRoute.distance_source }} / {{ displayRoute.path_source }}</small>
                </div>
                <div v-if="routeCompare">
                  <span>对比缓存</span>
                  <strong>{{ cacheStatusLabel(routeCompare.cache_status) }}</strong>
                  <small>{{ routeCompare.cache_entry_id ? `#${routeCompare.cache_entry_id}` : routeCompare.request_hash || '未写入' }}</small>
                </div>
              </div>
              <el-descriptions v-if="displayRoute" :column="1" border class="route-meta">
                <el-descriptions-item label="来源">{{ displayRoute.provider }} · {{ displayRoute.provider_status }}</el-descriptions-item>
                <el-descriptions-item label="距离">{{ displayRoute.distance_km }} km / {{ displayRoute.duration_min }} min</el-descriptions-item>
                <el-descriptions-item label="路径">{{ displayRoute.path_source }}</el-descriptions-item>
                <el-descriptions-item label="降级">{{ displayRoute.fallback_reason || '无' }}</el-descriptions-item>
              </el-descriptions>
              <div v-if="routeCompareRows.length" class="route-compare-insight">
                <div class="route-compare-stats">
                  <div v-for="item in routeCompareSummaryItems" :key="item.label" class="route-compare-stat">
                    <span>{{ item.label }}</span>
                    <strong>{{ item.value }}</strong>
                    <small>{{ item.hint }}</small>
                  </div>
                </div>
                <p>{{ routeCompareInsight }}</p>
                <div class="route-score-list">
                  <button
                    v-for="card in routeCompareScoreCards"
                    :key="card.provider"
                    type="button"
                    class="route-score-card"
                    :class="{ active: card.provider === displayRoute?.provider }"
                    @click="selectCompareRoute(card.raw)"
                  >
                    <div class="route-score-head">
                      <span>{{ card.provider }}</span>
                      <strong>{{ card.score }}</strong>
                    </div>
                    <el-progress :percentage="card.score" :color="scoreColor(card.score)" :stroke-width="8" :show-text="false" />
                    <div class="route-score-breakdown">
                      <span>真实 {{ card.breakdown.authenticity || 0 }}</span>
                      <span>状态 {{ card.breakdown.provider_status || 0 }}</span>
                      <span>几何 {{ card.breakdown.geometry || 0 }}</span>
                      <span>降级 {{ card.breakdown.fallback || 0 }}</span>
                    </div>
                    <small>{{ scoreBandLabel(card.band) }} · {{ card.status }}</small>
                  </button>
                </div>
              </div>
              <el-table
                v-if="routeCompareRows.length"
                :data="routeCompareRows"
                class="route-compare-table"
                height="220"
                highlight-current-row
                :row-class-name="routeCompareRowClass"
                @current-change="selectCompareRoute"
              >
                <el-table-column label="来源" width="96">
                  <template #default="{ row }">
                    <div class="provider-cell">
                      <strong>{{ row.provider }}</strong>
                      <el-tag v-if="row.provider === routeCompare?.summary?.recommended_provider" size="small" type="success">推荐</el-tag>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="等级" width="74">
                  <template #default="{ row }">
                    <el-tag :type="row.authenticity_level === 'A' ? 'success' : row.authenticity_level === 'B' ? 'warning' : 'info'" size="small">
                      {{ row.authenticity_level }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="距离" width="92">
                  <template #default="{ row }">{{ row.distance_km }}km</template>
                </el-table-column>
                <el-table-column label="时长" width="82">
                  <template #default="{ row }">{{ row.duration_min }}min</template>
                </el-table-column>
                <el-table-column label="评分" width="86">
                  <template #default="{ row }">
                    <strong class="route-score-value">{{ Math.round(row.quality_score || 0) }}</strong>
                  </template>
                </el-table-column>
                <el-table-column prop="fallback_reason" label="说明" min-width="180" show-overflow-tooltip />
              </el-table>
              <div v-if="routeHistoryRows.length" class="route-history-panel">
                <div class="history-title">
                  <span>最近路线对比记录</span>
                  <small>{{ routeHistory?.cache_contract?.table }}</small>
                </div>
                <el-table :data="routeHistoryRows" height="180" class="route-history-table">
                  <el-table-column prop="created_at" label="时间" width="138">
                    <template #default="{ row }">{{ formatHistoryTime(row.created_at) }}</template>
                  </el-table-column>
                  <el-table-column label="起终点" min-width="132">
                    <template #default="{ row }">{{ row.source_code }} → {{ row.target_code }}</template>
                  </el-table-column>
                  <el-table-column prop="recommended_provider" label="推荐" width="86" />
                  <el-table-column label="评分" width="72">
                    <template #default="{ row }">{{ Math.round(row.recommended_score || 0) }}</template>
                  </el-table-column>
                  <el-table-column prop="fallback_reason" label="降级/说明" min-width="160" show-overflow-tooltip />
                </el-table>
              </div>
            </div>
            <div ref="networkChartRef" class="network-chart"></div>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane label="数学模型" name="model">
        <section class="case-panel model-panel">
          <h2>多层级生鲜仓配模型</h2>
          <div class="model-grid">
            <div>
              <h3>决策变量</h3>
              <p>x<sub>ij</sub> 表示果园/仓/客户之间的流量，y<sub>k</sub> 表示仓库或中转场是否启用，z<sub>rv</sub> 表示路线 r 使用车辆 v。</p>
            </div>
            <div>
              <h3>目标函数</h3>
              <p>min 成本 + 碳排 + 鲜损风险 - 服务满意度。首期用确定性 baseline，二期接 Gurobi/CPLEX 和 pymoo Pareto。</p>
            </div>
            <div>
              <h3>硬约束</h3>
              <p>车辆载重/体积、仓库吞吐、订单唯一分配、无人机载重和航程、48 小时时效、3-5 天鲜度窗口。</p>
            </div>
            <div>
              <h3>AI Shadow</h3>
              <p>需求预测、鲜度风险、车辆方案重排建议只做 shadow，不直接替代求解器或写业务状态。</p>
            </div>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane label="智能调度" name="dispatch">
        <div class="two-column">
          <section class="case-panel">
            <div class="panel-title">
              <h2>调度波次</h2>
              <div class="panel-actions">
                <el-switch v-model="advancedMode" active-text="OR-Tools" inactive-text="贪心" />
                <el-button type="primary" :loading="loading.dispatch" @click="runDispatch">生成调度</el-button>
              </div>
            </div>
            <el-form :inline="true" class="control-form">
              <el-form-item label="日期">
                <el-input v-model="dispatchForm.wave_date" placeholder="06-01" />
              </el-form-item>
              <el-form-item label="门店数">
                <el-input-number v-model="dispatchForm.store_limit" :min="1" :max="60" />
              </el-form-item>
            </el-form>
            <div class="mini-summary">
              <span>已分配 {{ dispatchResult?.summary?.assigned_orders || 0 }}</span>
              <span>未分配 {{ dispatchResult?.summary?.unassigned_orders || 0 }}</span>
              <span>总成本 {{ formatMoney(dispatchResult?.summary?.total_cost) }}</span>
              <span>算法 {{ dispatchResult?.solver_family || '-' }}</span>
            </div>
          </section>

          <section class="case-panel">
            <div class="panel-title">
              <h2>约束校验</h2>
              <el-tag :type="dispatchResult?.constraint_validation?.capacity_violations ? 'danger' : 'success'">
                容量违约 {{ dispatchResult?.constraint_validation?.capacity_violations || 0 }}
              </el-tag>
            </div>
            <el-table :data="dispatchPlans" height="360">
              <el-table-column prop="route_id" label="路线" width="150" />
              <el-table-column prop="vehicle_type" label="车辆" width="100" />
              <el-table-column prop="stops" label="站点">
                <template #default="{ row }">{{ row.stops.join(' -> ') }}</template>
              </el-table-column>
              <el-table-column prop="load_kg" label="载重kg" width="100" />
              <el-table-column prop="utilization" label="利用率" width="110">
                <template #default="{ row }">{{ Math.round(row.utilization * 100) }}%</template>
              </el-table-column>
              <el-table-column prop="distance_km" label="距离km" width="100" />
            </el-table>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="方案对比" name="compare">
        <div class="two-column">
          <section class="case-panel">
            <div class="panel-title">
              <h2>仓网选址</h2>
              <div class="panel-actions">
                <el-switch v-model="advancedMode" active-text="MILP" inactive-text="基线" />
                <el-button :loading="loading.networkDesign" @click="runNetworkDesign">运行选址</el-button>
              </div>
            </div>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="选中设施">{{ networkDesign?.summary?.selected_facility_count || 0 }}</el-descriptions-item>
              <el-descriptions-item label="客户分配">{{ networkDesign?.summary?.assigned_customers || 0 }}</el-descriptions-item>
              <el-descriptions-item label="平均距离">{{ networkDesign?.summary?.avg_distance_km || 0 }} km</el-descriptions-item>
              <el-descriptions-item label="总成本">{{ formatMoney(networkDesign?.summary?.total_cost) }}</el-descriptions-item>
              <el-descriptions-item label="算法">{{ networkDesign?.solver_family || '-' }} / {{ networkDesign?.execution_mode || '-' }}</el-descriptions-item>
            </el-descriptions>
          </section>

          <section class="case-panel">
            <div class="panel-title">
              <h2>Pareto 前沿</h2>
              <div class="panel-actions">
                <el-switch v-model="advancedMode" active-text="NSGA" inactive-text="基线" />
                <el-button type="primary" :loading="loading.pareto" @click="runPareto">刷新对比</el-button>
              </div>
            </div>
            <div ref="paretoChartRef" class="pareto-chart"></div>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="C 端 & 无人机" name="c2c">
        <section class="case-panel">
          <div class="panel-title">
            <div>
              <h2>C 端地理分布</h2>
              <p class="panel-subtitle">
                22259 条 C 端地址聚合到有界区域中心；坐标来自 provider 地理编码或本地兜底，绝不造假。
              </p>
            </div>
            <div class="panel-actions">
              <el-button size="small" :loading="loading.geocode" @click="runGeocode">地理编码 5 条</el-button>
              <el-button size="small" :loading="loading.c2c" @click="loadC2cClusters">刷新聚类</el-button>
            </div>
          </div>
          <div class="mini-summary">
            <span>原始 <strong>{{ c2cSummary.raw_row_count || 0 }}</strong></span>
            <span>聚类 <strong>{{ c2cSummary.cluster_count || 0 }}</strong></span>
            <span>已解析 <strong>{{ c2cSummary.resolved_centroids || 0 }}</strong></span>
            <span>待编码 <strong>{{ c2cSummary.needs_geocoding || 0 }}</strong></span>
            <span>真实性 <strong>{{ c2cClustersMeta.authenticity_level || '-' }}</strong></span>
            <span v-if="c2cClustersMeta.fallback_reason" class="muted">降级 {{ c2cClustersMeta.fallback_reason }}</span>
          </div>
          <el-table :data="c2cClusterRows" height="320">
            <el-table-column prop="region" label="区域" min-width="120" />
            <el-table-column prop="orders" label="订单数" width="90" />
            <el-table-column prop="weight_kg" label="重量(kg)" width="100" />
            <el-table-column prop="address_count" label="地址数" width="90" />
            <el-table-column label="坐标" min-width="170">
              <template #default="{ row }">
                <span v-if="row.lon">{{ row.lon.toFixed(3) }}, {{ row.lat.toFixed(3) }}</span>
                <span v-else class="muted">待编码</span>
              </template>
            </el-table-column>
            <el-table-column prop="centroid_source" label="来源" min-width="180" show-overflow-tooltip />
            <el-table-column prop="cluster_authenticity_level" label="真实性" width="80" />
          </el-table>
        </section>

        <section class="case-panel">
          <div class="panel-title">
            <div>
              <h2>无人机最后一公里</h2>
              <p class="panel-subtitle">
                无人机(10kg/20km) vs 车辆 vs 混合，按成本/时效/碳排/鲜度对比；硬约束由求解器层保底。
              </p>
            </div>
            <div class="panel-actions">
              <el-button type="primary" size="small" :loading="loading.lastMile" @click="loadLastMile">刷新最后一公里</el-button>
            </div>
          </div>
          <div class="mini-summary">
            <span>聚类 <strong>{{ lastMileSummary.cluster_count || 0 }}</strong></span>
            <span>无人机可行 <strong>{{ lastMileSummary.drone_feasible_clusters || 0 }}</strong></span>
            <span>仅车辆 <strong>{{ lastMileSummary.vehicle_only_clusters || 0 }}</strong></span>
            <span>真实性 <strong>{{ lastMileMeta.authenticity_level || '-' }}</strong></span>
            <span v-if="lastMileMeta.fallback_reason" class="muted">降级 {{ lastMileMeta.fallback_reason }}</span>
          </div>
          <el-table :data="lastMileRows" height="360">
            <el-table-column prop="cluster" label="区域" min-width="110" />
            <el-table-column prop="weight_kg" label="重量(kg)" width="90" />
            <el-table-column prop="distance_km" label="距离(km)" width="90" />
            <el-table-column label="无人机" min-width="200">
              <template #default="{ row }">{{ formatLastMileMode(row, 'drone') }}</template>
            </el-table-column>
            <el-table-column label="车辆" min-width="200">
              <template #default="{ row }">{{ formatLastMileMode(row, 'vehicle') }}</template>
            </el-table-column>
            <el-table-column label="混合" min-width="200">
              <template #default="{ row }">{{ formatLastMileMode(row, 'hybrid') }}</template>
            </el-table-column>
            <el-table-column prop="recommended_mode" label="推荐" width="90" />
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane label="地理地图" name="map">
        <section class="case-panel">
          <div class="panel-title">
            <div>
              <h2>Leaflet 地理地图</h2>
              <p class="panel-subtitle">果园/仓/门店/机场/C 端聚类真实地理分布，按类型着色；坐标来自案例 Excel + 本地兜底。</p>
            </div>
            <el-button size="small" @click="loadFoodMap">刷新地图</el-button>
          </div>
          <div id="food-case-map" class="food-map"></div>
          <div class="map-legend">
            <span class="legend-item"><i class="dot dot-orchard"></i>果园</span>
            <span class="legend-item"><i class="dot dot-facility"></i>仓/中转</span>
            <span class="legend-item"><i class="dot dot-bstore"></i>B 端门店</span>
            <span class="legend-item"><i class="dot dot-airport"></i>机场</span>
            <span class="legend-item"><i class="dot dot-cluster"></i>C 端聚类</span>
          </div>
        </section>
      </el-tab-pane>

      <el-tab-pane label="季节 & 多式联运" name="season">
        <section class="case-panel">
          <div class="panel-title">
            <div>
              <h2>果园 92 天时序 & 需求预测</h2>
              <p class="panel-subtitle">确定性基线预测（移动平均+趋势+周季节性）+ 保鲜感知采摘波次；非已训练 ML 模型。</p>
            </div>
            <div class="panel-actions">
              <el-button size="small" :loading="loading.orchard" @click="loadOrchardTimeseries">刷新时序</el-button>
              <el-button size="small" :loading="loading.forecast" @click="loadOrchardForecast">刷新预测</el-button>
            </div>
          </div>
          <div class="mini-summary">
            <span>果园 <strong>{{ orchardSeries?.summary?.orchard_count || 0 }}</strong></span>
            <span>天数 <strong>{{ orchardSeries?.summary?.day_count || 0 }}</strong></span>
            <span>季总箱数 <strong>{{ orchardSeries?.summary?.season_total_boxes || 0 }}</strong></span>
            <span>模型 <strong>{{ orchardForecast?.model_stage || '-' }}</strong></span>
          </div>
          <el-table :data="orchardForecastRows" height="320">
            <el-table-column prop="orchard_code" label="果园" width="110" />
            <el-table-column prop="name" label="名称" min-width="100" />
            <el-table-column prop="moving_avg_7" label="7日均" width="90" />
            <el-table-column prop="trend" label="趋势" width="80" />
            <el-table-column label="预测14天合计" width="120">
              <template #default="{ row }">{{ row.forecast_daily?.reduce((s, d) => s + d.predicted_boxes, 0) || 0 }}</template>
            </el-table-column>
            <el-table-column label="采摘波次" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">{{ (row.harvest_waves || []).map(w => `${w.wave_date}(${w.boxes}箱/${w.days}天)`).join('，') }}</template>
            </el-table-column>
          </el-table>
        </section>

        <section class="case-panel">
          <div class="panel-title">
            <div>
              <h2>空运多式联运</h2>
              <p class="panel-subtitle">纯陆运 vs 空+陆 vs 空+无人机，B747-8F(135t/426km/h)，距离 Haversine 基线。</p>
            </div>
            <el-button type="primary" size="small" :loading="loading.multimodal" @click="runMultimodal">刷新多式联运</el-button>
          </div>
          <div class="mini-summary">
            <span>聚类 <strong>{{ multimodalResult?.summary?.cluster_count || 0 }}</strong></span>
            <span>空运可行 <strong>{{ multimodalResult?.summary?.air_feasible_clusters || 0 }}</strong></span>
            <span>货运机场已编码 <strong>{{ multimodalResult?.constraint_validation?.freight_airports_geocoded || 0 }}</strong></span>
          </div>
          <el-table :data="multimodalRows" height="320">
            <el-table-column prop="cluster" label="区域" min-width="100" />
            <el-table-column prop="weight_kg" label="重量(kg)" width="90" />
            <el-table-column prop="nearest_freight_airport" label="最近货运机场" min-width="140" show-overflow-tooltip />
            <el-table-column label="纯陆运" min-width="170"><template #default="{ row }">{{ formatMultimodalMode(row, 'pure_road') }}</template></el-table-column>
            <el-table-column label="空+陆" min-width="170"><template #default="{ row }">{{ formatMultimodalMode(row, 'air_plus_road') }}</template></el-table-column>
            <el-table-column label="空+无人机" min-width="170"><template #default="{ row }">{{ formatMultimodalMode(row, 'air_plus_drone') }}</template></el-table-column>
            <el-table-column prop="recommended_mode" label="推荐" width="100" />
          </el-table>
        </section>

        <section class="case-panel">
          <div class="panel-title">
            <div>
              <h2>鲜度感知 VRPTW 调度</h2>
              <p class="panel-subtitle">48h 时间窗硬约束 + 鲜度衰减(时间×温度×搬运)，30℃ 4 天满衰减（案例基准）。</p>
            </div>
            <el-button type="primary" size="small" :loading="loading.dispatchFresh" @click="runDispatchFresh">刷新鲜度调度</el-button>
          </div>
          <div class="mini-summary">
            <span>已分配 <strong>{{ dispatchFreshResult?.summary?.assigned_orders || 0 }}</strong></span>
            <span>未分配 <strong>{{ dispatchFreshResult?.summary?.unassigned_orders || 0 }}</strong></span>
            <span>时间窗 <strong>{{ dispatchFreshResult?.summary?.time_window_hours || 0 }}h</strong></span>
            <span>均鲜度 <strong>{{ dispatchFreshResult?.summary?.avg_freshness_score || 0 }}</strong></span>
          </div>
          <el-table :data="dispatchFreshPlans" height="300">
            <el-table-column prop="route_id" label="路线" min-width="160" />
            <el-table-column prop="customer" label="门店" min-width="120" />
            <el-table-column prop="vehicle_type" label="车型" width="90" />
            <el-table-column prop="distance_km" label="距离(km)" width="90" />
            <el-table-column prop="duration_hours" label="时长(h)" width="90" />
            <el-table-column prop="freshness_score" label="鲜度" width="80" />
            <el-table-column prop="cost" label="成本" width="80" />
          </el-table>
        </section>

        <section class="case-panel">
          <div class="panel-title">
            <div>
              <h2>可追溯链路</h2>
              <p class="panel-subtitle">采摘→包装→运输→签收，确定性追溯码（码即数据，无需查库）。</p>
            </div>
          </div>
          <el-form :inline="true" class="trace-form">
            <el-form-item label="果园"><el-input v-model="traceInput.orchard_code" /></el-form-item>
            <el-form-item label="波次日期"><el-input v-model="traceInput.wave_date" placeholder="MM-DD" /></el-form-item>
            <el-form-item label="聚类"><el-input v-model="traceInput.cluster_code" /></el-form-item>
            <el-button type="primary" :loading="loading.trace" @click="issueTrace">签发追溯码</el-button>
          </el-form>
          <div v-if="traceResult" class="trace-result">
            <div class="trace-code">追溯码：<strong>{{ traceResult.trace_code }}</strong></div>
            <el-steps :space="200" finish-status="success" :active="(traceResult.stages?.length || 1) - 1">
              <el-step v-for="(s, i) in traceResult.stages || []" :key="i" :title="s.stage" :description="`${s.time} @ ${s.location}`" />
            </el-steps>
          </div>
        </section>

        <section class="case-panel">
          <div class="panel-title">
            <div>
              <h2>场景持久化对比</h2>
              <p class="panel-subtitle">横向对比成本/碳排/时效/鲜度/服务水平，推荐可行中最优。</p>
            </div>
            <el-button type="primary" size="small" :loading="loading.scenario" @click="loadScenariosCompare">刷新对比</el-button>
          </div>
          <div class="mini-summary">
            <span>推荐 <strong>{{ scenarioCompare?.recommended_scenario || '-' }}</strong></span>
            <span>对比数 <strong>{{ scenarioCompare?.comparison?.length || 0 }}</strong></span>
          </div>
          <el-table :data="scenarioCompareRows" height="280">
            <el-table-column prop="name" label="场景" min-width="140" />
            <el-table-column prop="cost" label="成本" width="90" />
            <el-table-column prop="carbon_kg" label="碳排(kg)" width="100" />
            <el-table-column prop="duration_min" label="时效(min)" width="100" />
            <el-table-column prop="freshness_score" label="鲜度" width="80" />
            <el-table-column prop="service_level" label="服务" width="80" />
            <el-table-column label="可行" width="80">
              <template #default="{ row }"><el-tag :type="row.feasible ? 'success' : 'info'" size="small">{{ row.feasible ? '是' : '否' }}</el-tag></template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane label="Agent 解释" name="agent">
        <section class="case-panel agent-panel">
          <div class="panel-title">
            <h2>食品供应链专家 Agent</h2>
            <el-button type="primary" :loading="loading.agent" @click="askAgent">获取建议</el-button>
          </div>
          <el-input
            v-model="agentQuestion"
            type="textarea"
            :rows="3"
            placeholder="例如：请解释当前调度方案的成本、鲜度和风险，并给出下一步优化建议。"
          />
          <div class="agent-answer">
            <pre>{{ agentAnswer }}</pre>
          </div>
        </section>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  applyFoodSupplyImport,
  compareFoodSupplyRoutes,
  compareFoodSupplySolvers,
  explainFoodSupplyCase,
  buildFoodSupplyOsmCache,
  geocodeFoodSupplyC2c,
  getFoodSupplyC2cClusters,
  getFoodSupplyC2cGeocodeStatus,
  getFoodSupplyRouteCompareHistory,
  getFoodSupplyNetwork,
  getFoodSupplyOsmCacheStatus,
  getFoodSupplySummary,
  optimizeFoodSupplyDispatch,
  optimizeFoodSupplyDispatchFresh,
  optimizeFoodSupplyLastMile,
  optimizeFoodSupplyMultimodal,
  optimizeFoodSupplyNetwork,
  optimizeFoodSupplyPareto,
  compareFoodSupplyScenarios,
  getFoodSupplyOrchardForecast,
  getFoodSupplyOrchardTimeseries,
  issueFoodSupplyTrace,
  previewFoodSupplyRoute,
  validateFoodSupplyImport,
} from '@/api/foodSupplyCase'

const activeTab = ref('overview')
const summary = ref(null)
const validation = ref(null)
const network = ref(null)
const dispatchResult = ref(null)
const networkDesign = ref(null)
const paretoResult = ref(null)
const solverCompare = ref(null)
const osmCache = ref(null)
const routePreview = ref(null)
const routeCompare = ref(null)
const routeHistory = ref(null)
const c2cClusters = ref(null)
const lastMileResult = ref(null)
const orchardSeries = ref(null)
const orchardForecast = ref(null)
const multimodalResult = ref(null)
const dispatchFreshResult = ref(null)
const scenarioCompare = ref(null)
const traceResult = ref(null)
const traceInput = ref({ orchard_code: 'ORCHARD-A', wave_date: '09-01', cluster_code: 'CC-HEFEI' })
const selectedCompareProvider = ref('')
const advancedMode = ref(true)
const agentAnswer = ref('专家建议将在这里显示。首期 Agent 只读解释，不会写入业务状态。')
const agentQuestion = ref('请解释食品供应链仓配优化案例当前方案，并给出调度、仓网和鲜度风险建议。')
const networkChartRef = ref(null)
const paretoChartRef = ref(null)
let networkChart = null
let paretoChart = null
let foodMap = null

const dispatchForm = ref({
  wave_date: '06-01',
  store_limit: 8,
})

const routeForm = ref({
  provider: 'osm',
  source_code: 'FAC-1',
  target_code: 'BSTORE-001',
})

const loading = ref({
  summary: false,
  validate: false,
  importing: false,
  network: false,
  osmCache: false,
  osmBuild: false,
  routePreview: false,
  routeCompare: false,
  routeHistory: false,
  dispatch: false,
  networkDesign: false,
  pareto: false,
  solverCompare: false,
  agent: false,
  c2c: false,
  geocode: false,
  lastMile: false,
  orchard: false,
  forecast: false,
  multimodal: false,
  dispatchFresh: false,
  trace: false,
  scenario: false,
})

const summaryData = computed(() => summary.value?.summary || {})
const sourceFiles = computed(() => summary.value?.source_files || validation.value?.source_files || [])
const dispatchPlans = computed(() => dispatchResult.value?.plans || [])
const solverRows = computed(() => solverCompare.value?.solver_results || [])
const c2cSummary = computed(() => c2cClusters.value?.summary || {})
const c2cClustersMeta = computed(() => ({
  authenticity_level: c2cClusters.value?.authenticity_level,
  distance_source: c2cClusters.value?.distance_source,
  fallback_reason: c2cClusters.value?.fallback_reason,
}))
const c2cClusterRows = computed(() => c2cClusters.value?.clusters || [])
const lastMileSummary = computed(() => lastMileResult.value?.summary || {})
const lastMileMeta = computed(() => ({
  authenticity_level: lastMileResult.value?.authenticity_level,
  fallback_reason: lastMileResult.value?.fallback_reason,
}))
const lastMileRows = computed(() => lastMileResult.value?.clusters || [])
const orchardSeriesRows = computed(() => orchardSeries.value?.series || [])
const orchardForecastRows = computed(() => orchardForecast.value?.forecast || [])
const multimodalRows = computed(() => multimodalResult.value?.clusters || [])
const dispatchFreshPlans = computed(() => dispatchFreshResult.value?.plans || [])
const scenarioCompareRows = computed(() => scenarioCompare.value?.comparison || [])
const routeNodeOptions = computed(() => {
  return (network.value?.nodes || [])
    .filter((item) => item.lon != null && item.lat != null)
    .map((item) => ({
      ...item,
      label: `${item.node_code} · ${item.name}`,
    }))
})
const routeCompareRows = computed(() => routeCompare.value?.routes || [])
const routeHistoryRows = computed(() => routeHistory.value?.history || [])
const displayRoute = computed(() => {
  if (routeCompareRows.value.length) {
    const selected = routeCompareRows.value.find((item) => item.provider === selectedCompareProvider.value)
    return selected || routeCompare.value?.recommended_route || routeCompareRows.value[0]
  }
  return routePreview.value?.route || null
})
const routeCompareSummaryItems = computed(() => {
  if (!routeCompareRows.value.length) return []
  const summary = routeCompare.value?.summary || {}
  const recommended = routeCompare.value?.recommended_route || displayRoute.value
  const distances = routeCompareRows.value
    .map((item) => Number(item.distance_km || 0))
    .filter((value) => value > 0)
  const geometryCount = summary.geometry_count ?? routeCompareRows.value.filter((item) => (item.polyline || []).length >= 2).length
  const exactCount = summary.exact_count ?? routeCompareRows.value.filter((item) => ['A', 'B'].includes(item.authenticity_level) && !item.fallback_reason).length
  const degradedCount = summary.degraded_count ?? routeCompareRows.value.filter((item) => item.provider_status !== 'ok' || item.fallback_reason).length
  const bestDistance = summary.best_distance_km ?? (distances.length ? Math.min(...distances) : null)
  return [
    { label: '对比来源', value: formatNumber(summary.provider_count || routeCompareRows.value.length), hint: `${geometryCount} 条可绘制` },
    { label: '推荐来源', value: recommended?.provider || '-', hint: routeReasonLabel(summary.recommendation_reason, recommended) },
    { label: '准真实路线', value: formatNumber(exactCount), hint: 'A/B 且无降级' },
    { label: '降级来源', value: formatNumber(degradedCount), hint: routeCompare.value?.fallback_reason || '已透明标注' },
    { label: '最短距离', value: bestDistance ? `${Number(bestDistance).toFixed(2)}km` : '-', hint: recommended?.distance_km ? `推荐 ${recommended.distance_km}km` : '等待对比' },
  ]
})
const routeCompareInsight = computed(() => {
  if (!routeCompareRows.value.length) return ''
  const summary = routeCompare.value?.summary || {}
  const reason = routeReasonLabel(summary.recommendation_reason, routeCompare.value?.recommended_route)
  const recommendedProvider = summary.recommended_provider || routeCompare.value?.recommended_route?.provider || '当前路线'
  const score = summary.recommended_score ? `，评分 ${Math.round(summary.recommended_score)}` : ''
  return `${recommendedProvider} 被选为推荐来源${score}：${reason}。所有路线都会保留 distance_source、path_source、authenticity_level 与 fallback_reason，避免把本地基线误认为真实导航。`
})
const routeCompareScoreCards = computed(() => {
  return routeCompareRows.value
    .map((row) => ({
      provider: row.provider,
      score: Math.max(0, Math.min(100, Math.round(row.quality_score || 0))),
      band: row.quality_band || 'low',
      status: row.provider_status || 'unknown',
      breakdown: row.score_breakdown || {},
      raw: row,
    }))
    .sort((a, b) => b.score - a.score)
})
const truthMeta = computed(() => {
  return routeCompare.value || routePreview.value || dispatchResult.value || network.value || summary.value || {
    authenticity_level: 'B',
    data_source: 'case_excel_workbooks',
    distance_source: 'case_excel_coordinates',
    path_source: 'case_network_baseline',
  }
})
const truthAlertType = computed(() => truthMeta.value?.authenticity_level === 'B' ? 'success' : 'warning')
const summaryStatusType = computed(() => summary.value?.provider_status === 'ok' ? 'success' : 'warning')

const kpis = computed(() => [
  { label: '果园', value: summaryData.value.orchard_count || 0, hint: '上游产地' },
  { label: '仓/中转', value: summaryData.value.facility_count || 0, hint: '候选设施' },
  { label: 'B端门店', value: summaryData.value.b_store_count || 0, hint: '经销网络' },
  { label: 'B端需求', value: formatNumber(summaryData.value.b2b_demand_rows || 0), hint: '订单行' },
  { label: 'C端需求', value: formatNumber(summaryData.value.c2c_demand_rows || 0), hint: '聚合前行数' },
  { label: '车辆类型', value: summaryData.value.vehicle_type_count || 0, hint: '调度资源' },
])

function setLoading(key, value) {
  loading.value = { ...loading.value, [key]: value }
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN')
}

function formatMoney(value) {
  return `¥${Number(value || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`
}

function routeReasonLabel(reason, route) {
  const labels = {
    PREFERRED_NON_DEGRADED_AB_PROVIDER_GEOMETRY: '优先选择无降级的 A/B 级 provider 几何',
    SHORTEST_VISIBLE_LOCAL_BASELINE_AFTER_PROVIDER_FALLBACK: '真实 provider 暂不可用，选取最短可见本地基线',
    VISIBLE_ROUTE_WITH_EXPLICIT_FALLBACK_SELECTED: '仅有降级路线可用，保留原因后选取可见方案',
    SHORTEST_VISIBLE_ROUTE_SELECTED: '选取当前可见路线中耗时/距离更优的方案',
    NO_ROUTE_AVAILABLE: '暂无可用路线',
  }
  if (reason && labels[reason]) return labels[reason]
  if (route?.fallback_reason) return route.fallback_reason
  return reason || '按真实性、降级状态与时长综合排序'
}

function scoreColor(score) {
  if (score >= 82) return '#11e0b7'
  if (score >= 60) return '#ffcf5a'
  return '#ff6b7a'
}

function scoreBandLabel(band) {
  const labels = {
    high: '高可信',
    medium: '可用',
    low: '需谨慎',
  }
  return labels[band] || '需谨慎'
}

function cacheStatusLabel(status) {
  const labels = {
    hit: '命中',
    stored: '已记录',
    miss: '未命中',
    disabled: '未启用',
    store_failed: '写入失败',
  }
  return labels[status] || status || '未启用'
}

function formatHistoryTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function loadSummary() {
  setLoading('summary', true)
  try {
    summary.value = await getFoodSupplySummary()
  } finally {
    setLoading('summary', false)
  }
}

async function validateImport() {
  setLoading('validate', true)
  try {
    validation.value = await validateFoodSupplyImport({})
    ElMessage.success('案例数据预检完成')
  } finally {
    setLoading('validate', false)
  }
}

async function applyImport() {
  setLoading('importing', true)
  try {
    await applyFoodSupplyImport({ persist: true })
    ElMessage.success('案例数据已写入 case_food_* 表')
    await Promise.all([loadSummary(), loadNetwork()])
  } finally {
    setLoading('importing', false)
  }
}

async function loadNetwork() {
  setLoading('network', true)
  try {
    network.value = await getFoodSupplyNetwork()
    ensureRouteDefaults()
    await nextTick()
    renderNetworkChart()
  } finally {
    setLoading('network', false)
  }
}

async function loadOsmCacheStatus() {
  setLoading('osmCache', true)
  try {
    osmCache.value = await getFoodSupplyOsmCacheStatus()
  } finally {
    setLoading('osmCache', false)
  }
}

async function buildOsmCache() {
  setLoading('osmBuild', true)
  try {
    osmCache.value = await buildFoodSupplyOsmCache({
      mode: 'case-baseline',
      limit: 40,
      overwrite: true,
    })
    ElMessage.success('案例基线 GraphML 已生成')
  } finally {
    setLoading('osmBuild', false)
  }
}

async function previewRoute() {
  setLoading('routePreview', true)
  try {
    routeCompare.value = null
    selectedCompareProvider.value = ''
    routePreview.value = await previewFoodSupplyRoute({
      ...routeForm.value,
    })
    await nextTick()
    renderNetworkChart()
    if (routePreview.value?.route?.fallback_reason) {
      ElMessage.warning('路径已返回降级说明，请查看真实性标签')
    } else {
      ElMessage.success('路径预览已生成')
    }
  } finally {
    setLoading('routePreview', false)
  }
}

async function compareRoutes() {
  setLoading('routeCompare', true)
  try {
    routeCompare.value = await compareFoodSupplyRoutes({
      source_code: routeForm.value.source_code,
      target_code: routeForm.value.target_code,
      providers: ['amap', 'tianditu', 'osm', 'haversine'],
      use_cache: true,
      persist: true,
      cache_ttl_hours: 24,
    })
    selectedCompareProvider.value = routeCompare.value?.summary?.recommended_provider || routeCompare.value?.recommended_route?.provider || routeCompare.value?.routes?.[0]?.provider || ''
    await loadRouteHistory({ silent: true })
    await nextTick()
    renderNetworkChart()
    if (routeCompare.value?.fallback_reason) {
      ElMessage.warning('路线对比已完成，部分来源为降级结果')
    } else {
      ElMessage.success('路线来源对比已完成')
    }
  } finally {
    setLoading('routeCompare', false)
  }
}

async function loadRouteHistory(options = {}) {
  setLoading('routeHistory', true)
  try {
    routeHistory.value = await getFoodSupplyRouteCompareHistory({
      limit: 8,
      source_code: routeForm.value.source_code,
      target_code: routeForm.value.target_code,
    })
    if (!options.silent) ElMessage.success('路线对比历史已刷新')
  } finally {
    setLoading('routeHistory', false)
  }
}

function selectCompareRoute(row) {
  if (!row?.provider) return
  selectedCompareProvider.value = row.provider
  nextTick(() => renderNetworkChart())
}

function routeCompareRowClass({ row }) {
  return row?.provider === displayRoute.value?.provider ? 'selected-route-row' : ''
}

function ensureRouteDefaults() {
  const options = routeNodeOptions.value
  if (!options.length) return
  const sourceExists = options.some((item) => item.node_code === routeForm.value.source_code)
  const targetExists = options.some((item) => item.node_code === routeForm.value.target_code)
  const defaultSource = options.find((item) => item.node_type === 'facility') || options[0]
  const defaultTarget = options.find((item) => item.node_type === 'b_store') || options[1] || options[0]
  if (!sourceExists) routeForm.value.source_code = defaultSource.node_code
  if (!targetExists) routeForm.value.target_code = defaultTarget.node_code
}

async function runDispatch() {
  setLoading('dispatch', true)
  try {
    dispatchResult.value = await optimizeFoodSupplyDispatch({
      ...dispatchForm.value,
      solver_mode: advancedMode.value ? 'ortools' : 'greedy',
      persist: false,
    })
    ElMessage.success('调度方案已生成')
  } finally {
    setLoading('dispatch', false)
  }
}

async function runNetworkDesign() {
  setLoading('networkDesign', true)
  try {
    networkDesign.value = await optimizeFoodSupplyNetwork({
      solver_mode: advancedMode.value ? 'milp' : 'greedy',
      max_facilities: 2,
      store_limit: 18,
      persist: false,
    })
    ElMessage.success('仓网选址方案已生成')
  } finally {
    setLoading('networkDesign', false)
  }
}

async function runPareto() {
  setLoading('pareto', true)
  try {
    paretoResult.value = await optimizeFoodSupplyPareto({
      algorithm_family: advancedMode.value ? 'nsga' : 'deterministic',
      max_facilities: 2,
      store_limit: 18,
      persist: false,
    })
    await nextTick()
    renderParetoChart()
  } finally {
    setLoading('pareto', false)
  }
}

async function runSolverCompare() {
  setLoading('solverCompare', true)
  try {
    solverCompare.value = await compareFoodSupplySolvers({
      wave_date: dispatchForm.value.wave_date,
      store_limit: dispatchForm.value.store_limit,
      max_facilities: 2,
      advanced_mode: advancedMode.value,
      persist: false,
    })
    ElMessage.success('求解器对比已刷新')
  } finally {
    setLoading('solverCompare', false)
  }
}

async function askAgent() {
  setLoading('agent', true)
  try {
    const response = await explainFoodSupplyCase({
      question: agentQuestion.value,
      task_context: {
        summary: summaryData.value,
        dispatch_summary: dispatchResult.value?.summary,
        network_design_summary: networkDesign.value?.summary,
      },
    })
    agentAnswer.value = response.answer || response.fallback_reason || 'Agent 暂无建议。'
  } finally {
    setLoading('agent', false)
  }
}

async function loadFoodMap() {
  // 动态加载 Leaflet（参考 MapView 模式），渲染案例所有节点 + C 端聚类
  try {
    if (!window.L) {
      await new Promise((resolve, reject) => {
        const link = document.createElement('link')
        link.rel = 'stylesheet'
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
        document.head.appendChild(link)
        const script = document.createElement('script')
        script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
        script.onload = resolve
        script.onerror = reject
        document.head.appendChild(script)
      })
    }
    const L = window.L
    const el = document.getElementById('food-case-map')
    if (!el) return
    if (foodMap) { foodMap.remove(); foodMap = null }
    foodMap = L.map('food-case-map').setView([32.0, 117.5], 5)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap', maxZoom: 18,
    }).addTo(foodMap)
    const colorByType = { orchard: '#52c41a', facility: '#1890ff', b_store: '#faad14', origin_airport: '#722ed1', freight_airport: '#eb2f96' }
    const nodes = network.value?.nodes || []
    nodes.forEach((n) => {
      if (n.lon && n.lat) {
        L.circleMarker([n.lat, n.lon], { radius: 5, color: colorByType[n.node_type] || '#999', fillColor: colorByType[n.node_type] || '#999', fillOpacity: 0.8 })
          .addTo(foodMap)
          .bindPopup(`<b>${n.node_type}</b><br/>${n.name}`)
      }
    })
    const clusters = c2cClusters.value?.clusters || []
    clusters.forEach((c) => {
      if (c.lon && c.lat) {
        L.circleMarker([c.lat, c.lon], { radius: 7, color: '#13c2c2', fillColor: '#13c2c2', fillOpacity: 0.6 })
          .addTo(foodMap)
          .bindPopup(`<b>C 端聚类</b><br/>${c.region}<br/>${c.orders} 单 / ${c.weight_kg} kg`)
      }
    })
  } catch (e) {
    ElMessage.error('地图加载失败（可能无外网）')
  }
}

function formatLastMileMode(row, mode) {
  const m = (row.modes || []).find((x) => x.mode === mode)
  if (!m) return '-'
  const tag = m.feasible ? '' : ' (不可行)'
  return `${m.cost} 元 / ${m.duration_min} min${tag}`
}

async function loadC2cClusters() {
  setLoading('c2c', true)
  try {
    const res = await getFoodSupplyC2cClusters({ cluster_limit: 30 })
    c2cClusters.value = res.data
  } catch (e) {
    ElMessage.error('C 端聚类加载失败')
  } finally {
    setLoading('c2c', false)
  }
}

async function runGeocode() {
  setLoading('geocode', true)
  try {
    await geocodeFoodSupplyC2c({ geocode_limit: 5, provider: 'auto', persist: false })
    await loadC2cClusters()
    ElMessage.success('地理编码完成（provider 不可用时走本地区域中心兜底）')
  } catch (e) {
    ElMessage.error('地理编码失败')
  } finally {
    setLoading('geocode', false)
  }
}

async function loadLastMile() {
  setLoading('lastMile', true)
  try {
    const res = await optimizeFoodSupplyLastMile({ cluster_limit: 10, persist: false })
    lastMileResult.value = res.data
  } catch (e) {
    ElMessage.error('无人机最后一公里加载失败')
  } finally {
    setLoading('lastMile', false)
  }
}

async function loadOrchardTimeseries() {
  setLoading('orchard', true)
  try {
    const res = await getFoodSupplyOrchardTimeseries()
    orchardSeries.value = res.data
  } catch (e) {
    ElMessage.error('果园时序加载失败')
  } finally {
    setLoading('orchard', false)
  }
}

async function loadOrchardForecast() {
  setLoading('forecast', true)
  try {
    const res = await getFoodSupplyOrchardForecast({ horizon: 14, freshness_days: 4 })
    orchardForecast.value = res.data
  } catch (e) {
    ElMessage.error('需求预测加载失败')
  } finally {
    setLoading('forecast', false)
  }
}

async function runMultimodal() {
  setLoading('multimodal', true)
  try {
    const res = await optimizeFoodSupplyMultimodal({ cluster_limit: 8, persist: false })
    multimodalResult.value = res.data
  } catch (e) {
    ElMessage.error('多式联运加载失败')
  } finally {
    setLoading('multimodal', false)
  }
}

async function runDispatchFresh() {
  setLoading('dispatchFresh', true)
  try {
    const res = await optimizeFoodSupplyDispatchFresh({ wave_date: '06-01', store_limit: 8, time_window_hours: 48, freshness_window_days: 4, persist: false })
    dispatchFreshResult.value = res.data
  } catch (e) {
    ElMessage.error('鲜度调度加载失败')
  } finally {
    setLoading('dispatchFresh', false)
  }
}

async function issueTrace() {
  setLoading('trace', true)
  try {
    const res = await issueFoodSupplyTrace({ ...traceInput.value })
    traceResult.value = res.data
    ElMessage.success('追溯码已签发')
  } catch (e) {
    ElMessage.error('追溯签发失败')
  } finally {
    setLoading('trace', false)
  }
}

async function loadScenariosCompare() {
  setLoading('scenario', true)
  try {
    const res = await compareFoodSupplyScenarios({})
    scenarioCompare.value = res.data
  } catch (e) {
    ElMessage.error('场景对比加载失败')
  } finally {
    setLoading('scenario', false)
  }
}

function formatMultimodalMode(row, mode) {
  const m = (row.modes || []).find((x) => x.mode === mode)
  if (!m) return '-'
  const tag = m.feasible ? '' : ' (不可行)'
  return `${m.cost} 元 / ${m.duration_min} min${tag}`
}

function createProjection(nodes) {
  const positioned = nodes.filter((item) => item.lon != null && item.lat != null)
  const lons = positioned.map((item) => Number(item.lon))
  const lats = positioned.map((item) => Number(item.lat))
  const minLon = Math.min(...lons)
  const maxLon = Math.max(...lons)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const lonSpan = Math.max(maxLon - minLon, 0.000001)
  const latSpan = Math.max(maxLat - minLat, 0.000001)
  const project = (point) => ({
    x: 40 + ((Number(point.lon) - minLon) / lonSpan) * 720,
    y: 420 - ((Number(point.lat) - minLat) / latSpan) * 360,
  })
  return {
    nodes: positioned.map((item) => ({
      ...item,
      ...project(item),
    })),
    project,
  }
}

function renderNetworkChart() {
  if (!networkChartRef.value || !network.value?.nodes?.length) return
  if (!networkChart) networkChart = echarts.init(networkChartRef.value)
  const projection = createProjection(network.value.nodes)
  const nodes = projection.nodes
  const edges = network.value.edges || []
  const categories = [
    { name: '果园' },
    { name: '仓/中转' },
    { name: 'B端门店' },
    { name: '机场' },
    { name: '路径预览' },
  ]
  const categoryOf = (type) => {
    if (type === 'orchard') return 0
    if (type === 'facility') return 1
    if (type === 'b_store') return 2
    return 3
  }
  const activePolyline = displayRoute.value?.polyline || []
  const routePoints = activePolyline.map((point, index) => ({
    id: `route-preview-${index}`,
    name: index === 0 ? '路径起点' : index === activePolyline.length - 1 ? '路径终点' : `路径点 ${index}`,
    node_type: 'route_preview',
    category: 4,
    ...projection.project(point),
    symbolSize: index === 0 || index === activePolyline.length - 1 ? 13 : 7,
    itemStyle: { color: '#ffcf5a', borderColor: '#fff7d1', borderWidth: 1 },
    label: { show: false },
    value: [point.lon, point.lat],
  }))
  const routeLinks = routePoints.slice(1).map((point, index) => ({
    source: routePoints[index].id,
    target: point.id,
    edge_type: 'route_preview',
    distance_km: displayRoute.value?.distance_km,
    lineStyle: { color: '#ffcf5a', width: 4, opacity: 0.9, curveness: 0 },
  }))
  networkChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (params) => {
        const data = params.data || {}
        return `${data.name || ''}<br/>${data.node_type || data.edge_type || ''}<br/>${data.distance_km ? `${data.distance_km} km` : ''}`
      },
    },
    legend: {
      bottom: 4,
      textStyle: { color: '#b9cad8' },
      data: categories.map((item) => item.name),
    },
    series: [
      {
        type: 'graph',
        layout: 'none',
        roam: true,
        data: [
          ...nodes.map((item) => ({
          id: item.node_code,
          name: item.name,
          node_type: item.node_type,
          category: categoryOf(item.node_type),
          x: item.x,
          y: item.y,
          symbolSize: item.node_type === 'facility' ? 24 : item.node_type === 'orchard' ? 20 : 11,
          value: [item.lon, item.lat],
          })),
          ...routePoints,
        ],
        links: [
          ...edges.map((item) => ({
          source: item.source,
          target: item.target,
          edge_type: item.edge_type,
          distance_km: item.distance_km,
          })),
          ...routeLinks,
        ],
        categories,
        label: { show: true, color: '#ecf7ff', fontSize: 10, position: 'right' },
        lineStyle: { color: 'rgba(0, 212, 255, 0.35)', width: 1.3, curveness: 0.18 },
        itemStyle: {
          borderColor: 'rgba(255,255,255,0.5)',
          borderWidth: 1,
        },
      },
    ],
  }, true)
}

function renderParetoChart() {
  if (!paretoChartRef.value || !paretoResult.value?.pareto_front?.length) return
  if (!paretoChart) paretoChart = echarts.init(paretoChartRef.value)
  const data = paretoResult.value.pareto_front
  paretoChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (params) => {
        const row = params.data.raw
        return `${row.scenario}<br/>成本 ${formatMoney(row.cost)}<br/>碳排 ${row.carbon_kg} kg<br/>服务 ${Math.round(row.service_level * 100)}%`
      },
    },
    xAxis: {
      name: '成本',
      axisLabel: { color: '#a9bccb' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
    },
    yAxis: {
      name: '碳排',
      axisLabel: { color: '#a9bccb' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
    },
    series: [
      {
        type: 'scatter',
        data: data.map((item) => ({
          value: [item.cost, item.carbon_kg],
          symbolSize: 16 + item.service_level * 16,
          raw: item,
        })),
        itemStyle: { color: '#11e0b7' },
      },
    ],
  }, true)
}

function handleTabChange(name) {
  nextTick(() => {
    if (name === 'network') renderNetworkChart()
    if (name === 'compare') renderParetoChart()
    if (name === 'map') loadFoodMap()
  })
}

async function loadAll() {
  await loadSummary()
  await Promise.all([validateImport(), loadNetwork(), loadOsmCacheStatus(), runDispatch(), runNetworkDesign(), runPareto(), runSolverCompare(), loadC2cClusters(), loadLastMile(), loadOrchardTimeseries(), loadOrchardForecast(), runMultimodal(), runDispatchFresh(), loadScenariosCompare()])
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.food-map { height: 420px; width: 100%; border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.12); }
.map-legend { display: flex; gap: 16px; margin-top: 8px; flex-wrap: wrap; }
.legend-item { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; }
.legend-item .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
.dot-orchard { background: #52c41a; }
.dot-facility { background: #1890ff; }
.dot-bstore { background: #faad14; }
.dot-airport { background: #722ed1; }
.dot-cluster { background: #13c2c2; }
.food-case {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.food-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 18px;
  padding: 24px;
  border: 1px solid rgba(0, 212, 255, 0.18);
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(8, 22, 38, 0.94), rgba(9, 38, 43, 0.82));
}

.food-hero h1 {
  margin: 8px 0;
  color: #ecf7ff;
  font-size: 28px;
}

.food-hero p {
  margin: 0;
  max-width: 760px;
  color: rgba(236, 247, 255, 0.68);
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.truth-strip {
  border-radius: 8px;
}

.truth-line {
  line-height: 1.7;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.kpi-card,
.case-panel {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  background: rgba(7, 17, 31, 0.74);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.18);
}

.kpi-card {
  padding: 16px;
}

.kpi-card span,
.kpi-card small {
  display: block;
  color: rgba(236, 247, 255, 0.56);
}

.kpi-card strong {
  display: block;
  margin: 8px 0 4px;
  color: #ecf7ff;
  font-size: 26px;
}

.case-tabs {
  min-width: 0;
}

.two-column {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 16px;
}

.case-panel {
  min-width: 0;
  padding: 18px;
}

.panel-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.panel-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.panel-title h2,
.model-panel h2 {
  margin: 0;
  color: #ecf7ff;
  font-size: 18px;
}

.network-chart,
.pareto-chart {
  width: 100%;
  height: 460px;
}

.route-workbench {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  gap: 16px;
  align-items: stretch;
}

.route-controls {
  min-width: 0;
  padding: 14px;
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.035);
}

.route-controls :deep(.el-select) {
  width: 100%;
}

.route-status {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.route-status div {
  padding: 12px;
  border-radius: 8px;
  background: rgba(0, 212, 255, 0.08);
}

.route-status span,
.route-status small {
  display: block;
  color: rgba(236, 247, 255, 0.62);
}

.route-status strong {
  display: block;
  margin: 5px 0;
  color: #ffcf5a;
  font-size: 18px;
}

.route-meta {
  margin-top: 14px;
}

.route-compare-insight {
  margin-top: 14px;
  padding: 12px;
  border: 1px solid rgba(17, 224, 183, 0.18);
  border-radius: 8px;
  background: rgba(17, 224, 183, 0.07);
}

.route-compare-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.route-compare-stat {
  min-width: 0;
  padding: 10px;
  border-radius: 8px;
  background: rgba(4, 12, 22, 0.45);
}

.route-compare-stat span,
.route-compare-stat small {
  display: block;
  color: rgba(236, 247, 255, 0.62);
  line-height: 1.5;
}

.route-compare-stat strong {
  display: block;
  margin: 4px 0;
  color: #ecf7ff;
  font-size: 18px;
  word-break: break-word;
}

.route-compare-insight p {
  margin: 10px 0 0;
  color: rgba(236, 247, 255, 0.74);
  line-height: 1.7;
}

.route-score-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.route-score-card {
  min-width: 0;
  padding: 10px;
  border: 1px solid rgba(0, 212, 255, 0.14);
  border-radius: 8px;
  background: rgba(4, 12, 22, 0.52);
  color: #ecf7ff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease;
}

.route-score-card.active {
  border-color: rgba(255, 207, 90, 0.72);
  background: rgba(255, 207, 90, 0.1);
}

.route-score-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.route-score-head span {
  color: rgba(236, 247, 255, 0.74);
  font-weight: 700;
}

.route-score-head strong,
.route-score-value {
  color: #ffcf5a;
  font-weight: 800;
}

.route-score-breakdown {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 4px 8px;
  margin-top: 8px;
  color: rgba(236, 247, 255, 0.68);
  font-size: 12px;
  line-height: 1.5;
}

.route-score-card small {
  display: block;
  margin-top: 8px;
  color: rgba(236, 247, 255, 0.58);
}

.route-compare-table {
  margin-top: 14px;
  border-radius: 8px;
  overflow: hidden;
}

.route-history-panel {
  margin-top: 14px;
  padding: 12px;
  border: 1px solid rgba(0, 212, 255, 0.14);
  border-radius: 8px;
  background: rgba(4, 12, 22, 0.42);
}

.history-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.history-title span {
  color: #ecf7ff;
  font-weight: 700;
}

.history-title small {
  color: rgba(236, 247, 255, 0.55);
}

.route-history-table {
  border-radius: 8px;
  overflow: hidden;
}

.route-compare-table :deep(.el-table__row) {
  cursor: pointer;
}

.route-compare-table :deep(.selected-route-row td) {
  background: rgba(255, 207, 90, 0.12) !important;
}

.provider-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.provider-cell strong {
  color: #ecf7ff;
  font-weight: 700;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.model-grid div {
  padding: 16px;
  border: 1px solid rgba(0, 212, 255, 0.13);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
}

.model-grid h3 {
  margin: 0 0 10px;
  color: #11e0b7;
  font-size: 15px;
}

.model-grid p {
  margin: 0;
  color: rgba(236, 247, 255, 0.72);
  line-height: 1.8;
}

.control-form {
  margin-bottom: 12px;
}

.mini-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
}

.mini-summary span {
  padding: 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: #ecf7ff;
  text-align: center;
}

.solver-panel {
  margin-top: 16px;
}

.panel-subtitle {
  margin: 6px 0 0;
  color: rgba(236, 247, 255, 0.56);
  font-size: 13px;
}

.solver-summary {
  margin-bottom: 14px;
}

.metric-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: rgba(236, 247, 255, 0.74);
  font-size: 12px;
}

.metric-line span {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(0, 212, 255, 0.08);
}

.agent-panel {
  max-width: 980px;
}

.agent-answer {
  margin-top: 16px;
  padding: 16px;
  min-height: 220px;
  border-radius: 8px;
  background: #f5f8fb;
  color: #172435;
}

.agent-answer pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  line-height: 1.8;
}

:deep(.el-tabs__item) {
  color: rgba(236, 247, 255, 0.64);
}

:deep(.el-tabs__item.is-active) {
  color: #11e0b7;
}

:deep(.el-descriptions__label),
:deep(.el-descriptions__content) {
  color: #1d2c3a;
}

@media (max-width: 1280px) {
  .kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .two-column,
  .model-grid,
  .route-workbench {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .food-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .kpi-grid,
  .mini-summary,
  .route-compare-stats,
  .route-score-list {
    grid-template-columns: 1fr;
  }

  .network-chart,
  .pareto-chart {
    height: 360px;
  }
}
</style>
