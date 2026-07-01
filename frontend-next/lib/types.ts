export type ProviderStatus = "ok" | "degraded" | "failed" | "unknown" | string;

export interface TruthMetadata {
  data_source?: string | null;
  distance_source?: string | null;
  path_source?: string | null;
  provider_status?: ProviderStatus | null;
  fallback_reason?: string | null;
  authenticity_level?: string | null;
}

export interface MetricSet {
  mae?: number | null;
  rmse?: number | null;
  mape?: number | null;
  sample_count?: number | null;
}

export interface PredictionHealth extends TruthMetadata {
  success?: boolean;
  model_status?: string;
  summary?: {
    total_records?: number;
    demand_records?: number;
    eta_records?: number;
    delay_records?: number;
    cost_records?: number;
    status_counts?: Record<string, number>;
  };
  readiness?: Record<string, { ready?: boolean; records?: number; status?: string }>;
}

export interface PredictionBaseline extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  summary?: {
    ready_tasks?: string[];
    horizon_days?: number;
    limit?: number;
  };
  results?: Record<
    string,
    TruthMetadata & {
      task?: string;
      model?: string;
      metrics?: MetricSet;
      forecast?: Array<{ date?: string; predicted_orders?: number }>;
    }
  >;
}

export interface PredictionForecast extends TruthMetadata {
  success?: boolean;
  task?: string;
  prediction_target?: string;
  model?: string;
  model_stage?: string;
  metrics?: MetricSet;
  feature_summary?: {
    daily_points?: number;
    training_points?: number;
    test_points?: number;
    city?: string | null;
    date_range?: { start?: string; end?: string };
  };
  forecast?: Array<{ date?: string; predicted_orders?: number }>;
  backtest?: Array<{ date?: string; actual_orders?: number; predicted_orders?: number }>;
}

export interface PredictionTimeSeriesBenchmark extends TruthMetadata {
  success?: boolean;
  task?: string;
  prediction_target?: string;
  model_family?: string;
  benchmark_version?: string;
  series_summary?: {
    task?: string;
    city?: string | null;
    daily_points?: number;
    date_range?: { start?: string | null; end?: string | null };
    target_min?: number | null;
    target_max?: number | null;
    target_avg?: number | null;
    zero_value_days?: number;
  };
  backtest?: {
    test_days?: number;
    train_points?: number;
    test_points?: number;
    models?: Array<{
      model_id?: string;
      model_family?: string;
      metrics?: MetricSet;
      backtest_rows?: Array<{
        date?: string;
        actual?: number;
        predicted?: number;
        absolute_error?: number;
      }>;
      training_note?: string;
    }>;
    best_model?: {
      model_id?: string;
      model_family?: string;
      metrics?: MetricSet;
      training_note?: string;
    };
  };
  forecast?: Array<{
    date?: string;
    predicted_value?: number;
    method?: string;
  }>;
  deep_learning_readiness?: {
    ready?: boolean;
    status?: string;
    daily_points?: number;
    sequence_length?: number;
    training_windows?: number;
    minimum_training_windows?: number;
    candidate_models?: string[];
    recommended_next_step?: string;
    deployment_boundary?: string;
  };
  truth_contract?: Record<string, unknown>;
}

export interface PredictionCapacityGapForecast extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  forecast_version?: string;
  summary?: {
    daily_points?: number;
    horizon_days?: number;
    test_days?: number;
    city?: string | null;
    shortage_days?: number;
    max_weight_gap_kg?: number;
    max_volume_gap_m3?: number;
    avg_weight_utilization?: number | null;
  };
  fleet_capacity?: {
    vehicle_source?: string;
    capacity_source?: string;
    include_all_vehicles?: boolean;
    available_vehicles?: number;
    total_capacity_weight_tons?: number;
    total_capacity_weight_kg?: number;
    total_capacity_volume_m3?: number;
    vehicles?: Array<{
      id?: number;
      plate_number?: string;
      status?: string;
      capacity_weight_tons?: number;
      capacity_volume_m3?: number;
    }>;
  };
  models?: Record<
    string,
    {
      model_id?: string;
      model_family?: string;
      metrics?: MetricSet;
      fallback_reason?: string;
      test_points?: number;
      candidate_count?: number;
    }
  >;
  forecast?: Array<{
    date?: string;
    predicted_shipments?: number;
    predicted_weight_kg?: number;
    predicted_volume_m3?: number;
    capacity_weight_kg?: number;
    capacity_volume_m3?: number;
    weight_gap_kg?: number;
    volume_gap_m3?: number;
    weight_utilization?: number | null;
    volume_utilization?: number | null;
    status?: string;
  }>;
  deep_learning_readiness?: PredictionTimeSeriesBenchmark["deep_learning_readiness"];
  recommendations?: string[];
  truth_contract?: Record<string, unknown>;
}

export interface PredictionCostVolatilityForecast extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  forecast_version?: string;
  summary?: {
    daily_points?: number;
    horizon_days?: number;
    test_days?: number;
    city?: string | null;
    risk_days?: number;
    high_risk_days?: number;
    recent_volatility_cv?: number | null;
    volatility_threshold?: number | null;
    unit_cost_threshold?: number | null;
    avg_unit_cost_per_kg?: number | null;
  };
  models?: Record<
    string,
    {
      model_id?: string;
      model_family?: string;
      metrics?: MetricSet;
      fallback_reason?: string;
      test_points?: number;
      candidate_count?: number;
    }
  >;
  forecast?: Array<{
    date?: string;
    predicted_avg_freight?: number;
    predicted_unit_cost_per_kg?: number;
    predicted_total_freight?: number;
    unit_cost_threshold?: number | null;
    expected_volatility_cv?: number | null;
    volatility_threshold?: number | null;
    unit_cost_pressure?: number | null;
    risk_score?: number;
    risk_level?: string;
    method?: Record<string, string>;
  }>;
  deep_learning_readiness?: PredictionTimeSeriesBenchmark["deep_learning_readiness"];
  recommendations?: string[];
  truth_contract?: Record<string, unknown>;
}

export interface PredictionScorecard extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  scorecard_version?: string;
  summary?: {
    readiness_score?: number;
    status?: string;
    horizon_days?: number;
    test_days?: number;
    city?: string | null;
    ready_tasks?: string[];
    risk_summary?: {
      capacity_shortage_days?: number;
      cost_risk_days?: number;
      cost_high_risk_days?: number;
      dl_shadow_ready?: boolean;
    };
  };
  components?: Array<{
    id?: string;
    label?: string;
    score?: number;
    status?: string;
    details?: Record<string, unknown>;
  }>;
  gates?: Array<{
    id?: string;
    passed?: boolean;
    detail?: string;
  }>;
  recommendations?: string[];
  evidence?: Record<string, unknown>;
  truth_contract?: Record<string, unknown>;
}

export interface PredictionFeatureDataset extends TruthMetadata {
  success?: boolean;
  task?: string;
  dataset_name?: string;
  target_definition?: Record<string, unknown>;
  feature_schema?: Record<string, unknown> | Array<Record<string, unknown>>;
  row_count?: number;
  returned_rows?: number;
  truncated?: boolean;
  rows?: Array<Record<string, unknown>>;
  summary?: Record<string, unknown>;
}

export interface PredictionModelStatus extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  model_stage?: string;
  model_count?: number;
  models?: Array<{
    model_id?: string;
    task?: string;
    model_type?: string;
    trained_at?: string;
    metrics?: MetricSet;
  }>;
  latest_by_task?: Record<string, { model_id?: string; model_type?: string; metrics?: MetricSet }>;
}

export interface AiAnomalyHealth extends TruthMetadata {
  success?: boolean;
  model_stage?: string;
  summary?: {
    total_records?: number;
    cost_records?: number;
    geo_ready_records?: number;
    eta_records?: number;
    delay_records?: number;
    status_counts?: Record<string, number>;
  };
  readiness?: Record<string, unknown>;
}

export interface AiAnomalyDetect extends TruthMetadata {
  success?: boolean;
  detector_family?: string;
  summary?: {
    records_scanned?: number;
    anomaly_count?: number;
    anomaly_rate?: number;
    by_type?: Record<string, number>;
    by_level?: Record<string, number>;
    top_od_lanes?: Array<{ group_key?: string; shipment_count?: number }>;
  };
  anomalies?: Array<{
    anomaly_id?: string;
    anomaly_type?: string;
    level?: string;
    score?: number;
    order_id?: string | null;
    origin_city?: string | null;
    destination_city?: string | null;
    method?: string;
    explanation?: string;
  }>;
  diagnostics?: {
    ml_detector?: {
      enabled?: boolean;
      used?: boolean;
      detector?: string;
      fallback_reason?: string | null;
    };
  };
}

export interface AiAnomalyScorecard extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  scorecard_version?: string;
  summary?: {
    readiness_score?: number;
    status?: string;
    records_scanned?: number;
    anomaly_count?: number;
    high_risk_count?: number;
    anomaly_rate?: number;
    tasks?: string[];
  };
  components?: Array<{
    id?: string;
    label?: string;
    score?: number;
    status?: string;
    details?: Record<string, unknown>;
  }>;
  gates?: Array<{
    id?: string;
    passed?: boolean;
    detail?: string;
  }>;
  recommendations?: string[];
  evidence?: Record<string, unknown>;
  truth_contract?: Record<string, unknown>;
}

export interface OperationsSummary extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  summary_version?: string;
  summary?: {
    records_scanned?: number;
    limit?: number;
    city?: string | null;
    trend_days?: number;
    lane_limit?: number;
    status_counts?: Record<string, number>;
  };
  kpis?: {
    total_shipments?: number;
    freight_records?: number;
    freight_coverage?: number | null;
    total_freight?: number;
    avg_freight_per_shipment?: number | null;
    avg_freight_per_paid_shipment?: number | null;
    total_weight_kg?: number;
    total_volume_m3?: number;
    freight_per_kg?: number | null;
    freight_per_m3?: number | null;
    delivered_shipments?: number;
    delivery_completion_rate?: number | null;
    eta_records?: number;
    on_time_shipments?: number;
    on_time_rate?: number | null;
    avg_transit_hours?: number | null;
    avg_delay_minutes?: number | null;
    exception_shipments?: number;
    exception_rate?: number | null;
  };
  cost_components?: Array<{
    component?: string;
    amount?: number;
    share?: number | null;
    source?: string;
  }>;
  trend?: Array<{
    date?: string;
    shipment_count?: number;
    total_freight?: number;
    freight_per_kg?: number | null;
  }>;
  top_lanes?: Array<{
    lane?: string;
    origin_city?: string;
    destination_city?: string;
    shipment_count?: number;
    total_freight?: number;
    freight_share?: number | null;
    avg_freight?: number | null;
    freight_per_kg?: number | null;
    avg_transit_hours?: number | null;
    on_time_rate?: number | null;
  }>;
  city_breakdown?: Array<{
    city?: string;
    shipment_count?: number;
    inbound_count?: number;
    outbound_count?: number;
    total_freight?: number;
    freight_per_kg?: number | null;
  }>;
  recommendations?: string[];
  truth_contract?: Record<string, unknown>;
}

export interface DispatchHealth extends TruthMetadata {
  success?: boolean;
  data_source?: string | null;
  dispatchable_orders?: number;
  message?: string;
  vehicle_source?: {
    available_vehicles?: number;
    total_capacity_weight_tons?: number;
  };
  diagnostics?: Record<string, unknown>;
}

export interface DispatchAlgorithm {
  id?: string;
  name?: string;
  description?: string;
  best_for?: string;
  performance?: string;
}

export interface DispatchAlgorithms extends TruthMetadata {
  success?: boolean;
  algorithms?: DispatchAlgorithm[];
  weight_options?: Record<string, string>;
}

export interface DispatchOrder {
  id?: number | string;
  ref?: string;
  order_number?: string;
  customer_name?: string | null;
  origin_name?: string | null;
  destination_name?: string | null;
  origin_city?: string | null;
  destination_city?: string | null;
  weight_kg?: number | null;
  weight_tons?: number | null;
  volume_m3?: number | null;
  data_source?: string | null;
}

export interface DispatchVehicle {
  id?: number | string;
  plate_number?: string;
  vehicle_type?: string;
  capacity_weight_tons?: number | null;
  capacity_volume_m3?: number | null;
  status?: string;
  data_source?: string | null;
}

export interface DispatchWave extends TruthMetadata {
  success?: boolean;
  wave?: {
    id?: string;
    limit?: number;
    filters?: Record<string, unknown>;
    candidate_orders?: number;
    available_vehicles?: number;
    total_weight_kg?: number;
    total_volume_m3?: number;
    orders?: DispatchOrder[];
    vehicles?: DispatchVehicle[];
    diagnostics?: Record<string, unknown>;
  };
}

export interface DispatchSummary extends TruthMetadata {
  total_orders?: number;
  assigned_orders?: number;
  unassigned_orders?: number;
  vehicles_used?: number;
  total_orders_assigned?: number;
  total_orders_unassigned?: number;
  total_vehicles_used?: number;
  total_distance?: number;
  total_distance_km?: number;
  total_duration?: number;
  total_duration_min?: number;
  total_cost?: number;
  avg_cost_per_order?: number;
  average_cost_per_order?: number;
  average_load_utilization?: number;
  optimization_score?: number;
  route_truth?: DispatchRouteTruth;
}

export interface DispatchRouteLeg extends TruthMetadata {
  sequence?: number;
  order_ref?: string;
  order_number?: string;
  from_name?: string | null;
  to_name?: string | null;
  from_lng?: number | null;
  from_lat?: number | null;
  to_lng?: number | null;
  to_lat?: number | null;
  distance_km?: number | null;
  duration_minutes?: number | null;
  cost?: number | null;
  duration_source?: string | null;
}

export interface DispatchRouteTruth extends TruthMetadata {
  leg_type?: string;
  leg_count?: number;
  assignment_leg_count?: number;
  estimated_leg_count?: number;
  distance_source_counts?: Record<string, number>;
  duration_source_counts?: Record<string, number>;
  provider_status_counts?: Record<string, number>;
  fallback_reason_counts?: Record<string, number>;
  note?: string;
}

export interface DispatchPlan {
  vehicle_id?: number | string;
  vehicle_info?: DispatchVehicle;
  orders?: DispatchOrder[];
  route_sequence?: Array<Record<string, unknown>>;
  route_legs?: DispatchRouteLeg[];
  route_truth?: DispatchRouteTruth;
  total_distance?: number;
  total_duration?: number;
  total_cost?: number;
  score?: number;
  load_utilization?: number;
  volume_utilization?: number;
  suggestions?: string[];
}

export interface DispatchPreview extends TruthMetadata {
  success?: boolean;
  plans?: DispatchPlan[];
  unassigned_orders?: Array<DispatchOrder & { reason?: string; reason_code?: string }>;
  summary?: DispatchSummary;
  diagnostics?: Record<string, unknown>;
  solver?: string;
  requested_solver?: string;
  solver_status?: Record<string, unknown>;
  algorithm?: string;
  route_truth?: DispatchRouteTruth;
  wave?: {
    filters?: Record<string, unknown>;
    limit?: number;
    candidate_orders?: number;
    available_vehicles?: number;
  };
  solve_time_ms?: number;
  scenario_id?: number;
  scenario_code?: string;
  ai_shadow?: {
    mode?: string;
    enabled?: boolean;
    risk_score?: number;
    models?: Record<string, string>;
    top_lanes?: Array<{ lane?: string; orders?: number }>;
    recommendations?: string[];
  };
}

export interface DispatchScenarioList extends TruthMetadata {
  success?: boolean;
  scenarios?: Array<{
    id?: number;
    scenario_code?: string;
    status?: string;
    created_at?: string;
    applied_at?: string | null;
    summary?: DispatchSummary;
    solver?: string;
    data_source?: string;
    authenticity_level?: string;
  }>;
}

export interface DispatchScenarioAssignment {
  id?: number;
  vehicle_id?: number;
  vehicle_plate?: string | null;
  order_source?: string | null;
  order_ref?: string | null;
  order_number?: string | null;
  sequence_index?: number;
  assignment_status?: string | null;
  weight_kg?: number | null;
  volume_m3?: number | null;
  distance_km?: number | null;
  duration_min?: number | null;
  cost?: number | null;
  route?: Array<Record<string, unknown>>;
  diagnostics?: {
    load_utilization?: number | null;
    volume_utilization?: number | null;
    route_truth?: DispatchRouteTruth;
    [key: string]: unknown;
  };
}

export interface DispatchScenarioDetail extends TruthMetadata {
  success?: boolean;
  error?: string;
  scenario?: {
    id?: number;
    scenario_code?: string;
    name?: string;
    status?: string;
    solver?: string;
    data_source?: string | null;
    distance_source?: string | null;
    provider_status?: ProviderStatus | null;
    authenticity_level?: string | null;
    fallback_reason?: string | null;
    wave_filters?: Record<string, unknown>;
    summary?: DispatchSummary;
    diagnostics?: Record<string, unknown>;
    ai_shadow?: DispatchPreview["ai_shadow"];
    created_at?: string | null;
    applied_at?: string | null;
    assignments?: DispatchScenarioAssignment[];
  };
}

export interface DispatchSolverComparison extends TruthMetadata {
  success?: boolean;
  results?: Array<{
    solver?: string;
    available?: boolean;
    status?: string;
    assigned_orders?: number;
    unassigned_orders?: number;
    vehicles_used?: number;
    total_distance?: number;
    total_cost?: number;
    solve_time_ms?: number;
    authenticity_level?: string;
  }>;
  best_solver?: string | null;
  note?: string;
}

export interface DispatchLearningDataset extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  dataset_version?: string;
  mode?: string;
  filters?: {
    scenario_ids?: number[];
    status?: string | null;
    include_preview?: boolean;
    scenario_limit?: number;
    row_limit?: number;
  };
  summary?: {
    scenario_count?: number;
    assignment_count?: number;
    row_count?: number;
    scenario_status_counts?: Record<string, number>;
    unique_vehicles?: number;
    unique_orders?: number;
    route_truth_rows?: number;
    route_truth_coverage?: number;
    distance_source_counts?: Record<string, number>;
    provider_status_counts?: Record<string, number>;
    fallback_reason_counts?: Record<string, number>;
    avg_reward_proxy?: number;
    avg_load_utilization?: number;
    avg_volume_utilization?: number;
    truncated?: boolean;
  };
  readiness?: {
    ready?: boolean;
    status?: string;
    reason?: string | null;
    minimum_rows?: number;
    row_count?: number;
  };
  target_definition?: {
    task?: string;
    action?: string;
    target?: string;
    hard_constraints_note?: string;
    reward_proxy_formula?: string;
  };
  feature_schema?: Array<{
    name?: string;
    type?: string;
    description?: string;
  }>;
  rows?: Array<{
    scenario_id?: number;
    scenario_code?: string;
    scenario_status?: string;
    solver?: string;
    assignment_id?: number;
    vehicle_id?: number;
    order_ref?: string;
    action?: Record<string, unknown>;
    features?: Record<string, number | string | null>;
    target?: {
      reward_proxy?: number;
      target_type?: string;
      [key: string]: unknown;
    };
    truth?: TruthMetadata & { route_truth?: DispatchRouteTruth };
  }>;
  truth_contract?: Record<string, unknown>;
}

export interface DispatchPolicyScorer extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  scorer_version?: string;
  dataset_version?: string;
  mode?: string;
  dataset_summary?: DispatchLearningDataset["summary"];
  filters?: DispatchLearningDataset["filters"];
  readiness?: DispatchLearningDataset["readiness"] & {
    policy_rows?: number;
    top_k?: number;
  };
  target_definition?: DispatchLearningDataset["target_definition"] & {
    scoring_note?: string;
  };
  policies?: Array<{
    policy_id?: string;
    policy_family?: string;
    name?: string;
    description?: string;
    deployable?: boolean;
    row_count?: number;
    top_k?: number;
    top_k_reward_proxy?: number;
    discounted_reward_proxy?: number;
    policy_score?: number;
    score_delta_vs_baseline?: number;
    avg_load_utilization?: number;
    avg_volume_utilization?: number;
    avg_cost?: number;
    avg_risk_score?: number;
    avg_provider_reliability?: number;
    top_actions?: Array<{
      rank?: number;
      scenario_id?: number;
      order_ref?: string;
      vehicle_id?: number;
      reward_proxy?: number;
      provider_status?: ProviderStatus;
    }>;
  }>;
  best_policy?: NonNullable<DispatchPolicyScorer["policies"]>[number] | null;
  truth_contract?: Record<string, unknown>;
}

export interface DispatchRewardModel extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  model_version?: string;
  dataset_version?: string;
  mode?: string;
  dataset_summary?: DispatchLearningDataset["summary"];
  filters?: DispatchLearningDataset["filters"];
  readiness?: DispatchLearningDataset["readiness"] & {
    train_rows?: number;
    test_rows?: number;
    feature_count?: number;
  };
  feature_names?: string[];
  metrics?: {
    train?: MetricSet & { r2?: number | null };
    test?: MetricSet & { r2?: number | null };
    all?: MetricSet & { r2?: number | null };
    rank_accuracy?: {
      pair_count?: number;
      correct_pairs?: number;
      accuracy?: number | null;
    };
  };
  model?: {
    type?: string;
    intercept?: number;
    coefficients?: Record<string, number>;
    feature_means?: Record<string, number>;
    feature_scales?: Record<string, number>;
    feature_importance?: Array<{
      feature?: string;
      weight?: number;
      abs_weight?: number;
    }>;
    training_note?: string;
  } | null;
  predictions?: Array<{
    scenario_id?: number;
    assignment_id?: number;
    order_ref?: string;
    vehicle_id?: number;
    actual_reward_proxy?: number;
    predicted_reward_proxy?: number;
    error?: number;
    provider_status?: ProviderStatus;
    data_source?: string;
  }>;
  truth_contract?: Record<string, unknown>;
}

export interface DispatchRedispatchSimulator extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  simulator_version?: string;
  dataset_version?: string;
  mode?: string;
  filters?: DispatchLearningDataset["filters"];
  disruption?: {
    profile?: string;
    delay_minutes?: number;
    delay_vehicle_ids?: number[];
    unavailable_vehicle_ids?: number[];
    priority_order_refs?: string[];
    cost_multiplier?: number;
    provider_degradation?: boolean;
    reliability_drop?: number;
  };
  readiness?: DispatchLearningDataset["readiness"] & {
    top_k?: number;
  };
  summary?: {
    row_count?: number;
    impacted_assignments?: number;
    held_for_reassignment?: number;
    avg_original_reward_proxy?: number;
    avg_simulated_reward_proxy?: number;
    avg_reward_delta?: number;
    best_policy_id?: string | null;
    best_policy_score?: number | null;
    best_policy_delta_vs_baseline?: number | null;
    simulation_note?: string;
  };
  policies?: DispatchPolicyScorer["policies"];
  best_policy?: NonNullable<DispatchPolicyScorer["policies"]>[number] | null;
  impacts?: Array<{
    scenario_id?: number;
    assignment_id?: number;
    order_ref?: string;
    vehicle_id?: number;
    vehicle_plate?: string | null;
    original_reward_proxy?: number;
    simulated_reward_proxy?: number;
    reward_delta?: number;
    recommended_action?: string;
    impact_flags?: string[];
    provider_status?: ProviderStatus;
  }>;
  recommendations?: string[];
  truth_contract?: Record<string, unknown>;
}

export interface DispatchRedispatchProfiles extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  profile_version?: string;
  dataset_version?: string;
  mode?: string;
  filters?: DispatchLearningDataset["filters"];
  anomaly_summary?: {
    records_scanned?: number;
    anomaly_count?: number;
    anomaly_rate?: number;
    by_type?: Record<string, number>;
    by_level?: Record<string, number>;
    tasks?: string[];
  };
  readiness?: DispatchLearningDataset["readiness"] & {
    anomaly_count?: number;
    profile_count?: number;
  };
  profiles?: Array<{
    profile_id?: string;
    name?: string;
    description?: string;
    source?: string;
    confidence?: string;
    params?: {
      delay_minutes?: number;
      cost_multiplier?: number;
      provider_degradation?: boolean;
      reliability_drop?: number;
      priority_order_refs?: string[];
      top_k?: number;
    };
    evidence?: Record<string, unknown>;
  }>;
  truth_contract?: Record<string, unknown>;
}

export interface DispatchRedispatchScenarioGenerator extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  generator_version?: string;
  dataset_version?: string;
  profile_version?: string;
  mode?: string;
  filters?: DispatchLearningDataset["filters"];
  anomaly_summary?: DispatchRedispatchProfiles["anomaly_summary"];
  readiness?: DispatchLearningDataset["readiness"] & {
    profile_count?: number;
    generated_scenario_count?: number;
  };
  summary?: {
    generated_scenario_count?: number;
    profile_count?: number;
    row_count?: number;
    anomaly_count?: number;
    anomaly_by_type?: Record<string, number>;
    best_scenario_id?: string | null;
    avg_impacted_assignments?: number;
  };
  generated_scenarios?: Array<{
    scenario_id?: string;
    name?: string;
    description?: string;
    source?: string;
    confidence?: string;
    params?: NonNullable<DispatchRedispatchProfiles["profiles"]>[number]["params"] & {
      delay_vehicle_ids?: number[];
      unavailable_vehicle_ids?: number[];
    };
    evidence?: Record<string, unknown>;
    training_use?: string;
    simulation_summary?: DispatchRedispatchSimulator["summary"];
    best_policy?: DispatchRedispatchSimulator["best_policy"];
    impact_preview?: DispatchRedispatchSimulator["impacts"];
    recommendations?: string[];
    simulation_provider_status?: ProviderStatus;
    simulation_fallback_reason?: string | null;
  }>;
  truth_contract?: Record<string, unknown>;
}

export interface DispatchRlShadowRunner extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  runner_version?: string;
  generator_version?: string;
  dataset_version?: string;
  mode?: string;
  filters?: DispatchLearningDataset["filters"];
  readiness?: DispatchLearningDataset["readiness"] & {
    episode_count?: number;
    action_count?: number;
  };
  summary?: {
    episode_count?: number;
    action_count?: number;
    state_bucket_count?: number;
    avg_baseline_score?: number;
    avg_selected_score?: number;
    avg_score_delta_vs_baseline?: number;
    best_episode_id?: string | null;
    selected_action_counts?: Record<string, number>;
    deployable?: boolean;
  };
  state_schema?: string[];
  action_space?: string[];
  q_table?: Array<{
    state_bucket?: string;
    best_action?: string | null;
    best_q_value?: number | null;
    action_values?: Array<{
      action?: string;
      q_value?: number;
      sample_count?: number;
    }>;
  }>;
  episode_results?: Array<{
    episode_id?: string;
    state_bucket?: string;
    source?: string;
    confidence?: string;
    selected_action?: string;
    selected_policy_name?: string;
    baseline_action?: string;
    baseline_score?: number;
    selected_score?: number;
    score_delta_vs_baseline?: number;
    impacted_assignments?: number;
    held_for_reassignment?: number;
    avg_reward_delta?: number;
    policy_scores?: Array<{
      policy_id?: string;
      name?: string;
      deployable?: boolean;
      policy_score?: number;
      score_delta_vs_baseline?: number;
    }>;
  }>;
  truth_contract?: Record<string, unknown>;
}

export interface DispatchFittedQShadowModel extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  model_version?: string;
  runner_version?: string;
  generator_version?: string;
  dataset_version?: string;
  mode?: string;
  filters?: DispatchLearningDataset["filters"];
  readiness?: DispatchLearningDataset["readiness"] & {
    sample_count?: number;
    train_samples?: number;
    test_samples?: number;
    feature_count?: number;
    episode_count?: number;
    action_count?: number;
  };
  summary?: {
    sample_count?: number;
    episode_count?: number;
    action_count?: number;
    best_predicted_action_counts?: Record<string, number>;
    avg_predicted_q?: number;
    avg_actual_q?: number;
    deployable?: boolean;
  };
  feature_names?: string[];
  metrics?: {
    train?: MetricSet & { r2?: number | null };
    test?: MetricSet & { r2?: number | null };
    all?: MetricSet & { r2?: number | null };
    rank_accuracy?: {
      pair_count?: number;
      correct_pairs?: number;
      accuracy?: number | null;
    };
  };
  model?: {
    type?: string;
    intercept?: number;
    coefficients?: Record<string, number>;
    feature_means?: Record<string, number>;
    feature_scales?: Record<string, number>;
    feature_importance?: Array<{
      feature?: string;
      weight?: number;
      abs_weight?: number;
    }>;
    training_note?: string;
  } | null;
  recommendations?: Array<{
    episode_id?: string;
    state_bucket?: string;
    predicted_best_action?: string;
    predicted_best_policy_name?: string;
    predicted_best_q?: number;
    actual_best_action?: string;
    actual_best_q?: number;
    matches_actual_best?: boolean;
  }>;
  predictions?: Array<{
    episode_id?: string;
    state_bucket?: string;
    action?: string;
    policy_name?: string;
    actual_q?: number;
    predicted_q?: number;
    error?: number;
    score_delta_vs_baseline?: number;
  }>;
  truth_contract?: Record<string, unknown>;
}

export interface DispatchShadowBenchmark extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  benchmark_version?: string;
  mode?: string;
  filters?: DispatchLearningDataset["filters"];
  summary?: {
    component_count?: number;
    ready_component_count?: number;
    gate_count?: number;
    passed_gate_count?: number;
    readiness_score?: number;
    shadow_chain?: string[];
    deployable?: boolean;
  };
  components?: Array<{
    component_id?: string;
    name?: string;
    ready?: boolean;
    status?: string;
    reason?: string | null;
    provider_status?: ProviderStatus;
    authenticity_level?: string | null;
    metrics?: Record<string, unknown>;
  }>;
  gates?: Array<{
    gate_id?: string;
    passed?: boolean;
    reason?: string | null;
    evidence?: Record<string, unknown>;
  }>;
  recommendations?: string[];
  truth_contract?: Record<string, unknown>;
}

export interface DispatchShadowBenchmarkSnapshot extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  snapshot_version?: string;
  benchmark_version?: string;
  mode?: string;
  snapshot?: {
    snapshot_id?: string;
    created_at?: string;
    content_hash?: string;
    hash_algorithm?: string;
    storage?: string;
    mutation?: string;
    replay_request?: {
      endpoint?: string;
      method?: string;
      body?: Record<string, unknown>;
    };
    summary?: DispatchShadowBenchmark["summary"];
    component_count?: number;
    gate_count?: number;
  };
  scorecard?: DispatchShadowBenchmark;
  truth_contract?: Record<string, unknown>;
}

export interface OperationsScorecard extends TruthMetadata {
  success?: boolean;
  model_family?: string;
  scorecard_version?: string;
  summary?: {
    readiness_score?: number;
    status?: string;
    records_scanned?: number;
    total_freight?: number;
    on_time_rate?: number | null;
    exception_rate?: number | null;
    top_lane_freight_share?: number | null;
  };
  components?: Array<{
    id?: string;
    label?: string;
    score?: number;
    status?: string;
    details?: Record<string, unknown>;
  }>;
  gates?: Array<{
    id?: string;
    passed?: boolean;
    detail?: string;
  }>;
  recommendations?: string[];
  evidence?: Record<string, unknown>;
  truth_contract?: Record<string, unknown>;
}

export interface GurobiHealth extends TruthMetadata {
  success?: boolean;
  available?: boolean;
  status?: string;
  summary?: Record<string, unknown>;
  capability?: Record<string, unknown>;
  fallback_reason?: string | null;
}

export interface NetworkDesignSummary {
  selected_facilities?: number;
  assigned_customers?: number;
  unassigned_customers?: number;
  assigned_demand?: number;
  total_demand?: number;
  demand_coverage_rate?: number;
  fixed_cost?: number;
  transport_cost?: number;
  total_cost?: number;
  objective_value?: number;
  optimality_gap?: number | null;
  model_status?: string | number;
}

export interface NetworkFacility {
  id?: string | number;
  name?: string;
  facility_id?: string | number;
  facility_name?: string;
  capacity?: number;
  fixed_cost?: number;
  used_capacity?: number;
  utilization?: number;
  lat?: number | null;
  lon?: number | null;
  data_source?: string;
}

export interface NetworkAssignment {
  customer_id?: string | number;
  customer_name?: string;
  facility_id?: string | number;
  facility_name?: string;
  demand?: number;
  distance_km?: number;
  transport_cost?: number;
}

export interface NetworkDesignResult extends TruthMetadata {
  success?: boolean;
  error?: string;
  solver?: string | null;
  solver_quality?: string;
  summary?: NetworkDesignSummary;
  selected_facilities?: NetworkFacility[];
  assignments?: NetworkAssignment[];
  unassigned_customers?: Array<Record<string, unknown>>;
  diagnostics?: {
    unassigned_reason_distribution?: Record<string, number>;
    max_network_customers?: number;
    max_network_candidates?: number;
  };
  constraints?: string[];
  solve_time_seconds?: number;
  input_summary?: {
    customers?: number;
    candidates?: number;
    total_demand?: number;
    total_capacity?: number;
    transport_cost_per_km?: number;
    max_facilities?: number | null;
    source_mode?: string;
    customer_limit?: number;
    candidate_limit?: number;
  };
  gurobi_status?: {
    available?: boolean;
    provider_status?: ProviderStatus;
    fallback_reason?: string | null;
    checks?: Record<string, unknown>;
  };
}

export interface ProviderKeyStatus {
  provider?: string;
  effective_key_configured?: boolean;
  configured_aliases?: string[];
  missing_aliases?: string[];
  [key: string]: unknown;
}

export interface MapProviderComponent extends TruthMetadata {
  success?: boolean;
  provider?: string;
  provider_status?: ProviderStatus;
  degraded?: boolean;
  fallback_reason?: string | null;
  distance_km?: number | null;
  error?: string | null;
}

export interface AmapProviderHealth extends TruthMetadata {
  success?: boolean;
  provider?: string;
  keys?: ProviderKeyStatus;
  probed?: boolean;
  components?: Record<string, MapProviderComponent>;
  error?: string;
}

export interface TiandituKeyHealth extends TruthMetadata {
  success?: boolean;
  provider?: string;
  browser_key_configured?: boolean;
  server_key_configured?: boolean;
  keys?: ProviderKeyStatus;
  degraded?: boolean;
  error?: string;
}

export interface AmapDistanceCacheStats {
  total_entries?: number;
  amap_exact?: number;
  haversine_corrected?: number;
  expired?: number;
  db_path?: string;
}

export interface AmapDistanceCacheStatsResponse {
  success?: boolean;
  data?: AmapDistanceCacheStats;
  error?: string;
}

export interface AmapDistanceValidationPoint {
  node_id?: number | string | null;
  node_name?: string | null;
  longitude?: number | null;
  latitude?: number | null;
}

export interface AmapDistanceValidation extends TruthMetadata {
  origin?: AmapDistanceValidationPoint;
  destination?: AmapDistanceValidationPoint;
  strategy?: number | string;
  use_amap?: boolean;
  distance?: {
    distance_m?: number | null;
    distance_km?: number | null;
    duration_s?: number | null;
    duration_minutes?: number | null;
    source?: string | null;
    is_exact?: boolean;
    correction_factor?: number | null;
  };
  cache?: {
    hit_before_call?: boolean;
    exists_after_call?: boolean;
    cached_source?: string | null;
  };
  integration_status?: {
    amap_integrated?: boolean;
    real_distance_enabled?: boolean;
    fallback_enabled?: boolean;
  };
  provider?: string;
  provider_status?: ProviderStatus;
  degraded?: boolean;
  authenticity?: {
    level?: string;
    mode?: string;
    distance_source?: string;
    duration_source?: string;
    message?: string;
    [key: string]: unknown;
  };
}

export interface AmapDistanceValidationResponse {
  success?: boolean;
  data?: AmapDistanceValidation;
  error?: string;
}

export interface RouteNode {
  id?: number | string;
  name?: string;
  node_name?: string;
  type?: string;
  city?: string;
  province?: string;
  district?: string;
  address?: string;
  longitude?: number | null;
  latitude?: number | null;
  status?: string;
  [key: string]: unknown;
}

export interface NodeSearchResult {
  nodes?: RouteNode[];
  total?: number;
  page?: number;
  per_page?: number;
  pages?: number;
  error?: string;
}

export interface OrderSearchItem {
  id?: number | string;
  order_number?: string;
  external_order_id?: string;
  external_shipment_id?: string;
  data_source?: string;
  origin_name?: string;
  origin_address?: string;
  destination_name?: string;
  destination_address?: string;
  cargo_name?: string;
  goods_name?: string;
  cargo_type?: string;
  weight?: number | null;
  volume?: number | null;
  freight?: number | null;
  status?: string;
  created_at?: string | null;
  [key: string]: unknown;
}

export interface OrderSearchResult {
  orders?: OrderSearchItem[];
  total?: number;
  pages?: number;
  current_page?: number;
  data_source?: string;
  error?: string;
}

export type RouteSuggestionKind = "node" | "order";

export interface RouteSuggestionResponse extends TruthMetadata {
  success?: boolean;
  kind?: RouteSuggestionKind;
  query?: string;
  nodes?: RouteNode[];
  orders?: OrderSearchItem[];
  total?: number;
  data_source?: string;
  error?: string;
}

export interface RouteCandidate extends TruthMetadata {
  success?: boolean;
  source?: string;
  provider?: string;
  algorithm?: string;
  distance?: number | null;
  distance_km?: number | null;
  duration?: number | null;
  duration_minutes?: number | null;
  cost?: number | null;
  path?: Array<number | string> | Array<Record<string, unknown>>;
  polyline?: string | Array<string> | null;
  steps?: Array<Record<string, unknown>>;
  error?: string | null;
  degraded?: boolean;
  computation_time?: number | null;
  authenticity?: {
    level?: string;
    mode?: string;
    distance_source?: string;
    duration_source?: string;
    message?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface LocalRouteSegment {
  sequence?: number;
  from_node_id?: number | string;
  to_node_id?: number | string;
  route_id?: number | string | null;
  route_name?: string | null;
  distance_km?: number | null;
  duration_hours?: number | null;
  distance_source?: string | null;
  duration_source?: string | null;
  provider?: string | null;
  provider_status?: ProviderStatus | null;
  fallback_reason?: string | null;
}

export interface LocalRouteTruth {
  segment_count?: number;
  missing_segment_count?: number;
  route_ids?: Array<number | string>;
  distance_source_counts?: Record<string, number>;
  duration_source_counts?: Record<string, number>;
  provider_status_counts?: Record<string, number>;
  authenticity_level?: string | null;
}

export interface LocalRouteStrategy extends RouteCandidate {
  strategy_id?: string;
  optimize_by?: string;
  visited_nodes?: number | null;
  route_segments?: LocalRouteSegment[];
  route_truth?: LocalRouteTruth;
  comparison_to_provider?: {
    comparable?: boolean;
    provider?: string;
    provider_distance_km?: number | null;
    provider_duration_minutes?: number | null;
    distance_delta_km?: number | null;
    distance_delta_ratio?: number | null;
    duration_delta_minutes?: number | null;
    duration_delta_ratio?: number | null;
    fallback_reason?: string | null;
  };
  comparison_to_providers?: Record<
    string,
    {
      comparable?: boolean;
      provider?: string;
      provider_distance_km?: number | null;
      provider_duration_minutes?: number | null;
      distance_delta_km?: number | null;
      distance_delta_ratio?: number | null;
      duration_delta_minutes?: number | null;
      duration_delta_ratio?: number | null;
      fallback_reason?: string | null;
    }
  >;
}

export interface LocalRouteBenchmark extends TruthMetadata {
  success?: boolean;
  error?: string;
  origin?: RouteNode | null;
  destination?: RouteNode | null;
  provider_route?: RouteCandidate | null;
  provider_routes?: RouteCandidate[];
  provider_errors?: Record<string, string>;
  local_strategies?: LocalRouteStrategy[];
  summary?: {
    local_strategy_count?: number;
    successful_local_strategies?: number;
    failed_local_strategies?: number;
    best_local_strategy?: string | null;
    best_distance_strategy?: string | null;
    best_duration_strategy?: string | null;
    best_cost_strategy?: string | null;
    closest_to_provider_strategy?: string | null;
    provider_available?: boolean;
    primary_provider?: string | null;
    provider_count?: number;
    provider_available_count?: number;
    provider_available_sources?: string[];
    provider_distance_km?: number | null;
    provider_duration_minutes?: number | null;
    local_distance_source_counts?: Record<string, number>;
    local_provider_status_counts?: Record<string, number>;
  };
  diagnostics?: Record<string, unknown>;
}

export interface RouteSequenceLeg extends TruthMetadata {
  sequence?: number;
  from_node_id?: number | string;
  to_node_id?: number | string;
  distance_km?: number | null;
  duration_minutes?: number | null;
  path_node_ids?: Array<number | string>;
  route_truth?: LocalRouteTruth;
}

export interface RouteSequenceTruth extends LocalRouteTruth {
  leg_count?: number;
}

export interface RouteSequenceResult extends TruthMetadata {
  success?: boolean;
  solver?: string;
  solver_family?: string;
  solver_quality?: string;
  objective_value?: number | null;
  total_distance_km?: number | null;
  total_duration_minutes?: number | null;
  solve_time_seconds?: number | null;
  feasible?: boolean;
  hard_constraint_violations?: string[];
  node_sequence?: Array<number | string>;
  node_labels?: string[];
  route_legs?: RouteSequenceLeg[];
  route_truth?: RouteSequenceTruth;
  summary?: Record<string, unknown>;
}

export interface RouteSequenceBenchmark extends TruthMetadata {
  success?: boolean;
  error?: string;
  benchmark_type?: string;
  solver?: string;
  origin?: RouteNode | null;
  waypoints?: RouteNode[];
  distance_matrix?: number[][];
  duration_matrix_minutes?: number[][];
  matrix_truth?: {
    distance_source?: string;
    pair_count?: number;
    route_graph_pair_count?: number;
    haversine_fallback_pair_count?: number;
    failed_pair_count?: number;
    distance_source_counts?: Record<string, number>;
    duration_source_counts?: Record<string, number>;
    provider_status_counts?: Record<string, number>;
    provider_status?: ProviderStatus;
    fallback_reason?: string | null;
    authenticity_level?: string | null;
  };
  results?: RouteSequenceResult[];
  rankings?: Array<{
    rank?: number;
    solver?: string;
    total_distance_km?: number | null;
    total_duration_minutes?: number | null;
    solve_time_seconds?: number | null;
    solver_quality?: string;
  }>;
  summary?: {
    requested_solvers?: string[];
    succeeded_solvers?: string[];
    feasible_solvers?: string[];
    best_solver?: string | null;
    solve_time_seconds?: number;
    node_count?: number;
    waypoint_count?: number;
    return_to_depot?: boolean;
    allow_haversine_fallback?: boolean;
  };
  diagnostics?: Record<string, unknown>;
}

export interface AmapRouteComparison extends TruthMetadata {
  success?: boolean;
  error?: string;
  origin?: RouteNode;
  destination?: RouteNode;
  amap?: RouteCandidate | null;
  local?: RouteCandidate | null;
}

export interface TiandituAmapComparison extends TruthMetadata {
  success?: boolean;
  error?: string;
  tianditu?: RouteCandidate | null;
  amap?: RouteCandidate | null;
  comparison?: {
    distance_diff?: number | null;
    duration_diff?: number | null;
    better_distance?: string | null;
    better_duration?: string | null;
  };
}

export interface OrderRouteRecommendation extends TruthMetadata {
  success?: boolean;
  error?: string;
  data?: {
    order_id?: number | string;
    order_number?: string;
    data_source?: string;
    origin?: RouteNode;
    destination?: RouteNode;
    local_route?: RouteCandidate | null;
    amap_route?: RouteCandidate | null;
    recommended_route?: RouteCandidate | null;
    recommendation_reason?: string;
    provider_status?: ProviderStatus;
    fallback_reason?: string | null;
  };
}

export interface RouteComparePageData {
  generatedAt: string;
  apiBaseUrl: string;
  amapHealth: RemoteResult<AmapProviderHealth>;
  amapDistanceCacheStats: RemoteResult<AmapDistanceCacheStatsResponse>;
  amapDistanceValidation: RemoteResult<AmapDistanceValidationResponse>;
  tiandituKeys: RemoteResult<TiandituKeyHealth>;
  amapLocalCompare: RemoteResult<AmapRouteComparison>;
  localBenchmark: RemoteResult<LocalRouteBenchmark>;
  routeSequenceBenchmark: RemoteResult<RouteSequenceBenchmark>;
  tiandituAmapCompare: RemoteResult<TiandituAmapComparison>;
  routeRecommendation: RemoteResult<OrderRouteRecommendation>;
  nodeSuggestions: RemoteResult<NodeSearchResult>;
  orderSuggestions: RemoteResult<OrderSearchResult>;
}

export interface MapViewPageData {
  generatedAt: string;
  apiBaseUrl: string;
  amapHealth: RemoteResult<AmapProviderHealth>;
  tiandituKeys: RemoteResult<TiandituKeyHealth>;
  amapDistanceCacheStats: RemoteResult<AmapDistanceCacheStatsResponse>;
  amapDistanceValidation: RemoteResult<AmapDistanceValidationResponse>;
  amapLocalCompare: RemoteResult<AmapRouteComparison>;
  localBenchmark: RemoteResult<LocalRouteBenchmark>;
  routeSequenceBenchmark: RemoteResult<RouteSequenceBenchmark>;
  tiandituAmapCompare: RemoteResult<TiandituAmapComparison>;
  routeRecommendation: RemoteResult<OrderRouteRecommendation>;
  nodeInventory: RemoteResult<NodeSearchResult>;
  orderSample: RemoteResult<OrderSearchResult>;
}

export interface SolverBenchmark extends TruthMetadata {
  success?: boolean;
  summary?: {
    solver_count?: number;
    feasible_solver_count?: number;
    best_solver?: string | null;
  };
  rankings?: Array<{
    solver?: string;
    objective?: number;
    total_distance_km?: number;
    total_load?: number;
    success?: boolean;
    provider_status?: ProviderStatus;
  }>;
}

export interface RemoteResult<T> {
  ok: boolean;
  endpoint: string;
  data?: T;
  error?: string;
}

export interface DecisionConsoleData {
  generatedAt: string;
  apiBaseUrl: string;
  predictionHealth: RemoteResult<PredictionHealth>;
  predictionBaseline: RemoteResult<PredictionBaseline>;
  predictionModelStatus: RemoteResult<PredictionModelStatus>;
  predictionScorecard: RemoteResult<PredictionScorecard>;
  anomalyHealth: RemoteResult<AiAnomalyHealth>;
  anomalyDetect: RemoteResult<AiAnomalyDetect>;
  anomalyScorecard: RemoteResult<AiAnomalyScorecard>;
  operationsSummary: RemoteResult<OperationsSummary>;
  operationsScorecard: RemoteResult<OperationsScorecard>;
  dispatchHealth: RemoteResult<DispatchHealth>;
  dispatchShadowBenchmark: RemoteResult<DispatchShadowBenchmark>;
  gurobiHealth: RemoteResult<GurobiHealth>;
  solverBenchmark: RemoteResult<SolverBenchmark>;
}

export interface PredictionPageData {
  generatedAt: string;
  apiBaseUrl: string;
  predictionHealth: RemoteResult<PredictionHealth>;
  predictionBaseline: RemoteResult<PredictionBaseline>;
  predictionForecast: RemoteResult<PredictionForecast>;
  predictionTimeSeriesBenchmark: RemoteResult<PredictionTimeSeriesBenchmark>;
  predictionCapacityGapForecast: RemoteResult<PredictionCapacityGapForecast>;
  predictionCostVolatilityForecast: RemoteResult<PredictionCostVolatilityForecast>;
  predictionScorecard: RemoteResult<PredictionScorecard>;
  predictionFeatureDataset: RemoteResult<PredictionFeatureDataset>;
  predictionModelStatus: RemoteResult<PredictionModelStatus>;
}

export interface AnomalyPageData {
  generatedAt: string;
  apiBaseUrl: string;
  anomalyHealth: RemoteResult<AiAnomalyHealth>;
  anomalyDetect: RemoteResult<AiAnomalyDetect>;
  anomalyScorecard: RemoteResult<AiAnomalyScorecard>;
}

export interface DispatchPageData {
  generatedAt: string;
  apiBaseUrl: string;
  dispatchHealth: RemoteResult<DispatchHealth>;
  dispatchAlgorithms: RemoteResult<DispatchAlgorithms>;
  dispatchWave: RemoteResult<DispatchWave>;
  dispatchPreview: RemoteResult<DispatchPreview>;
  dispatchScenarios: RemoteResult<DispatchScenarioList>;
  dispatchSolverComparison: RemoteResult<DispatchSolverComparison>;
  dispatchLearningDataset: RemoteResult<DispatchLearningDataset>;
  dispatchPolicyScorer: RemoteResult<DispatchPolicyScorer>;
  dispatchRewardModel: RemoteResult<DispatchRewardModel>;
  dispatchShadowBenchmark: RemoteResult<DispatchShadowBenchmark>;
  dispatchShadowBenchmarkSnapshot: RemoteResult<DispatchShadowBenchmarkSnapshot>;
}

export interface DispatchScenarioPageData {
  generatedAt: string;
  apiBaseUrl: string;
  scenarioDetail: RemoteResult<DispatchScenarioDetail>;
  dispatchLearningDataset: RemoteResult<DispatchLearningDataset>;
  dispatchPolicyScorer: RemoteResult<DispatchPolicyScorer>;
  dispatchRewardModel: RemoteResult<DispatchRewardModel>;
  dispatchRedispatchSimulator: RemoteResult<DispatchRedispatchSimulator>;
  dispatchRedispatchProfiles: RemoteResult<DispatchRedispatchProfiles>;
  dispatchRedispatchScenarioGenerator: RemoteResult<DispatchRedispatchScenarioGenerator>;
  dispatchRlShadowRunner: RemoteResult<DispatchRlShadowRunner>;
  dispatchFittedQShadowModel: RemoteResult<DispatchFittedQShadowModel>;
  dispatchShadowBenchmark: RemoteResult<DispatchShadowBenchmark>;
  dispatchShadowBenchmarkSnapshot: RemoteResult<DispatchShadowBenchmarkSnapshot>;
}

export interface NetworkDesignPageData {
  generatedAt: string;
  apiBaseUrl: string;
  gurobiHealth: RemoteResult<GurobiHealth>;
  networkDemo: RemoteResult<NetworkDesignResult>;
  networkDatabase: RemoteResult<NetworkDesignResult>;
}
