import { cookies, headers } from "next/headers";
import { ACCESS_TOKEN_COOKIE } from "./auth";
import { getApiBaseUrl } from "./api-base";
import { refreshAccessTokenFromCookie } from "./token-refresh";
import type {
  AiAnomalyDetect,
  AiAnomalyHealth,
  AiAnomalyScorecard,
  AmapDistanceCacheStatsResponse,
  AmapDistanceValidationResponse,
  AmapProviderHealth,
  AmapRouteComparison,
  AnomalyPageData,
  DispatchAlgorithms,
  DecisionConsoleData,
  DispatchFittedQShadowModel,
  DispatchHealth,
  DispatchLearningDataset,
  DispatchPageData,
  DispatchPolicyScorer,
  DispatchPreview,
  DispatchRedispatchProfiles,
  DispatchRedispatchScenarioGenerator,
  DispatchRedispatchSimulator,
  DispatchRewardModel,
  DispatchRlShadowRunner,
  DispatchScenarioDetail,
  DispatchScenarioList,
  DispatchScenarioPageData,
  DispatchShadowBenchmark,
  DispatchShadowBenchmarkSnapshot,
  DispatchSolverComparison,
  DispatchWave,
  GurobiHealth,
  LocalRouteBenchmark,
  MapViewPageData,
  NetworkDesignPageData,
  NetworkDesignResult,
  NodeSearchResult,
  PredictionBaseline,
  PredictionCapacityGapForecast,
  PredictionCostVolatilityForecast,
  PredictionFeatureDataset,
  PredictionForecast,
  PredictionHealth,
  PredictionModelStatus,
  PredictionPageData,
  PredictionScorecard,
  PredictionTimeSeriesBenchmark,
  RemoteResult,
  RouteComparePageData,
  RouteSequenceBenchmark,
  OrderRouteRecommendation,
  OrderSearchResult,
  OperationsScorecard,
  OperationsSummary,
  SolverBenchmark,
  TiandituAmapComparison,
  TiandituKeyHealth,
} from "./types";

const SERVER_AUTH_ENV_KEYS = ["NEXT_API_BEARER_TOKEN", "NEXT_API_AUTH_TOKEN"];
const AUTH_COOKIE_KEYS = [ACCESS_TOKEN_COOKIE, "jwt", "token"];

export { getApiBaseUrl } from "./api-base";

type AuthSource = "explicit" | "env" | "incoming" | "cookie" | "none";

interface AuthResolution {
  headers: Record<string, string>;
  source: AuthSource;
  canRefreshFromCookie: boolean;
}

interface ApiFetchAttempt<T> {
  response: Response;
  payload: T | null;
}

export interface RouteCompareInput {
  originId?: number | null;
  destinationId?: number | null;
  waypointIds?: number[] | null;
  orderId?: number | null;
  preferSource?: string | null;
  strategy?: string | null;
  nodeQuery?: string | null;
  orderQuery?: string | null;
}

export interface RedispatchSimulatorInput {
  delayMinutes?: number | null;
  delayVehicleIds?: string | null;
  unavailableVehicleIds?: string | null;
  costMultiplier?: number | null;
  providerDegradation?: boolean | null;
  reliabilityDrop?: number | null;
  priorityOrderRefs?: string | null;
  topK?: number | null;
}

function normalizeHeaders(headersInit?: HeadersInit): Record<string, string> {
  if (!headersInit) return {};
  if (headersInit instanceof Headers) {
    return Object.fromEntries(headersInit.entries());
  }
  if (Array.isArray(headersInit)) {
    return Object.fromEntries(headersInit);
  }
  return { ...headersInit };
}

function hasAuthorizationHeader(headersObject: Record<string, string>): boolean {
  return Object.keys(headersObject).some((key) => key.toLowerCase() === "authorization");
}

function asBearerHeader(tokenOrHeader?: string | null): string | null {
  const value = tokenOrHeader?.trim();
  if (!value) return null;
  return value.toLowerCase().startsWith("bearer ") ? value : `Bearer ${value}`;
}

function getEnvAuthHeader(): string | null {
  for (const key of SERVER_AUTH_ENV_KEYS) {
    const value = asBearerHeader(process.env[key]);
    if (value) return value;
  }
  return null;
}

async function getRequestAuthHeader(): Promise<{ header: string; source: "incoming" | "cookie" } | null> {
  try {
    const incomingHeaders = await headers();
    const authorization = incomingHeaders.get("authorization");
    if (authorization?.trim().toLowerCase().startsWith("bearer ")) {
      return { header: authorization, source: "incoming" };
    }
  } catch {}

  try {
    const cookieStore = await cookies();
    for (const key of AUTH_COOKIE_KEYS) {
      const value = asBearerHeader(cookieStore.get(key)?.value);
      if (value) return { header: value, source: "cookie" };
    }
  } catch {
    return null;
  }

  return null;
}

async function resolveAuthHeaders(existingHeaders: Record<string, string>): Promise<AuthResolution> {
  if (hasAuthorizationHeader(existingHeaders)) {
    return {
      headers: {},
      source: "explicit",
      canRefreshFromCookie: false,
    };
  }

  const envAuth = getEnvAuthHeader();
  if (envAuth) {
    return {
      headers: { Authorization: envAuth },
      source: "env",
      canRefreshFromCookie: false,
    };
  }

  const requestAuth = await getRequestAuthHeader();
  if (requestAuth) {
    return {
      headers: { Authorization: requestAuth.header },
      source: requestAuth.source,
      canRefreshFromCookie: true,
    };
  }

  return {
    headers: {},
    source: "none",
    canRefreshFromCookie: true,
  };
}

function buildFetchHeaders(
  init: RequestInit,
  initHeaders: Record<string, string>,
  authHeaders: Record<string, string>,
): Record<string, string> {
  return {
    Accept: "application/json",
    ...(init.body ? { "Content-Type": "application/json" } : {}),
    ...authHeaders,
    ...initHeaders,
  };
}

async function fetchApiAttempt<T>(
  url: string,
  init: RequestInit,
  initHeaders: Record<string, string>,
  authHeaders: Record<string, string>,
): Promise<ApiFetchAttempt<T>> {
  const response = await fetch(url, {
    ...init,
    cache: "no-store",
    headers: buildFetchHeaders(init, initHeaders, authHeaders),
  });
  const payload = (await response.json().catch(() => null)) as T | null;
  return { response, payload };
}

export async function safeApiFetch<T>(
  endpoint: string,
  init: RequestInit = {},
): Promise<RemoteResult<T>> {
  const apiBaseUrl = getApiBaseUrl();
  const url = `${apiBaseUrl}${endpoint}`;
  const initHeaders = normalizeHeaders(init.headers);
  const authResolution = await resolveAuthHeaders(initHeaders);
  try {
    const { response, payload } = await fetchApiAttempt<T>(
      url,
      init,
      initHeaders,
      authResolution.headers,
    );

    if (response.status === 401 && authResolution.canRefreshFromCookie) {
      const refresh = await refreshAccessTokenFromCookie(apiBaseUrl);
      const refreshedAuthHeader = asBearerHeader(refresh.accessToken);
      if (refreshedAuthHeader) {
        const retry = await fetchApiAttempt<T>(url, init, initHeaders, {
          Authorization: refreshedAuthHeader,
        });
        if (!retry.response.ok) {
          return {
            ok: false,
            endpoint,
            data: retry.payload ?? undefined,
            error: `HTTP_${retry.response.status}`,
          };
        }
        return {
          ok: true,
          endpoint,
          data: retry.payload ?? undefined,
        };
      }
    }

    if (!response.ok) {
      return {
        ok: false,
        endpoint,
        data: payload ?? undefined,
        error: `HTTP_${response.status}`,
      };
    }
    return {
      ok: true,
      endpoint,
      data: payload ?? undefined,
    };
  } catch (error) {
    return {
      ok: false,
      endpoint,
      error: error instanceof Error ? error.message : "REQUEST_FAILED",
    };
  }
}

export async function getDecisionConsoleData(): Promise<DecisionConsoleData> {
  const [
    predictionHealth,
    predictionBaseline,
    predictionModelStatus,
    predictionScorecard,
    anomalyHealth,
    anomalyDetect,
    anomalyScorecard,
    operationsSummary,
    operationsScorecard,
    dispatchHealth,
    dispatchShadowBenchmark,
    gurobiHealth,
    solverBenchmark,
  ] = await Promise.all([
    safeApiFetch<PredictionHealth>("/ai-prediction/health"),
    safeApiFetch<PredictionBaseline>("/ai-prediction/baseline/evaluate", {
      method: "POST",
      body: JSON.stringify({
        tasks: ["demand", "eta", "delay", "cost"],
        horizon_days: 7,
        limit: 50000,
      }),
    }),
    safeApiFetch<PredictionModelStatus>("/ai-prediction/model/status"),
    safeApiFetch<PredictionScorecard>("/ai-prediction/scorecard", {
      method: "POST",
      body: JSON.stringify({
        horizon_days: 14,
        test_days: 14,
        sequence_length: 14,
        limit: 50000,
      }),
    }),
    safeApiFetch<AiAnomalyHealth>("/ai-anomaly/health"),
    safeApiFetch<AiAnomalyDetect>("/ai-anomaly/detect", {
      method: "POST",
      body: JSON.stringify({
        tasks: ["status", "geo", "cost", "eta", "delay", "od_volume", "node_congestion", "ml"],
        limit: 50000,
        anomaly_limit: 8,
        use_ml: true,
      }),
    }),
    safeApiFetch<AiAnomalyScorecard>("/ai-anomaly/scorecard", {
      method: "POST",
      body: JSON.stringify({
        tasks: ["status", "geo", "cost", "eta", "delay", "od_volume", "node_congestion", "ml"],
        limit: 50000,
        anomaly_limit: 80,
        use_ml: true,
      }),
    }),
    safeApiFetch<OperationsSummary>("/analytics/operations-summary", {
      method: "POST",
      body: JSON.stringify({
        limit: 50000,
        trend_days: 30,
        lane_limit: 8,
      }),
    }),
    safeApiFetch<OperationsScorecard>("/analytics/operations-scorecard", {
      method: "POST",
      body: JSON.stringify({
        limit: 50000,
        trend_days: 30,
        lane_limit: 8,
      }),
    }),
    safeApiFetch<DispatchHealth>("/dispatch/health"),
    safeApiFetch<DispatchShadowBenchmark>(
      "/dispatch/shadow-benchmark?scenario_limit=50&row_limit=100&anomaly_limit=80&use_ml=false&top_k=10&test_ratio=0.3",
    ),
    safeApiFetch<GurobiHealth>("/optimization/gurobi/health"),
    safeApiFetch<SolverBenchmark>("/optimization/solver-benchmark-demo"),
  ]);

  return {
    generatedAt: new Date().toISOString(),
    apiBaseUrl: getApiBaseUrl(),
    predictionHealth,
    predictionBaseline,
    predictionModelStatus,
    predictionScorecard,
    anomalyHealth,
    anomalyDetect,
    anomalyScorecard,
    operationsSummary,
    operationsScorecard,
    dispatchHealth,
    dispatchShadowBenchmark,
    gurobiHealth,
    solverBenchmark,
  };
}

export async function getPredictionPageData(): Promise<PredictionPageData> {
  const [
    predictionHealth,
    predictionBaseline,
    predictionForecast,
    predictionTimeSeriesBenchmark,
    predictionCapacityGapForecast,
    predictionCostVolatilityForecast,
    predictionScorecard,
    predictionFeatureDataset,
    predictionModelStatus,
  ] = await Promise.all([
    safeApiFetch<PredictionHealth>("/ai-prediction/health"),
    safeApiFetch<PredictionBaseline>("/ai-prediction/baseline/evaluate", {
      method: "POST",
      body: JSON.stringify({
        tasks: ["demand", "eta", "delay", "cost"],
        horizon_days: 14,
        limit: 50000,
      }),
    }),
    safeApiFetch<PredictionForecast>("/ai-prediction/demand/forecast?days=14&limit=50000"),
    safeApiFetch<PredictionTimeSeriesBenchmark>("/ai-prediction/time-series/benchmark", {
      method: "POST",
      body: JSON.stringify({
        task: "demand",
        horizon_days: 14,
        test_days: 14,
        sequence_length: 14,
        limit: 50000,
      }),
    }),
    safeApiFetch<PredictionCapacityGapForecast>("/ai-prediction/capacity-gap/forecast", {
      method: "POST",
      body: JSON.stringify({
        horizon_days: 14,
        test_days: 14,
        sequence_length: 14,
        limit: 50000,
      }),
    }),
    safeApiFetch<PredictionCostVolatilityForecast>("/ai-prediction/cost-volatility/forecast", {
      method: "POST",
      body: JSON.stringify({
        horizon_days: 14,
        test_days: 14,
        sequence_length: 14,
        volatility_window: 7,
        limit: 50000,
      }),
    }),
    safeApiFetch<PredictionScorecard>("/ai-prediction/scorecard", {
      method: "POST",
      body: JSON.stringify({
        horizon_days: 14,
        test_days: 14,
        sequence_length: 14,
        limit: 50000,
      }),
    }),
    safeApiFetch<PredictionFeatureDataset>("/ai-prediction/features/dataset", {
      method: "POST",
      body: JSON.stringify({
        task: "eta",
        limit: 50000,
        row_limit: 8,
      }),
    }),
    safeApiFetch<PredictionModelStatus>("/ai-prediction/model/status"),
  ]);

  return {
    generatedAt: new Date().toISOString(),
    apiBaseUrl: getApiBaseUrl(),
    predictionHealth,
    predictionBaseline,
    predictionForecast,
    predictionTimeSeriesBenchmark,
    predictionCapacityGapForecast,
    predictionCostVolatilityForecast,
    predictionScorecard,
    predictionFeatureDataset,
    predictionModelStatus,
  };
}

export async function getAnomalyPageData(): Promise<AnomalyPageData> {
  const [anomalyHealth, anomalyDetect, anomalyScorecard] = await Promise.all([
    safeApiFetch<AiAnomalyHealth>("/ai-anomaly/health"),
    safeApiFetch<AiAnomalyDetect>("/ai-anomaly/detect", {
      method: "POST",
      body: JSON.stringify({
        tasks: ["status", "geo", "cost", "eta", "delay", "od_volume", "node_congestion", "ml"],
        limit: 50000,
        anomaly_limit: 40,
        use_ml: true,
      }),
    }),
    safeApiFetch<AiAnomalyScorecard>("/ai-anomaly/scorecard", {
      method: "POST",
      body: JSON.stringify({
        tasks: ["status", "geo", "cost", "eta", "delay", "od_volume", "node_congestion", "ml"],
        limit: 50000,
        anomaly_limit: 80,
        use_ml: true,
      }),
    }),
  ]);

  return {
    generatedAt: new Date().toISOString(),
    apiBaseUrl: getApiBaseUrl(),
    anomalyHealth,
    anomalyDetect,
    anomalyScorecard,
  };
}

export async function getDispatchPageData(): Promise<DispatchPageData> {
  const previewPayload = {
    data_source: "auto",
    algorithm: "balanced",
    solver: "auto",
    limit: 100,
    max_orders_per_vehicle: 20,
    use_precise_distance: false,
    persist: false,
    weights: {
      cost: 0.4,
      time: 0.3,
      satisfaction: 0.3,
    },
  };

  const [
    dispatchHealth,
    dispatchAlgorithms,
    dispatchWave,
    dispatchPreview,
    dispatchScenarios,
    dispatchSolverComparison,
    dispatchLearningDataset,
    dispatchPolicyScorer,
    dispatchRewardModel,
    dispatchShadowBenchmark,
    dispatchShadowBenchmarkSnapshot,
  ] = await Promise.all([
    safeApiFetch<DispatchHealth>("/dispatch/health"),
    safeApiFetch<DispatchAlgorithms>("/dispatch/algorithms"),
    safeApiFetch<DispatchWave>("/dispatch/waves", {
      method: "POST",
      body: JSON.stringify(previewPayload),
    }),
    safeApiFetch<DispatchPreview>("/dispatch/preview", {
      method: "POST",
      body: JSON.stringify(previewPayload),
    }),
    safeApiFetch<DispatchScenarioList>("/dispatch/scenarios?limit=8"),
    safeApiFetch<DispatchSolverComparison>("/dispatch/compare-solvers", {
      method: "POST",
      body: JSON.stringify({
        ...previewPayload,
        solvers: ["greedy", "balanced", "capacity_first", "ortools", "alns", "genetic"],
      }),
    }),
    safeApiFetch<DispatchLearningDataset>("/dispatch/learning-dataset?scenario_limit=50&row_limit=100"),
    safeApiFetch<DispatchPolicyScorer>("/dispatch/policy-scorer?scenario_limit=50&row_limit=100&top_k=10"),
    safeApiFetch<DispatchRewardModel>("/dispatch/reward-model?scenario_limit=50&row_limit=100&test_ratio=0.3"),
    safeApiFetch<DispatchShadowBenchmark>(
      "/dispatch/shadow-benchmark?scenario_limit=50&row_limit=100&anomaly_limit=80&use_ml=false&top_k=10&test_ratio=0.3",
    ),
    safeApiFetch<DispatchShadowBenchmarkSnapshot>(
      "/dispatch/shadow-benchmark/snapshot?scenario_limit=50&row_limit=100&anomaly_limit=80&use_ml=false&top_k=10&test_ratio=0.3",
    ),
  ]);

  return {
    generatedAt: new Date().toISOString(),
    apiBaseUrl: getApiBaseUrl(),
    dispatchHealth,
    dispatchAlgorithms,
    dispatchWave,
    dispatchPreview,
    dispatchScenarios,
    dispatchSolverComparison,
    dispatchLearningDataset,
    dispatchPolicyScorer,
    dispatchRewardModel,
    dispatchShadowBenchmark,
    dispatchShadowBenchmarkSnapshot,
  };
}

export async function getDispatchScenarioPageData(
  scenarioId: number,
  simulatorInput: RedispatchSimulatorInput = {},
): Promise<DispatchScenarioPageData> {
  const scenarioQuery = `scenario_id=${encodeURIComponent(String(scenarioId))}&scenario_limit=1&row_limit=100`;
  const policyQuery = `${scenarioQuery}&top_k=10`;
  const rewardQuery = `${scenarioQuery}&test_ratio=0.3`;
  const simulatorParams = new URLSearchParams({
    scenario_id: String(scenarioId),
    scenario_limit: "1",
    row_limit: "100",
    top_k: String(simulatorInput.topK ?? 10),
    delay_minutes: String(simulatorInput.delayMinutes ?? 45),
    cost_multiplier: String(simulatorInput.costMultiplier ?? 1.12),
    provider_degradation: String(simulatorInput.providerDegradation ?? true),
    reliability_drop: String(simulatorInput.reliabilityDrop ?? 0.25),
  });
  if (simulatorInput.delayVehicleIds) {
    simulatorParams.set("delay_vehicle_ids", simulatorInput.delayVehicleIds);
  }
  if (simulatorInput.unavailableVehicleIds) {
    simulatorParams.set("unavailable_vehicle_ids", simulatorInput.unavailableVehicleIds);
  }
  if (simulatorInput.priorityOrderRefs) {
    simulatorParams.set("priority_order_refs", simulatorInput.priorityOrderRefs);
  }
  const [
    scenarioDetail,
    dispatchLearningDataset,
    dispatchPolicyScorer,
    dispatchRewardModel,
    dispatchRedispatchSimulator,
    dispatchRedispatchProfiles,
    dispatchRedispatchScenarioGenerator,
    dispatchRlShadowRunner,
    dispatchFittedQShadowModel,
    dispatchShadowBenchmark,
    dispatchShadowBenchmarkSnapshot,
  ] = await Promise.all([
    safeApiFetch<DispatchScenarioDetail>(`/dispatch/scenarios/${scenarioId}`),
    safeApiFetch<DispatchLearningDataset>(`/dispatch/learning-dataset?${scenarioQuery}`),
    safeApiFetch<DispatchPolicyScorer>(`/dispatch/policy-scorer?${policyQuery}`),
    safeApiFetch<DispatchRewardModel>(`/dispatch/reward-model?${rewardQuery}`),
    safeApiFetch<DispatchRedispatchSimulator>(`/dispatch/redispatch-simulator?${simulatorParams.toString()}`),
    safeApiFetch<DispatchRedispatchProfiles>(`/dispatch/redispatch-profiles?${scenarioQuery}&anomaly_limit=80&use_ml=false`),
    safeApiFetch<DispatchRedispatchScenarioGenerator>(
      `/dispatch/redispatch-scenario-generator?${scenarioQuery}&anomaly_limit=80&use_ml=false&top_k=10`,
    ),
    safeApiFetch<DispatchRlShadowRunner>(
      `/dispatch/rl-shadow-runner?${scenarioQuery}&anomaly_limit=80&use_ml=false&top_k=10`,
    ),
    safeApiFetch<DispatchFittedQShadowModel>(
      `/dispatch/fitted-q-shadow-model?${scenarioQuery}&anomaly_limit=80&use_ml=false&top_k=10&test_ratio=0.3`,
    ),
    safeApiFetch<DispatchShadowBenchmark>(
      `/dispatch/shadow-benchmark?${scenarioQuery}&anomaly_limit=80&use_ml=false&top_k=10&test_ratio=0.3`,
    ),
    safeApiFetch<DispatchShadowBenchmarkSnapshot>(
      `/dispatch/shadow-benchmark/snapshot?${scenarioQuery}&anomaly_limit=80&use_ml=false&top_k=10&test_ratio=0.3`,
    ),
  ]);

  return {
    generatedAt: new Date().toISOString(),
    apiBaseUrl: getApiBaseUrl(),
    scenarioDetail,
    dispatchLearningDataset,
    dispatchPolicyScorer,
    dispatchRewardModel,
    dispatchRedispatchSimulator,
    dispatchRedispatchProfiles,
    dispatchRedispatchScenarioGenerator,
    dispatchRlShadowRunner,
    dispatchFittedQShadowModel,
    dispatchShadowBenchmark,
    dispatchShadowBenchmarkSnapshot,
  };
}

export async function getNetworkDesignPageData(): Promise<NetworkDesignPageData> {
  const [gurobiHealth, networkDemo, networkDatabase] = await Promise.all([
    safeApiFetch<GurobiHealth>("/optimization/gurobi/health"),
    safeApiFetch<NetworkDesignResult>("/optimization/gurobi/network-design-demo"),
    safeApiFetch<NetworkDesignResult>("/optimization/gurobi/network-design", {
      method: "POST",
      body: JSON.stringify({
        solver: "auto",
        use_database: true,
        customer_limit: 8,
        candidate_limit: 5,
        max_facilities: 3,
        transport_cost_per_km: 2.4,
      }),
    }),
  ]);

  return {
    generatedAt: new Date().toISOString(),
    apiBaseUrl: getApiBaseUrl(),
    gurobiHealth,
    networkDemo,
    networkDatabase,
  };
}

function positiveInteger(value?: number | string | null): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return Math.trunc(parsed);
}

function pairFromRecommendation(result?: RemoteResult<OrderRouteRecommendation> | null) {
  return {
    origin_id: positiveInteger(result?.data?.data?.origin?.id),
    destination_id: positiveInteger(result?.data?.data?.destination?.id),
  };
}

function compactQuery(value?: string | null): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed.slice(0, 80) : null;
}

function queryString(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

function uniquePositiveIntegers(values?: Array<number | string | null | undefined> | null): number[] {
  const result: number[] = [];
  for (const value of values || []) {
    const parsed = positiveInteger(value);
    if (parsed && !result.includes(parsed)) {
      result.push(parsed);
    }
  }
  return result;
}

function routeSequenceNodeIds(depotId?: number | null, destinationId?: number | null, waypointIds?: number[] | null): number[] {
  const nodes = uniquePositiveIntegers([...(waypointIds || []), destinationId]);
  return nodes.filter((nodeId) => nodeId !== depotId).slice(0, 8);
}

export async function getMapViewPageData(
  input: RouteCompareInput = {},
): Promise<MapViewPageData> {
  const requestedPair = {
    origin_id: positiveInteger(input.originId),
    destination_id: positiveInteger(input.destinationId),
  };
  const orderId = positiveInteger(input.orderId);
  const preferSource = input.preferSource || "auto";
  const strategy = input.strategy || "0";
  const nodeQuery = compactQuery(input.nodeQuery);
  const orderQuery = compactQuery(input.orderQuery) || (orderId ? String(orderId) : "35692");

  const orderRecommendationSeed = orderId
    ? safeApiFetch<OrderRouteRecommendation>(
        `/orders/${orderId}/recommend-route?prefer_source=${encodeURIComponent(preferSource)}`,
      )
    : Promise.resolve(null);

  const [
    amapHealth,
    tiandituKeys,
    amapDistanceCacheStats,
    nodeInventory,
    orderSample,
    seedRecommendation,
  ] = await Promise.all([
    safeApiFetch<AmapProviderHealth>("/amap/provider-health?probe=1"),
    safeApiFetch<TiandituKeyHealth>("/tianditu/keys"),
    safeApiFetch<AmapDistanceCacheStatsResponse>("/amap/distance/cache/stats"),
    safeApiFetch<NodeSearchResult>(
      `/nodes${queryString({
        page: 1,
        per_page: 8,
        keyword: nodeQuery,
      })}`,
    ),
    safeApiFetch<OrderSearchResult>(
      `/orders${queryString({
        page: 1,
        per_page: 6,
        search: orderQuery,
      })}`,
    ),
    orderRecommendationSeed,
  ]);

  const recommendationPair = pairFromRecommendation(seedRecommendation);
  const samplePair = {
    origin_id: requestedPair.origin_id || recommendationPair.origin_id || 1,
    destination_id: requestedPair.destination_id || recommendationPair.destination_id || 2,
  };
  const sequenceNodeIds = routeSequenceNodeIds(samplePair.origin_id, samplePair.destination_id, input.waypointIds);

  const [
    amapDistanceValidation,
    amapLocalCompare,
    localBenchmark,
    routeSequenceBenchmark,
    tiandituAmapCompare,
    routeRecommendation,
  ] =
    await Promise.all([
      safeApiFetch<AmapDistanceValidationResponse>("/amap/distance/validate", {
        method: "POST",
        body: JSON.stringify({
          ...samplePair,
          strategy,
          use_amap: true,
        }),
      }),
      safeApiFetch<AmapRouteComparison>("/amap/route/compare", {
        method: "POST",
        body: JSON.stringify(samplePair),
      }),
      safeApiFetch<LocalRouteBenchmark>("/amap/route/local-benchmark", {
        method: "POST",
        body: JSON.stringify({
          ...samplePair,
          strategy,
          include_provider: true,
          provider_sources: ["amap", "tianditu"],
        }),
      }),
      safeApiFetch<RouteSequenceBenchmark>("/optimization/route-sequence-benchmark", {
        method: "POST",
        body: JSON.stringify({
          depot_id: samplePair.origin_id,
          node_ids: sequenceNodeIds,
          solvers: ["nearest_neighbor", "two_opt", "ortools", "gurobi"],
          return_to_depot: true,
          allow_haversine_fallback: true,
          time_limit: 3,
        }),
      }),
      safeApiFetch<TiandituAmapComparison>("/tianditu/compare/amap", {
        method: "POST",
        body: JSON.stringify({
          ...samplePair,
          strategy,
        }),
      }),
      seedRecommendation ||
        safeApiFetch<OrderRouteRecommendation>("/orders/recommend-route", {
          method: "POST",
          body: JSON.stringify({
            ...samplePair,
            prefer_source: preferSource,
          }),
        }),
    ]);

  return {
    generatedAt: new Date().toISOString(),
    apiBaseUrl: getApiBaseUrl(),
    amapHealth,
    tiandituKeys,
    amapDistanceCacheStats,
    amapDistanceValidation,
    amapLocalCompare,
    localBenchmark,
    routeSequenceBenchmark,
    tiandituAmapCompare,
    routeRecommendation,
    nodeInventory,
    orderSample,
  };
}

export async function getRouteComparePageData(
  input: RouteCompareInput = {},
): Promise<RouteComparePageData> {
  const requestedPair = {
    origin_id: positiveInteger(input.originId),
    destination_id: positiveInteger(input.destinationId),
  };
  const orderId = positiveInteger(input.orderId);
  const preferSource = input.preferSource || "auto";
  const strategy = input.strategy || "0";
  const nodeQuery = compactQuery(input.nodeQuery);
  const orderQuery = compactQuery(input.orderQuery) || (orderId ? String(orderId) : null);

  const [amapHealth, tiandituKeys, orderRecommendation, nodeSuggestions, orderSuggestions] = await Promise.all([
    safeApiFetch<AmapProviderHealth>("/amap/provider-health?probe=1"),
    safeApiFetch<TiandituKeyHealth>("/tianditu/keys"),
    orderId
      ? safeApiFetch<OrderRouteRecommendation>(
          `/orders/${orderId}/recommend-route?prefer_source=${encodeURIComponent(preferSource)}`,
        )
      : Promise.resolve(null),
    safeApiFetch<NodeSearchResult>(
      `/nodes${queryString({
        page: 1,
        per_page: 8,
        keyword: nodeQuery,
      })}`,
    ),
    safeApiFetch<OrderSearchResult>(
      `/orders${queryString({
        page: 1,
        per_page: 6,
        search: orderQuery,
      })}`,
    ),
  ]);

  const recommendationPair = pairFromRecommendation(orderRecommendation);
  const samplePair = {
    origin_id: requestedPair.origin_id || recommendationPair.origin_id || 1,
    destination_id: requestedPair.destination_id || recommendationPair.destination_id || 2,
  };
  const sequenceNodeIds = routeSequenceNodeIds(samplePair.origin_id, samplePair.destination_id, input.waypointIds);

  const [
    amapLocalCompare,
    localBenchmark,
    routeSequenceBenchmark,
    tiandituAmapCompare,
    routeRecommendation,
    amapDistanceCacheStats,
    amapDistanceValidation,
  ] = await Promise.all([
    safeApiFetch<AmapRouteComparison>("/amap/route/compare", {
      method: "POST",
      body: JSON.stringify(samplePair),
    }),
    safeApiFetch<LocalRouteBenchmark>("/amap/route/local-benchmark", {
      method: "POST",
      body: JSON.stringify({
        ...samplePair,
        strategy,
        include_provider: true,
        provider_sources: ["amap", "tianditu"],
      }),
    }),
    safeApiFetch<RouteSequenceBenchmark>("/optimization/route-sequence-benchmark", {
      method: "POST",
      body: JSON.stringify({
        depot_id: samplePair.origin_id,
        node_ids: sequenceNodeIds,
        solvers: ["nearest_neighbor", "two_opt", "ortools", "gurobi"],
        return_to_depot: true,
        allow_haversine_fallback: true,
        time_limit: 3,
      }),
    }),
    safeApiFetch<TiandituAmapComparison>("/tianditu/compare/amap", {
      method: "POST",
      body: JSON.stringify({
        ...samplePair,
        strategy,
      }),
    }),
    orderRecommendation ||
      safeApiFetch<OrderRouteRecommendation>("/orders/recommend-route", {
        method: "POST",
        body: JSON.stringify({
          ...samplePair,
          prefer_source: preferSource,
        }),
      }),
    safeApiFetch<AmapDistanceCacheStatsResponse>("/amap/distance/cache/stats"),
    safeApiFetch<AmapDistanceValidationResponse>("/amap/distance/validate", {
      method: "POST",
      body: JSON.stringify({
        ...samplePair,
        strategy,
        use_amap: true,
      }),
    }),
  ]);

  return {
    generatedAt: new Date().toISOString(),
    apiBaseUrl: getApiBaseUrl(),
    amapHealth,
    amapDistanceCacheStats,
    amapDistanceValidation,
    tiandituKeys,
    amapLocalCompare,
    localBenchmark,
    routeSequenceBenchmark,
    tiandituAmapCompare,
    routeRecommendation,
    nodeSuggestions,
    orderSuggestions,
  };
}
