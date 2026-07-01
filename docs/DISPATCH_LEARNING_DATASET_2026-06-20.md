# Dispatch Learning Dataset

Date: 2026-06-20

## Purpose

`/api/dispatch/learning-dataset` exposes persisted dispatch scenarios and assignments as a compact AI shadow-mode dataset. It is the first data foundation for later dynamic re-dispatch strategy learning.

This endpoint does not train or execute DQN/DQL. It only prepares state/action/proxy-reward rows for offline evaluation and shadow scoring.

## Endpoint

```text
GET /api/dispatch/learning-dataset?scenario_limit=50&row_limit=200
GET /api/dispatch/learning-dataset?scenario_id=123&row_limit=200
POST /api/dispatch/learning-dataset

GET /api/dispatch/policy-scorer?scenario_limit=50&row_limit=200&top_k=10
GET /api/dispatch/policy-scorer?scenario_id=123&row_limit=200&top_k=10
POST /api/dispatch/policy-scorer

GET /api/dispatch/reward-model?scenario_limit=50&row_limit=200&test_ratio=0.3
GET /api/dispatch/reward-model?scenario_id=123&row_limit=200&test_ratio=0.3
POST /api/dispatch/reward-model

GET /api/dispatch/redispatch-simulator?scenario_id=123&row_limit=200&top_k=10
POST /api/dispatch/redispatch-simulator

GET /api/dispatch/redispatch-profiles?scenario_id=123&anomaly_limit=80
POST /api/dispatch/redispatch-profiles

GET /api/dispatch/redispatch-scenario-generator?scenario_id=123&anomaly_limit=80
POST /api/dispatch/redispatch-scenario-generator

GET /api/dispatch/rl-shadow-runner?scenario_id=123&anomaly_limit=80
POST /api/dispatch/rl-shadow-runner

GET /api/dispatch/fitted-q-shadow-model?scenario_id=123&anomaly_limit=80
POST /api/dispatch/fitted-q-shadow-model

GET /api/dispatch/shadow-benchmark?scenario_id=123&anomaly_limit=80
POST /api/dispatch/shadow-benchmark

GET /api/dispatch/shadow-benchmark/snapshot?scenario_id=123&anomaly_limit=80
POST /api/dispatch/shadow-benchmark/snapshot
```

GET query / POST body:

- `scenario_id`: optional single dispatch scenario ID for replay/scenario-detail evaluation.
- `scenario_ids`: optional comma-separated or array-style list of dispatch scenario IDs.
- `scenario_limit`: number of recent scenarios to inspect.
- `row_limit`: maximum assignment rows returned.
- `status`: optional scenario status filter.
- `include_preview`: include preview scenarios when status is not specified.

Redispatch simulator disruption fields:

- `delay_minutes`: synthetic delay pressure added to matching assignment rows.
- `delay_vehicle_ids`: optional vehicle IDs that receive delay pressure; empty means all rows.
- `unavailable_vehicle_ids`: vehicle IDs that should be held for solver-backed reassignment.
- `cost_multiplier`: synthetic cost pressure multiplier.
- `provider_degradation`: whether to degrade route provider reliability in the simulation.
- `reliability_drop`: reliability penalty when provider degradation is enabled.

Authentication follows the existing dispatch API contract and requires JWT.

## Output Contract

Top-level truth:

- `data_source = dispatch_scenarios_assignments`
- `path_source = dispatch_assignment_sequence`
- `distance_source`: primary source aggregated from assignment `route_truth`
- `provider_status`: `ok` only when the dataset is ready
- `fallback_reason`: readiness reason when not ready
- `authenticity_level`: `B-` when persisted rows exist

Main payload:

- `summary`: scenario count, assignment count, row count, unique vehicles/orders, route truth coverage, source/status counts, average proxy reward.
- `filters`: resolved scenario/status/limit filters used to build the dataset.
- `readiness`: whether enough persisted rows and route truth exist for shadow training.
- `target_definition`: state/action/reward boundary and hard-constraint note.
- `feature_schema`: model-ready feature fields.
- `rows`: assignment-level state/action/reward rows.

## Scenario-Scoped Replay

`/dispatch/scenarios/[id]` in `frontend-next` calls the learning dataset, policy scorer, and reward model with `scenario_id=<id>`. This makes the page a replay-style shadow evaluation for the selected persisted scenario instead of a global recent-scenario summary.

When a `scenario_id` filter is active:

- dataset rows only come from the selected persisted scenario;
- `filters.scenario_ids` echoes the selected ID;
- policy scoring ranks only that scenario's assignment rows;
- the reward model is still offline and shadow-only, but its metrics describe the selected scenario's available rows.

Each row includes:

- `state_key`
- `action.assign_to_vehicle_id`
- `features`
- `target.reward_proxy`
- `truth.route_truth`

## Reward Boundary

`reward_proxy` is an offline proxy:

```text
utilization + provider reliability + applied bonus
- cost/duration/unassigned/risk penalties
```

It is not a verified business KPI and must not override dispatch hard constraints. Capacity, order uniqueness, vehicle availability, and route feasibility remain solver responsibilities.

## Offline Policy Scorer

`/api/dispatch/policy-scorer` consumes the same `rl_shadow_dataset_v1` rows and compares simple shadow policies:

- `historical_solver_order`: persisted assignment order baseline.
- `balanced_shadow`: reward, utilization, reliability, cost, and risk balance.
- `utilization_first`: prioritizes load/volume utilization.
- `reliability_first`: prioritizes route-truth reliability and fewer estimated legs.
- `risk_averse`: penalizes AI shadow risk.
- `cost_guarded`: prefers lower cost while retaining route-truth reliability.
- `reward_oracle_upper_bound`: offline upper bound using known proxy reward. This row is explicitly non-deployable.

Scoring is rank-sensitive:

- `top_k_reward_proxy`: average proxy reward among top-ranked actions.
- `discounted_reward_proxy`: rank-discounted proxy reward over all rows.
- `policy_score`: weighted summary of top-k and discounted reward.
- `score_delta_vs_baseline`: difference from `historical_solver_order`.

The best policy only considers deployable shadow heuristics. The oracle upper bound is never returned as the deployable recommendation.

## Offline Reward Model

`/api/dispatch/reward-model` trains and evaluates a lightweight `linear_reward_ranker_v1` over the same persisted dataset.

It returns:

- train/test row counts.
- feature names and standardized linear coefficients.
- feature importance by absolute coefficient weight.
- MAE, RMSE, R2, and pairwise rank accuracy.
- sample predictions with actual vs predicted `reward_proxy`.

This model is a contextual shadow baseline for later DQL/DQN work. It does not replace the dispatch solver, does not enforce constraints, does not apply scenarios, and does not write model artifacts or business state.

## Dynamic Re-dispatch Shadow Simulator

`/api/dispatch/redispatch-simulator` runs a read-only disruption simulation over the same `rl_shadow_dataset_v1` rows.

It returns:

- `disruption`: normalized synthetic disruption parameters.
- `summary`: impacted assignment count, held-for-reassignment count, original/simulated average reward proxy, and best shadow policy.
- `policies`: the same deployable/non-deployable policy comparison under the disrupted row scores.
- `impacts`: assignment-level score deltas, impact flags, and suggested shadow action.
- `recommendations`: operator-facing shadow recommendations.
- `truth_contract.mutation = none`.

This endpoint is a bridge toward DQL/DQN dynamic re-dispatch experiments. It does not mutate dispatch scenarios, assignments, orders, vehicles, or `shipment_facts`; final apply must remain behind solver hard constraints.

`frontend-next` `/dispatch/scenarios/[id]` renders the simulator as `Dynamic Re-dispatch Shadow`. The panel includes an SSR form for:

- `delay_minutes`
- `delay_vehicle_ids`
- `unavailable_vehicle_ids`
- `cost_multiplier`
- `provider_degradation`
- `reliability_drop`
- `top_k`

Submitting the form updates the URL and re-renders the read-only simulator server-side with the selected scenario ID.

`/api/dispatch/redispatch-profiles` generates ready-to-apply simulator profiles from real `/api/ai-anomaly` shipment-fact signals. Current profiles include:

- `anomaly_balanced_pressure`
- `delay_recovery`
- `cost_guard`

Each profile contains simulator `params`, anomaly `evidence`, confidence, and truth metadata. The Next scenario detail panel renders these profiles as `Apply` links that update the simulator URL parameters. This is still read-only shadow evaluation and does not apply dispatch changes.

## Historical Disruption Scenario Generator

`/api/dispatch/redispatch-scenario-generator` turns the anomaly-driven profiles into scored replay episodes. It calls the read-only simulator for each generated preset and returns:

- `generated_scenarios`: replayable disruption episodes with params, evidence, simulation summary, best shadow policy, impact preview, and recommendations.
- `summary.anomaly_by_type`: anomaly distribution from real `shipment_facts` signals.
- `summary.avg_impacted_assignments`: average simulated assignment impact across generated episodes.
- `truth_contract.mutation = none`.
- `truth_contract.dql_dqn_boundary`: the output is suitable for shadow training/evaluation presets only; hard constraints remain solver-owned.

Current generated episodes include the anomaly profiles plus a `vehicle_holdout_recovery` episode derived from low-reward persisted assignment streams. This helps future DQL/DQN work start from real historical pressure patterns instead of purely manual simulator parameters.

`frontend-next` `/dispatch/scenarios/[id]` renders these as `Historical Disruption Episodes`. Each episode can be applied to the simulator form through an SSR-safe link; no business state is mutated and no browser token is exposed.

## Offline RL Shadow Runner

`/api/dispatch/rl-shadow-runner` is the first reinforcement-learning-shaped evaluation layer. It does not deploy a DQN/DQL controller. It treats generated disruption episodes as state buckets and existing deployable shadow policies as actions, then estimates a small Q-style table from simulator policy scores.

It returns:

- `state_schema`: the state bucket dimensions, including delay, cost, provider, vehicle availability, and priority pressure.
- `action_space`: deployable shadow policy actions such as `historical_solver_order`, `balanced_shadow`, `reliability_first`, and `cost_guarded`.
- `q_table`: average Q-style score per state bucket and action.
- `episode_results`: selected action, baseline score, selected score, score delta, impacted assignments, and per-policy scores for each generated episode.
- `summary.deployable = false`.
- `truth_contract.mutation = none`.

This gives later DQL/DQN work a measurable offline benchmark surface while keeping hard dispatch constraints with the solver layer.

`frontend-next` `/dispatch/scenarios/[id]` renders this as `RL Shadow Runner` next to the episode generator and dynamic simulator. The panel shows Q-state counts, action counts, baseline vs selected score, selected action distribution, and episode-level deltas.

## Offline Fitted-Q Shadow Model

`/api/dispatch/fitted-q-shadow-model` trains/evaluates a lightweight fitted-Q style approximator over the same generated redispatch episodes. It expands each episode/action pair into a model sample:

- state features: delay minutes, cost multiplier, provider degradation, reliability drop, vehicle holdout, priority pressure, impacted assignments, held assignments.
- action features: one-hot deployable shadow policy action.
- target: simulator `policy_score` for that episode/action.

The current model is `linear_fitted_q_shadow_v1`, a dependency-light standardized linear Q approximator. It returns:

- `feature_names`
- train/test/all MAE, RMSE, R2
- pairwise rank accuracy within each episode
- fitted coefficients and feature importance
- predicted best action per episode
- sample predictions with actual vs predicted Q
- `summary.deployable = false`
- `truth_contract.mutation = none`

This is closer to a DQL/DQN training interface than the Q table, but it is still an offline shadow model. It does not control dispatch, does not bypass solver constraints, does not persist model artifacts, and does not mutate business data.

`frontend-next` `/dispatch/scenarios/[id]` renders this as `Fitted-Q Shadow Model`, showing samples, episodes, actions, regression metrics, rank accuracy, predicted actions, and feature importance.

## Shadow Benchmark Scorecard

`/api/dispatch/shadow-benchmark` aggregates the full dispatch AI/RL shadow chain into one readiness report:

- `learning_dataset`
- `policy_scorer`
- `reward_model`
- `disruption_episode_generator`
- `rl_shadow_runner`
- `fitted_q_shadow_model`

It returns:

- component readiness and key metrics.
- gate results for persisted rows, route truth coverage, policy scoring, reward model samples, generated episodes, RL runner, fitted-Q, and non-mutating contracts.
- `summary.readiness_score`
- recommendations for failed gates.
- `summary.deployable = false`
- `truth_contract.mutation = none`

This endpoint is the preferred smoke/acceptance surface for the dispatch AI shadow chain. It is a scorecard, not a deployment switch, and does not mutate business state.

`frontend-next` `/dispatch/scenarios/[id]` renders it as `Shadow Benchmark Scorecard`, so operators can see whether the scenario has enough data quality and shadow-model evidence before reading the detailed RL panels.

`frontend-next` `/dispatch` also renders the same benchmark as a global recent-scenario scorecard using `scenario_limit=50`. This makes the dispatch console the main readiness/acceptance surface for the AI/RL shadow chain, showing readiness score, component readiness, gates, recommendations, and a non-persistent snapshot hash. The snapshot payload is an audit/export envelope only:

- `storage = not_persisted`
- `mutation = none`
- `replay_request.endpoint = /api/dispatch/shadow-benchmark`

It does not apply dispatch changes, persist model artifacts, or mutate `dispatch_scenarios`, `dispatch_assignments`, `orders`, `vehicles`, or `shipment_facts`.

## Verification

Focused verification:

```powershell
python -m pytest backend\tests\test_dispatch_orchestration_layered.py backend\tests\test_dispatch_smart_contract.py -q
cd frontend-next
npm run typecheck
npm run build
```

Current result on 2026-06-20:

- backend dispatch suite: `17 passed`
- Next typecheck: passed
- Next production build: passed
