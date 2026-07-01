"""Dispatch learning dataset service for AI shadow-mode upgrades.

The dataset is built from persisted dispatch_scenarios / dispatch_assignments.
It intentionally exposes a proxy reward for offline policy experiments instead
of claiming that reinforcement learning is already controlling dispatch.
"""

from __future__ import annotations

import json
import math
import hashlib
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from app.models import DispatchAssignment, DispatchScenario
from app.services.shipment_anomaly_service import get_shipment_anomaly_service


DEFAULT_SCENARIO_LIMIT = 50
DEFAULT_ROW_LIMIT = 200
MAX_SCENARIO_LIMIT = 200
MAX_ROW_LIMIT = 1000
MIN_READY_ROWS = 2
DEFAULT_POLICY_TOP_K = 10
MAX_POLICY_TOP_K = 50
DEFAULT_MODEL_TEST_RATIO = 0.3
MIN_MODEL_ROWS = 2
DEFAULT_SIMULATION_TOP_K = 10
DEFAULT_PROFILE_ANOMALY_LIMIT = 80


class DispatchLearningDatasetService:
    """Build compact training rows for dispatch AI shadow experiments."""

    def build_dataset(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        scenario_limit = self._coerce_int(payload.get("scenario_limit"), DEFAULT_SCENARIO_LIMIT)
        row_limit = self._coerce_int(payload.get("row_limit"), DEFAULT_ROW_LIMIT)
        status = self._clean_text(payload.get("status"))
        include_preview = self._coerce_bool(payload.get("include_preview"), True)
        requested_scenario_ids = self._scenario_id_filter(payload)

        scenario_limit = max(1, min(MAX_SCENARIO_LIMIT, scenario_limit))
        row_limit = max(1, min(MAX_ROW_LIMIT, row_limit))

        scenario_query = DispatchScenario.query
        if requested_scenario_ids:
            scenario_query = scenario_query.filter(DispatchScenario.id.in_(requested_scenario_ids))
        if status:
            scenario_query = scenario_query.filter(DispatchScenario.status == status)
        elif not include_preview:
            scenario_query = scenario_query.filter(DispatchScenario.status == "applied")

        scenarios = scenario_query.order_by(DispatchScenario.created_at.desc()).limit(scenario_limit).all()
        scenario_by_id = {scenario.id: scenario for scenario in scenarios}
        scenario_ids = list(scenario_by_id)

        assignments: List[DispatchAssignment] = []
        if scenario_ids:
            assignments = (
                DispatchAssignment.query.filter(DispatchAssignment.scenario_id.in_(scenario_ids))
                .order_by(
                    DispatchAssignment.scenario_id.desc(),
                    DispatchAssignment.vehicle_id,
                    DispatchAssignment.sequence_index,
                )
                .limit(row_limit)
                .all()
            )

        rows: List[Dict[str, Any]] = []
        status_counts: Counter = Counter()
        distance_counts: Counter = Counter()
        provider_counts: Counter = Counter()
        fallback_counts: Counter = Counter()
        vehicle_ids = set()
        order_refs = set()
        route_truth_rows = 0

        for assignment in assignments:
            scenario = scenario_by_id.get(assignment.scenario_id)
            if scenario is None:
                continue
            row = self._row_from_assignment(assignment, scenario)
            rows.append(row)
            status_counts[str(scenario.status or "unknown")] += 1
            vehicle_ids.add(assignment.vehicle_id)
            order_refs.add(assignment.order_ref)

            route_truth = row["truth"].get("route_truth") or {}
            if route_truth:
                route_truth_rows += 1
            self._merge_counts(distance_counts, route_truth.get("distance_source_counts") or {})
            self._merge_counts(provider_counts, route_truth.get("provider_status_counts") or {})
            self._merge_counts(fallback_counts, route_truth.get("fallback_reason_counts") or {})
            if not route_truth:
                distance_counts[str(scenario.distance_source or "unknown")] += 1
                provider_counts[str(scenario.provider_status or "unknown")] += 1

        readiness = self._readiness(len(rows), len(scenarios), route_truth_rows)
        provider_status = "ok" if readiness["ready"] else "degraded"
        fallback_reason = None if readiness["ready"] else readiness["reason"]

        return {
            "success": True,
            "model_family": "rl_shadow_dataset",
            "dataset_version": "rl_shadow_dataset_v1",
            "mode": "shadow_training_dataset",
            "data_source": "dispatch_scenarios_assignments",
            "distance_source": self._primary_count_key(distance_counts),
            "path_source": "dispatch_assignment_sequence",
            "provider_status": provider_status,
            "fallback_reason": fallback_reason,
            "authenticity_level": "B-" if rows else "C",
            "summary": {
                "scenario_count": len(scenarios),
                "assignment_count": len(assignments),
                "row_count": len(rows),
                "scenario_status_counts": dict(status_counts),
                "unique_vehicles": len(vehicle_ids),
                "unique_orders": len(order_refs),
                "route_truth_rows": route_truth_rows,
                "route_truth_coverage": round(route_truth_rows / len(rows), 4) if rows else 0.0,
                "distance_source_counts": dict(distance_counts),
                "provider_status_counts": dict(provider_counts),
                "fallback_reason_counts": dict(fallback_counts),
                "avg_reward_proxy": self._average([row["target"]["reward_proxy"] for row in rows]),
                "avg_load_utilization": self._average(
                    [row["features"]["load_utilization"] for row in rows]
                ),
                "avg_volume_utilization": self._average(
                    [row["features"]["volume_utilization"] for row in rows]
                ),
                "truncated": len(assignments) >= row_limit,
            },
            "filters": {
                "scenario_ids": requested_scenario_ids,
                "status": status,
                "include_preview": include_preview,
                "scenario_limit": scenario_limit,
                "row_limit": row_limit,
            },
            "readiness": readiness,
            "target_definition": self._target_definition(),
            "feature_schema": self._feature_schema(),
            "rows": rows,
            "truth_contract": self._truth_contract(),
        }

    def build_redispatch_profiles(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate disruption profiles from real shipment anomaly signals."""
        payload = dict(payload or {})
        payload.setdefault("row_limit", DEFAULT_ROW_LIMIT)
        dataset = self.build_dataset(payload)
        rows = list(dataset.get("rows") or [])
        anomaly_limit = max(
            1,
            min(
                300,
                self._coerce_int(payload.get("anomaly_limit"), DEFAULT_PROFILE_ANOMALY_LIMIT),
            ),
        )
        anomaly_result = get_shipment_anomaly_service().detect({
            "tasks": payload.get("tasks")
            or ["status", "cost", "eta", "delay", "od_volume", "node_congestion"],
            "limit": self._coerce_int(payload.get("anomaly_source_limit"), 50000),
            "anomaly_limit": anomaly_limit,
            "use_ml": self._coerce_bool(payload.get("use_ml"), False),
            "city": payload.get("city") or payload.get("destination_city"),
        })
        anomalies = list(anomaly_result.get("anomalies") or [])
        profiles = self._profiles_from_anomalies(anomalies, rows)
        readiness = {
            **dict(dataset.get("readiness") or {}),
            "ready": bool(rows),
            "status": "ready_for_anomaly_driven_redispatch_profiles" if rows else "insufficient_profile_rows",
            "reason": None if rows else "NO_DISPATCH_ASSIGNMENTS",
            "row_count": len(rows),
            "anomaly_count": len(anomalies),
            "profile_count": len(profiles),
        }
        provider_status = "ok" if rows and anomaly_result.get("provider_status") == "ok" else "degraded"
        fallback_reason = None if rows else "NO_DISPATCH_ASSIGNMENTS"

        return {
            "success": True,
            "model_family": "dispatch_dynamic_redispatch_shadow",
            "profile_version": "anomaly_driven_redispatch_profiles_v1",
            "dataset_version": dataset.get("dataset_version"),
            "mode": "offline_shadow_disruption_profile_generation",
            "data_source": "dispatch_scenarios_assignments + shipment_fact_anomalies",
            "distance_source": dataset.get("distance_source"),
            "path_source": dataset.get("path_source"),
            "provider_status": provider_status,
            "fallback_reason": fallback_reason,
            "authenticity_level": "B-" if rows else "C",
            "filters": dataset.get("filters") or {},
            "anomaly_summary": anomaly_result.get("summary") or {},
            "anomaly_diagnostics": anomaly_result.get("diagnostics") or {},
            "readiness": readiness,
            "profiles": profiles,
            "truth_contract": {
                **self._truth_contract(),
                "profile_source": "real shipment_fact anomaly detection converted to synthetic simulator parameters",
                "mutation": "none",
            },
        }

    def build_redispatch_scenario_generator(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate and score replayable disruption scenarios from historical signals.

        Profiles describe parameter presets. This generator runs those presets
        through the read-only simulator so the UI and future DQL/DQN jobs can
        consume concrete shadow episodes instead of hand-written examples.
        """
        payload = dict(payload or {})
        payload.setdefault("row_limit", DEFAULT_ROW_LIMIT)
        payload.setdefault("scenario_limit", payload.get("scenario_limit") or 1)
        payload.setdefault("top_k", payload.get("top_k") or DEFAULT_SIMULATION_TOP_K)

        profiles_result = self.build_redispatch_profiles(payload)
        profiles = list(profiles_result.get("profiles") or [])
        dataset = self.build_dataset(payload)
        rows = list(dataset.get("rows") or [])

        scenarios = [self._generated_scenario_from_profile(profile, payload) for profile in profiles]
        vehicle_holdout = self._vehicle_holdout_scenario(rows, profiles_result)
        if vehicle_holdout:
            scenarios.append(vehicle_holdout)

        scored_scenarios: List[Dict[str, Any]] = []
        for scenario in scenarios[:6]:
            simulation_payload = {
                **payload,
                **dict(scenario.get("params") or {}),
                "profile": scenario.get("scenario_id"),
            }
            simulation = self.simulate_redispatch(simulation_payload)
            scored_scenarios.append({
                **scenario,
                "simulation_summary": simulation.get("summary") or {},
                "best_policy": simulation.get("best_policy"),
                "impact_preview": list(simulation.get("impacts") or [])[:5],
                "recommendations": list(simulation.get("recommendations") or [])[:3],
                "simulation_provider_status": simulation.get("provider_status"),
                "simulation_fallback_reason": simulation.get("fallback_reason"),
            })

        ready = bool(rows and scored_scenarios)
        fallback_reason = None if ready else (
            profiles_result.get("fallback_reason")
            or dataset.get("fallback_reason")
            or "NO_GENERATED_SCENARIOS"
        )

        return {
            "success": True,
            "model_family": "dispatch_dynamic_redispatch_shadow",
            "generator_version": "historical_disruption_scenario_generator_v1",
            "dataset_version": dataset.get("dataset_version"),
            "profile_version": profiles_result.get("profile_version"),
            "mode": "offline_shadow_historical_disruption_generation",
            "data_source": "dispatch_scenarios_assignments + shipment_fact_anomalies",
            "distance_source": dataset.get("distance_source"),
            "path_source": dataset.get("path_source"),
            "provider_status": "ok" if ready else "degraded",
            "fallback_reason": fallback_reason,
            "authenticity_level": "B-" if rows else "C",
            "filters": dataset.get("filters") or {},
            "anomaly_summary": profiles_result.get("anomaly_summary") or {},
            "readiness": {
                **dict(dataset.get("readiness") or {}),
                "ready": ready,
                "status": "ready_for_historical_disruption_shadow_generation" if ready else "insufficient_generation_inputs",
                "reason": fallback_reason,
                "row_count": len(rows),
                "profile_count": len(profiles),
                "generated_scenario_count": len(scored_scenarios),
            },
            "summary": {
                "generated_scenario_count": len(scored_scenarios),
                "profile_count": len(profiles),
                "row_count": len(rows),
                "anomaly_count": (profiles_result.get("anomaly_summary") or {}).get("anomaly_count", 0),
                "anomaly_by_type": (profiles_result.get("anomaly_summary") or {}).get("by_type") or {},
                "best_scenario_id": self._best_generated_scenario_id(scored_scenarios),
                "avg_impacted_assignments": self._average([
                    self._safe_float((item.get("simulation_summary") or {}).get("impacted_assignments"))
                    for item in scored_scenarios
                ]),
            },
            "generated_scenarios": scored_scenarios,
            "truth_contract": {
                **self._truth_contract(),
                "scenario_generator": (
                    "real shipment_fact anomaly signals converted to read-only "
                    "redispatch simulator episodes"
                ),
                "mutation": "none",
                "dql_dqn_boundary": "shadow training/evaluation presets only; solver remains the hard-constraint owner",
            },
        }

    def run_rl_shadow_runner(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run an offline Q-shadow benchmark over generated redispatch episodes.

        This is intentionally not a deployed DQN/DQL controller. It treats
        generated disruption episodes as states and existing deployable shadow
        policies as actions, then estimates a small Q table from simulator
        scores. The output is a training/evaluation scaffold for later neural
        RL work while preserving solver ownership of hard constraints.
        """
        payload = dict(payload or {})
        payload.setdefault("row_limit", DEFAULT_ROW_LIMIT)
        payload.setdefault("scenario_limit", payload.get("scenario_limit") or 1)
        payload.setdefault("top_k", payload.get("top_k") or DEFAULT_SIMULATION_TOP_K)

        generator = self.build_redispatch_scenario_generator(payload)
        episodes = list(generator.get("generated_scenarios") or [])
        q_values: Dict[str, Dict[str, List[float]]] = {}
        episode_results: List[Dict[str, Any]] = []
        action_ids: List[str] = []

        for episode in episodes:
            params = dict(episode.get("params") or {})
            simulation_payload = {
                **payload,
                **params,
                "profile": episode.get("scenario_id"),
            }
            simulation = self.simulate_redispatch(simulation_payload)
            policies = list(simulation.get("policies") or [])
            deployable = [policy for policy in policies if policy.get("deployable")]
            baseline = next(
                (policy for policy in policies if policy.get("policy_id") == "historical_solver_order"),
                None,
            )
            selected = max(deployable, key=lambda item: self._safe_float(item.get("policy_score"))) if deployable else None
            state_bucket = self._episode_state_bucket(params)

            for policy in deployable:
                policy_id = str(policy.get("policy_id") or "unknown")
                if policy_id not in action_ids:
                    action_ids.append(policy_id)
                q_values.setdefault(state_bucket, {}).setdefault(policy_id, []).append(
                    self._safe_float(policy.get("policy_score"))
                )

            selected_score = self._safe_float((selected or {}).get("policy_score"))
            baseline_score = self._safe_float((baseline or {}).get("policy_score"))
            episode_results.append({
                "episode_id": episode.get("scenario_id"),
                "state_bucket": state_bucket,
                "source": episode.get("source"),
                "confidence": episode.get("confidence"),
                "selected_action": (selected or {}).get("policy_id"),
                "selected_policy_name": (selected or {}).get("name"),
                "baseline_action": (baseline or {}).get("policy_id"),
                "baseline_score": round(baseline_score, 4),
                "selected_score": round(selected_score, 4),
                "score_delta_vs_baseline": round(selected_score - baseline_score, 4),
                "impacted_assignments": (simulation.get("summary") or {}).get("impacted_assignments"),
                "held_for_reassignment": (simulation.get("summary") or {}).get("held_for_reassignment"),
                "avg_reward_delta": (simulation.get("summary") or {}).get("avg_reward_delta"),
                "policy_scores": [
                    {
                        "policy_id": policy.get("policy_id"),
                        "name": policy.get("name"),
                        "deployable": policy.get("deployable"),
                        "policy_score": policy.get("policy_score"),
                        "score_delta_vs_baseline": policy.get("score_delta_vs_baseline"),
                    }
                    for policy in policies
                ],
            })

        q_table = self._q_table_summary(q_values)
        selected_scores = [self._safe_float(item.get("selected_score")) for item in episode_results]
        baseline_scores = [self._safe_float(item.get("baseline_score")) for item in episode_results]
        deltas = [self._safe_float(item.get("score_delta_vs_baseline")) for item in episode_results]
        ready = bool(episode_results)
        fallback_reason = None if ready else generator.get("fallback_reason") or "NO_RL_SHADOW_EPISODES"

        return {
            "success": True,
            "model_family": "dispatch_rl_shadow_runner",
            "runner_version": "offline_q_shadow_runner_v1",
            "generator_version": generator.get("generator_version"),
            "dataset_version": generator.get("dataset_version"),
            "mode": "offline_shadow_rl_evaluation",
            "data_source": generator.get("data_source"),
            "distance_source": generator.get("distance_source"),
            "path_source": generator.get("path_source"),
            "provider_status": "ok" if ready else "degraded",
            "fallback_reason": fallback_reason,
            "authenticity_level": generator.get("authenticity_level"),
            "filters": generator.get("filters") or {},
            "readiness": {
                **dict(generator.get("readiness") or {}),
                "ready": ready,
                "status": "ready_for_offline_rl_shadow_evaluation" if ready else "insufficient_rl_shadow_inputs",
                "reason": fallback_reason,
                "episode_count": len(episode_results),
                "action_count": len(action_ids),
            },
            "summary": {
                "episode_count": len(episode_results),
                "action_count": len(action_ids),
                "state_bucket_count": len(q_table),
                "avg_baseline_score": self._average(baseline_scores),
                "avg_selected_score": self._average(selected_scores),
                "avg_score_delta_vs_baseline": self._average(deltas),
                "best_episode_id": self._best_rl_episode_id(episode_results),
                "selected_action_counts": dict(Counter(
                    str(item.get("selected_action") or "none") for item in episode_results
                )),
                "deployable": False,
            },
            "state_schema": [
                "delay_pressure",
                "cost_pressure",
                "provider_pressure",
                "vehicle_availability",
                "priority_pressure",
            ],
            "action_space": action_ids,
            "q_table": q_table,
            "episode_results": episode_results,
            "truth_contract": {
                **self._truth_contract(),
                "rl_shadow_runner": (
                    "offline Q-style benchmark over generated disruption episodes; "
                    "not a deployed DQN/DQL controller"
                ),
                "mutation": "none",
                "deployable": False,
                "hard_constraints_owner": "dispatch solver layer (Gurobi/OR-Tools/ALNS/greedy fallback)",
            },
        }

    def train_fitted_q_shadow_model(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Train a lightweight fitted-Q style shadow model.

        This approximates Q(state, action) from simulator policy scores using
        a small standardized linear model. It is an offline benchmark artifact,
        not a deployed neural DQN/DQL policy.
        """
        payload = dict(payload or {})
        payload.setdefault("row_limit", DEFAULT_ROW_LIMIT)
        payload.setdefault("scenario_limit", payload.get("scenario_limit") or 1)
        payload.setdefault("top_k", payload.get("top_k") or DEFAULT_SIMULATION_TOP_K)
        test_ratio = max(
            0.1,
            min(0.8, self._coerce_float(payload.get("test_ratio"), DEFAULT_MODEL_TEST_RATIO)),
        )

        generator = self.build_redispatch_scenario_generator(payload)
        episodes = list(generator.get("generated_scenarios") or [])
        samples: List[Dict[str, Any]] = []

        for episode in episodes:
            params = dict(episode.get("params") or {})
            simulation_payload = {
                **payload,
                **params,
                "profile": episode.get("scenario_id"),
            }
            simulation = self.simulate_redispatch(simulation_payload)
            policies = [policy for policy in list(simulation.get("policies") or []) if policy.get("deployable")]
            for policy in policies:
                samples.append(self._fitted_q_sample(episode, params, simulation, policy))

        action_ids = sorted({str(sample.get("action") or "") for sample in samples if sample.get("action")})
        feature_names = self._fitted_q_feature_names(samples, action_ids)
        split = self._split_fitted_q_samples(samples, test_ratio)

        if len(samples) < MIN_MODEL_ROWS or not feature_names:
            fallback_reason = generator.get("fallback_reason") or "INSUFFICIENT_FITTED_Q_SAMPLES"
            return {
                "success": True,
                "model_family": "dispatch_rl_shadow_runner",
                "model_version": "linear_fitted_q_shadow_v1",
                "runner_version": "offline_q_shadow_runner_v1",
                "generator_version": generator.get("generator_version"),
                "dataset_version": generator.get("dataset_version"),
                "mode": "offline_fitted_q_shadow_training",
                "data_source": generator.get("data_source"),
                "distance_source": generator.get("distance_source"),
                "path_source": generator.get("path_source"),
                "provider_status": "degraded",
                "fallback_reason": fallback_reason,
                "authenticity_level": generator.get("authenticity_level"),
                "filters": generator.get("filters") or {},
                "readiness": {
                    **dict(generator.get("readiness") or {}),
                    "ready": False,
                    "status": "insufficient_fitted_q_samples",
                    "reason": fallback_reason,
                    "sample_count": len(samples),
                    "feature_count": len(feature_names),
                },
                "summary": {
                    "sample_count": len(samples),
                    "episode_count": len(episodes),
                    "action_count": len(action_ids),
                    "deployable": False,
                },
                "feature_names": feature_names,
                "metrics": {},
                "model": None,
                "recommendations": [],
                "predictions": [],
                "truth_contract": {
                    **self._truth_contract(),
                    "fitted_q_shadow_model": "offline fitted-Q approximation only",
                    "mutation": "none",
                    "deployable": False,
                },
            }

        model = self._fit_linear_q_model(split["train"], feature_names)
        train_predictions = self._predict_fitted_q_samples(split["train"], feature_names, model)
        test_predictions = self._predict_fitted_q_samples(split["test"], feature_names, model)
        all_predictions = self._predict_fitted_q_samples(samples, feature_names, model)
        recommendations = self._fitted_q_recommendations(all_predictions)
        ready = bool(samples and recommendations)

        return {
            "success": True,
            "model_family": "dispatch_rl_shadow_runner",
            "model_version": "linear_fitted_q_shadow_v1",
            "runner_version": "offline_q_shadow_runner_v1",
            "generator_version": generator.get("generator_version"),
            "dataset_version": generator.get("dataset_version"),
            "mode": "offline_fitted_q_shadow_training",
            "data_source": generator.get("data_source"),
            "distance_source": generator.get("distance_source"),
            "path_source": generator.get("path_source"),
            "provider_status": "ok" if ready else "degraded",
            "fallback_reason": None if ready else "NO_FITTED_Q_RECOMMENDATIONS",
            "authenticity_level": generator.get("authenticity_level"),
            "filters": generator.get("filters") or {},
            "readiness": {
                **dict(generator.get("readiness") or {}),
                "ready": ready,
                "status": "ready_for_offline_fitted_q_shadow_training" if ready else "insufficient_fitted_q_outputs",
                "reason": None if ready else "NO_FITTED_Q_RECOMMENDATIONS",
                "sample_count": len(samples),
                "train_samples": len(split["train"]),
                "test_samples": len(split["test"]),
                "feature_count": len(feature_names),
                "episode_count": len(episodes),
                "action_count": len(action_ids),
            },
            "summary": {
                "sample_count": len(samples),
                "episode_count": len(episodes),
                "action_count": len(action_ids),
                "best_predicted_action_counts": dict(Counter(
                    str(item.get("predicted_best_action") or "none") for item in recommendations
                )),
                "avg_predicted_q": self._average([
                    self._safe_float(item.get("predicted_best_q")) for item in recommendations
                ]),
                "avg_actual_q": self._average([
                    self._safe_float(item.get("actual_best_q")) for item in recommendations
                ]),
                "deployable": False,
            },
            "feature_names": feature_names,
            "metrics": {
                "train": self._q_regression_metrics(train_predictions),
                "test": self._q_regression_metrics(test_predictions),
                "all": self._q_regression_metrics(all_predictions),
                "rank_accuracy": self._q_pairwise_rank_accuracy(all_predictions),
            },
            "model": {
                "type": "standardized_linear_q_approximator",
                "intercept": round(self._safe_float(model.get("intercept")), 6),
                "coefficients": {
                    key: round(self._safe_float(value), 6)
                    for key, value in (model.get("coefficients") or {}).items()
                },
                "feature_means": model.get("means") or {},
                "feature_scales": model.get("scales") or {},
                "feature_importance": self._feature_importance(model.get("coefficients") or {}),
                "training_note": (
                    "Offline fitted-Q shadow approximation over simulator scores only. "
                    "It is not a deployed DQN/DQL controller."
                ),
            },
            "recommendations": recommendations,
            "predictions": all_predictions[:50],
            "truth_contract": {
                **self._truth_contract(),
                "fitted_q_shadow_model": "offline fitted-Q approximation only",
                "mutation": "none",
                "deployable": False,
                "hard_constraints_owner": "dispatch solver layer (Gurobi/OR-Tools/ALNS/greedy fallback)",
            },
        }

    def build_shadow_benchmark_report(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build a unified scorecard for dispatch AI/RL shadow readiness."""
        payload = dict(payload or {})
        payload.setdefault("row_limit", DEFAULT_ROW_LIMIT)
        payload.setdefault("scenario_limit", payload.get("scenario_limit") or 1)
        payload.setdefault("top_k", payload.get("top_k") or DEFAULT_SIMULATION_TOP_K)

        dataset = self.build_dataset(payload)
        policy = self.score_policies(payload)
        reward = self.train_reward_model(payload)
        generator = self.build_redispatch_scenario_generator(payload)
        rl_runner = self.run_rl_shadow_runner(payload)
        fitted_q = self.train_fitted_q_shadow_model(payload)

        components = [
            self._benchmark_component(
                "learning_dataset",
                "Learning Dataset",
                dataset,
                {
                    "rows": (dataset.get("summary") or {}).get("row_count"),
                    "route_truth_coverage": (dataset.get("summary") or {}).get("route_truth_coverage"),
                    "avg_reward_proxy": (dataset.get("summary") or {}).get("avg_reward_proxy"),
                },
            ),
            self._benchmark_component(
                "policy_scorer",
                "Policy Scorer",
                policy,
                {
                    "best_policy": ((policy.get("best_policy") or {}).get("policy_id")),
                    "best_policy_score": ((policy.get("best_policy") or {}).get("policy_score")),
                },
            ),
            self._benchmark_component(
                "reward_model",
                "Reward Model",
                reward,
                {
                    "sample_count": ((reward.get("metrics") or {}).get("all") or {}).get("sample_count"),
                    "mae": ((reward.get("metrics") or {}).get("all") or {}).get("mae"),
                    "rank_accuracy": (((reward.get("metrics") or {}).get("rank_accuracy") or {}).get("accuracy")),
                },
            ),
            self._benchmark_component(
                "disruption_episode_generator",
                "Disruption Episode Generator",
                generator,
                {
                    "episodes": (generator.get("summary") or {}).get("generated_scenario_count"),
                    "anomalies": (generator.get("summary") or {}).get("anomaly_count"),
                    "avg_impacted_assignments": (generator.get("summary") or {}).get("avg_impacted_assignments"),
                },
            ),
            self._benchmark_component(
                "rl_shadow_runner",
                "RL Shadow Runner",
                rl_runner,
                {
                    "episodes": (rl_runner.get("summary") or {}).get("episode_count"),
                    "actions": (rl_runner.get("summary") or {}).get("action_count"),
                    "avg_score_delta_vs_baseline": (rl_runner.get("summary") or {}).get("avg_score_delta_vs_baseline"),
                },
            ),
            self._benchmark_component(
                "fitted_q_shadow_model",
                "Fitted-Q Shadow Model",
                fitted_q,
                {
                    "samples": (fitted_q.get("summary") or {}).get("sample_count"),
                    "mae": ((fitted_q.get("metrics") or {}).get("all") or {}).get("mae"),
                    "rank_accuracy": (((fitted_q.get("metrics") or {}).get("rank_accuracy") or {}).get("accuracy")),
                },
            ),
        ]
        gates = self._shadow_benchmark_gates(dataset, policy, reward, generator, rl_runner, fitted_q)
        readiness_score = self._benchmark_readiness_score(gates)
        ready = readiness_score >= 0.75

        return {
            "success": True,
            "model_family": "dispatch_ai_shadow_benchmark",
            "benchmark_version": "dispatch_ai_shadow_benchmark_v1",
            "mode": "offline_shadow_readiness_scorecard",
            "data_source": "dispatch_scenarios_assignments + shipment_fact_anomalies",
            "distance_source": dataset.get("distance_source"),
            "path_source": dataset.get("path_source"),
            "provider_status": "ok" if ready else "degraded",
            "fallback_reason": None if ready else self._first_failed_gate_reason(gates),
            "authenticity_level": "B-" if (dataset.get("summary") or {}).get("row_count") else "C",
            "filters": dataset.get("filters") or {},
            "summary": {
                "component_count": len(components),
                "ready_component_count": sum(1 for item in components if item.get("ready")),
                "gate_count": len(gates),
                "passed_gate_count": sum(1 for item in gates if item.get("passed")),
                "readiness_score": readiness_score,
                "shadow_chain": [
                    "learning_dataset",
                    "policy_scorer",
                    "reward_model",
                    "disruption_episode_generator",
                    "rl_shadow_runner",
                    "fitted_q_shadow_model",
                ],
                "deployable": False,
            },
            "components": components,
            "gates": gates,
            "recommendations": self._shadow_benchmark_recommendations(gates),
            "truth_contract": {
                **self._truth_contract(),
                "shadow_benchmark": "offline readiness scorecard over AI/RL shadow components",
                "mutation": "none",
                "deployable": False,
                "hard_constraints_owner": "dispatch solver layer (Gurobi/OR-Tools/ALNS/greedy fallback)",
            },
        }

    def export_shadow_benchmark_snapshot(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return a deterministic, non-persistent audit snapshot payload."""
        payload = dict(payload or {})
        report = self.build_shadow_benchmark_report(payload)
        replay_request = self._shadow_snapshot_replay_request(payload, report)
        snapshot_body = {
            "benchmark_version": report.get("benchmark_version"),
            "mode": report.get("mode"),
            "filters": report.get("filters") or {},
            "summary": report.get("summary") or {},
            "components": report.get("components") or [],
            "gates": report.get("gates") or [],
            "recommendations": report.get("recommendations") or [],
            "truth_contract": report.get("truth_contract") or {},
        }
        content_hash = self._stable_hash(snapshot_body)
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        snapshot_id = f"dispatch-shadow-{content_hash[:12]}"

        return {
            "success": True,
            "model_family": "dispatch_ai_shadow_benchmark",
            "snapshot_version": "dispatch_ai_shadow_snapshot_v1",
            "benchmark_version": report.get("benchmark_version"),
            "mode": "offline_shadow_benchmark_snapshot_export",
            "data_source": report.get("data_source"),
            "distance_source": report.get("distance_source"),
            "path_source": report.get("path_source"),
            "provider_status": report.get("provider_status"),
            "fallback_reason": report.get("fallback_reason"),
            "authenticity_level": report.get("authenticity_level"),
            "snapshot": {
                "snapshot_id": snapshot_id,
                "created_at": created_at,
                "content_hash": content_hash,
                "hash_algorithm": "sha256",
                "storage": "not_persisted",
                "mutation": "none",
                "replay_request": replay_request,
                "summary": report.get("summary") or {},
                "component_count": len(report.get("components") or []),
                "gate_count": len(report.get("gates") or []),
            },
            "scorecard": report,
            "truth_contract": {
                **self._truth_contract(),
                "shadow_benchmark_snapshot": (
                    "deterministic export payload for audit/regression comparison; "
                    "not persisted and not a deployment switch"
                ),
                "mutation": "none",
                "deployable": False,
                "content_hash": content_hash,
            },
        }

    def simulate_redispatch(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run a read-only dynamic re-dispatch shadow simulation.

        This simulates disruption pressure over persisted assignment rows and
        compares simple policy rerankers. It never applies assignments or
        mutates dispatch/order/shipment tables.
        """
        payload = dict(payload or {})
        payload.setdefault("row_limit", DEFAULT_ROW_LIMIT)
        top_k = max(
            1,
            min(MAX_POLICY_TOP_K, self._coerce_int(payload.get("top_k"), DEFAULT_SIMULATION_TOP_K)),
        )
        dataset = self.build_dataset(payload)
        rows = list(dataset.get("rows") or [])
        disruption = self._normalize_disruption(payload.get("disruption") or payload)

        if not rows:
            readiness = {
                **dict(dataset.get("readiness") or {}),
                "ready": False,
                "status": "insufficient_simulation_rows",
                "reason": dataset.get("fallback_reason") or "NO_SIMULATION_ROWS",
                "row_count": 0,
            }
            return {
                "success": True,
                "model_family": "dispatch_dynamic_redispatch_shadow",
                "simulator_version": "dynamic_redispatch_shadow_v1",
                "dataset_version": dataset.get("dataset_version"),
                "mode": "offline_shadow_disruption_simulation",
                "data_source": dataset.get("data_source"),
                "distance_source": dataset.get("distance_source"),
                "path_source": dataset.get("path_source"),
                "provider_status": "degraded",
                "fallback_reason": readiness["reason"],
                "authenticity_level": dataset.get("authenticity_level"),
                "filters": dataset.get("filters") or {},
                "disruption": disruption,
                "readiness": readiness,
                "summary": {},
                "policies": [],
                "best_policy": None,
                "impacts": [],
                "recommendations": [],
                "truth_contract": {
                    **self._truth_contract(),
                    "redispatch_simulator": "offline shadow simulation only",
                    "mutation": "none",
                },
            }

        simulated_rows = [self._simulate_row(row, disruption) for row in rows]
        policies = self._score_policy_suite(simulated_rows, top_k=top_k)
        baseline = next((item for item in policies if item["policy_id"] == "historical_solver_order"), None)
        baseline_score = float((baseline or {}).get("policy_score") or 0.0)
        for policy in policies:
            policy["score_delta_vs_baseline"] = round(float(policy["policy_score"]) - baseline_score, 4)

        deployable = [policy for policy in policies if policy.get("deployable")]
        best_policy = max(deployable, key=lambda item: item["policy_score"]) if deployable else None
        original_rewards = [self._target_value(row, "reward_proxy") for row in rows]
        simulated_rewards = [self._target_value(row, "reward_proxy") for row in simulated_rows]
        held_rows = [row for row in simulated_rows if (row.get("simulation") or {}).get("recommended_action") == "hold_for_reassignment"]
        impacted_rows = [row for row in simulated_rows if (row.get("simulation") or {}).get("impact_flags")]
        readiness = {
            **dict(dataset.get("readiness") or {}),
            "ready": bool(simulated_rows),
            "status": "ready_for_dynamic_redispatch_shadow",
            "reason": None,
            "row_count": len(simulated_rows),
            "top_k": min(top_k, len(simulated_rows)),
        }

        return {
            "success": True,
            "model_family": "dispatch_dynamic_redispatch_shadow",
            "simulator_version": "dynamic_redispatch_shadow_v1",
            "dataset_version": dataset.get("dataset_version"),
            "mode": "offline_shadow_disruption_simulation",
            "data_source": dataset.get("data_source"),
            "distance_source": dataset.get("distance_source"),
            "path_source": dataset.get("path_source"),
            "provider_status": "ok" if dataset.get("provider_status") == "ok" else "degraded",
            "fallback_reason": dataset.get("fallback_reason"),
            "authenticity_level": dataset.get("authenticity_level"),
            "filters": dataset.get("filters") or {},
            "disruption": disruption,
            "readiness": readiness,
            "summary": {
                "row_count": len(simulated_rows),
                "impacted_assignments": len(impacted_rows),
                "held_for_reassignment": len(held_rows),
                "avg_original_reward_proxy": self._average(original_rewards),
                "avg_simulated_reward_proxy": self._average(simulated_rewards),
                "avg_reward_delta": round(self._average(simulated_rewards) - self._average(original_rewards), 4),
                "best_policy_id": (best_policy or {}).get("policy_id"),
                "best_policy_score": (best_policy or {}).get("policy_score"),
                "best_policy_delta_vs_baseline": (best_policy or {}).get("score_delta_vs_baseline"),
                "simulation_note": (
                    "Hard dispatch constraints remain solver-owned. This simulator only "
                    "scores shadow reordering suggestions under synthetic disruptions."
                ),
            },
            "policies": policies,
            "best_policy": best_policy,
            "impacts": [
                {
                    "scenario_id": row.get("scenario_id"),
                    "assignment_id": row.get("assignment_id"),
                    "order_ref": row.get("order_ref"),
                    "vehicle_id": row.get("vehicle_id"),
                    "vehicle_plate": row.get("vehicle_plate"),
                    "original_reward_proxy": (row.get("simulation") or {}).get("original_reward_proxy"),
                    "simulated_reward_proxy": self._target_value(row, "reward_proxy"),
                    "reward_delta": (row.get("simulation") or {}).get("reward_delta"),
                    "recommended_action": (row.get("simulation") or {}).get("recommended_action"),
                    "impact_flags": (row.get("simulation") or {}).get("impact_flags") or [],
                    "provider_status": (row.get("truth") or {}).get("provider_status"),
                }
                for row in sorted(
                    simulated_rows,
                    key=lambda item: self._safe_float((item.get("simulation") or {}).get("reward_delta")),
                )[: min(20, len(simulated_rows))]
            ],
            "recommendations": self._simulation_recommendations(best_policy, held_rows, impacted_rows),
            "truth_contract": {
                **self._truth_contract(),
                "redispatch_simulator": "offline shadow simulation only",
                "mutation": "none",
                "disruption_source": "synthetic payload parameters",
            },
        }

    def score_policies(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Compare simple offline shadow policies over rl_shadow_dataset_v1 rows."""
        payload = dict(payload or {})
        top_k = max(
            1,
            min(MAX_POLICY_TOP_K, self._coerce_int(payload.get("top_k"), DEFAULT_POLICY_TOP_K)),
        )
        dataset = self.build_dataset(payload)
        rows = list(dataset.get("rows") or [])
        policies = self._score_policy_suite(rows, top_k=top_k)
        baseline = next((item for item in policies if item["policy_id"] == "historical_solver_order"), None)
        baseline_score = float((baseline or {}).get("policy_score") or 0.0)

        for policy in policies:
            policy["score_delta_vs_baseline"] = round(float(policy["policy_score"]) - baseline_score, 4)

        best_policy = None
        deployable = [policy for policy in policies if policy.get("deployable")]
        if deployable:
            best_policy = max(deployable, key=lambda item: item["policy_score"])

        readiness = dict(dataset.get("readiness") or {})
        if rows and policies:
            readiness.update({
                "policy_rows": len(rows),
                "top_k": min(top_k, len(rows)),
                "status": "ready_for_shadow_policy_scoring" if readiness.get("ready") else readiness.get("status"),
            })

        return {
            "success": True,
            "model_family": "rl_shadow_policy_scorer",
            "scorer_version": "dispatch_policy_shadow_scorer_v1",
            "dataset_version": dataset.get("dataset_version"),
            "mode": "offline_shadow_policy_comparison",
            "data_source": dataset.get("data_source"),
            "distance_source": dataset.get("distance_source"),
            "path_source": dataset.get("path_source"),
            "provider_status": "ok" if rows and policies and dataset.get("provider_status") == "ok" else "degraded",
            "fallback_reason": dataset.get("fallback_reason") if not rows else None,
            "authenticity_level": dataset.get("authenticity_level"),
            "dataset_summary": dataset.get("summary") or {},
            "filters": dataset.get("filters") or {},
            "readiness": readiness,
            "target_definition": {
                **self._target_definition(),
                "scoring_note": (
                    "Policies are evaluated offline against persisted assignment rows. "
                    "No business state is mutated and no policy bypasses solver constraints."
                ),
            },
            "policies": policies,
            "best_policy": best_policy,
            "truth_contract": {
                **self._truth_contract(),
                "policy_scorer": "offline shadow comparison only",
            },
        }

    def train_reward_model(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fit a lightweight contextual reward ranker for offline shadow evaluation."""
        payload = dict(payload or {})
        dataset = self.build_dataset(payload)
        rows = list(dataset.get("rows") or [])
        feature_names = self._model_feature_names(rows)
        test_ratio = self._coerce_float(payload.get("test_ratio"), DEFAULT_MODEL_TEST_RATIO)
        test_ratio = max(0.1, min(0.5, test_ratio))

        if len(rows) < MIN_MODEL_ROWS or not feature_names:
            readiness = {
                **dict(dataset.get("readiness") or {}),
                "ready": False,
                "status": "insufficient_model_rows",
                "reason": "INSUFFICIENT_MODEL_ROWS",
                "minimum_rows": MIN_MODEL_ROWS,
                "row_count": len(rows),
                "feature_count": len(feature_names),
            }
            return {
                "success": True,
                "model_family": "dispatch_shadow_reward_model",
                "model_version": "linear_reward_ranker_v1",
                "dataset_version": dataset.get("dataset_version"),
                "mode": "offline_shadow_model_training",
                "data_source": dataset.get("data_source"),
                "distance_source": dataset.get("distance_source"),
                "path_source": dataset.get("path_source"),
                "provider_status": "degraded",
                "fallback_reason": readiness["reason"],
                "authenticity_level": dataset.get("authenticity_level"),
                "dataset_summary": dataset.get("summary") or {},
                "filters": dataset.get("filters") or {},
                "readiness": readiness,
                "feature_names": feature_names,
                "metrics": {},
                "model": None,
                "predictions": [],
                "truth_contract": {
                    **self._truth_contract(),
                    "reward_model": "offline shadow learning baseline only",
                },
            }

        split = self._train_test_split(rows, test_ratio)
        model = self._fit_linear_reward_ranker(split["train"], feature_names)
        train_predictions = self._predict_rows(split["train"], feature_names, model)
        test_predictions = self._predict_rows(split["test"], feature_names, model)
        all_predictions = self._predict_rows(rows, feature_names, model)
        metrics = {
            "train": self._regression_metrics(train_predictions),
            "test": self._regression_metrics(test_predictions),
            "all": self._regression_metrics(all_predictions),
            "rank_accuracy": self._pairwise_rank_accuracy(all_predictions),
        }

        coefficients = model["coefficients"]
        feature_importance = sorted(
            [
                {
                    "feature": name,
                    "weight": round(coefficients.get(name, 0.0), 6),
                    "abs_weight": round(abs(coefficients.get(name, 0.0)), 6),
                }
                for name in feature_names
            ],
            key=lambda item: item["abs_weight"],
            reverse=True,
        )
        readiness = {
            **dict(dataset.get("readiness") or {}),
            "ready": True,
            "status": "ready_for_shadow_reward_model",
            "reason": None,
            "row_count": len(rows),
            "train_rows": len(split["train"]),
            "test_rows": len(split["test"]),
            "feature_count": len(feature_names),
        }

        return {
            "success": True,
            "model_family": "dispatch_shadow_reward_model",
            "model_version": "linear_reward_ranker_v1",
            "dataset_version": dataset.get("dataset_version"),
            "mode": "offline_shadow_model_training",
            "data_source": dataset.get("data_source"),
            "distance_source": dataset.get("distance_source"),
            "path_source": dataset.get("path_source"),
            "provider_status": "ok" if dataset.get("provider_status") == "ok" else "degraded",
            "fallback_reason": dataset.get("fallback_reason"),
            "authenticity_level": dataset.get("authenticity_level"),
            "dataset_summary": dataset.get("summary") or {},
            "filters": dataset.get("filters") or {},
            "readiness": readiness,
            "feature_names": feature_names,
            "metrics": metrics,
            "model": {
                "type": "standardized_linear_regression",
                "intercept": round(model["intercept"], 6),
                "coefficients": {key: round(value, 6) for key, value in coefficients.items()},
                "feature_means": {key: round(value, 6) for key, value in model["means"].items()},
                "feature_scales": {key: round(value, 6) for key, value in model["scales"].items()},
                "feature_importance": feature_importance,
                "training_note": (
                    "This model predicts offline reward_proxy for shadow ranking only. "
                    "It is not a dispatch solver and does not apply business actions."
                ),
            },
            "predictions": all_predictions[: min(10, len(all_predictions))],
            "truth_contract": {
                **self._truth_contract(),
                "reward_model": "offline shadow learning baseline only",
            },
        }

    def _row_from_assignment(
        self,
        assignment: DispatchAssignment,
        scenario: DispatchScenario,
    ) -> Dict[str, Any]:
        summary = self._json_loads(scenario.summary_json, {})
        scenario_diagnostics = self._json_loads(scenario.diagnostics_json, {})
        ai_shadow = self._json_loads(scenario.ai_shadow_json, {})
        assignment_diagnostics = self._json_loads(assignment.diagnostics_json, {})
        route_truth = assignment_diagnostics.get("route_truth") or summary.get("route_truth") or {}

        load_utilization = self._safe_float(assignment_diagnostics.get("load_utilization"))
        volume_utilization = self._safe_float(assignment_diagnostics.get("volume_utilization"))
        assigned_orders = self._safe_float(
            summary.get("assigned_orders") or summary.get("total_orders_assigned")
        )
        unassigned_orders = self._safe_float(
            summary.get("unassigned_orders") or summary.get("total_orders_unassigned")
        )
        risk_score = self._safe_float(ai_shadow.get("risk_score"))
        provider_status = self._route_provider_status(route_truth, scenario.provider_status)
        reliability_score = self._provider_reliability(provider_status)

        features = {
            "weight_tons": round(self._safe_float(assignment.weight_kg) / 1000.0, 4),
            "volume_m3": round(self._safe_float(assignment.volume_m3), 4),
            "distance_km": round(self._safe_float(assignment.distance_km), 4),
            "duration_min": round(self._safe_float(assignment.duration_min), 4),
            "cost": round(self._safe_float(assignment.cost), 4),
            "sequence_index": int(assignment.sequence_index or 0),
            "load_utilization": round(load_utilization, 4),
            "volume_utilization": round(volume_utilization, 4),
            "route_leg_count": int(route_truth.get("leg_count") or 0),
            "route_estimated_leg_count": int(route_truth.get("estimated_leg_count") or 0),
            "scenario_assigned_orders": round(assigned_orders, 4),
            "scenario_unassigned_orders": round(unassigned_orders, 4),
            "scenario_total_distance": round(
                self._safe_float(summary.get("total_distance_km") or summary.get("total_distance")),
                4,
            ),
            "scenario_total_cost": round(self._safe_float(summary.get("total_cost")), 4),
            "capacity_gap_weight_kg": round(
                self._safe_float(scenario_diagnostics.get("capacity_gap_weight_kg")),
                4,
            ),
            "ai_shadow_risk_score": round(risk_score, 4),
            "provider_reliability_score": reliability_score,
            "is_applied": 1 if scenario.status == "applied" else 0,
        }

        target = self._reward_proxy(features, provider_status)

        return {
            "scenario_id": scenario.id,
            "scenario_code": scenario.scenario_code,
            "scenario_status": scenario.status,
            "solver": scenario.solver,
            "assignment_id": assignment.id,
            "vehicle_id": assignment.vehicle_id,
            "vehicle_plate": assignment.vehicle_plate,
            "order_source": assignment.order_source,
            "order_ref": assignment.order_ref,
            "order_number": assignment.order_number,
            "assignment_status": assignment.assignment_status,
            "state_key": f"{scenario.id}:{assignment.vehicle_id}:{assignment.sequence_index}",
            "action": {
                "assign_to_vehicle_id": assignment.vehicle_id,
                "sequence_index": assignment.sequence_index,
            },
            "features": features,
            "target": target,
            "truth": {
                "data_source": scenario.data_source or assignment.order_source,
                "distance_source": scenario.distance_source,
                "path_source": "dispatch_assignment_sequence",
                "provider_status": provider_status,
                "fallback_reason": scenario.fallback_reason,
                "authenticity_level": scenario.authenticity_level,
                "route_truth": route_truth,
            },
        }

    def _normalize_disruption(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        unavailable_vehicle_ids = self._int_list(raw.get("unavailable_vehicle_ids"))
        delay_vehicle_ids = self._int_list(raw.get("delay_vehicle_ids"))
        priority_order_refs = self._string_list(raw.get("priority_order_refs"))
        delay_minutes = max(0.0, self._coerce_float(raw.get("delay_minutes"), 45.0))
        cost_multiplier = self._coerce_float(raw.get("cost_multiplier"), 1.12)
        if cost_multiplier <= 0:
            cost_multiplier = 1.0
        provider_degradation = self._coerce_bool(raw.get("provider_degradation"), True)
        reliability_drop = max(0.0, min(0.9, self._coerce_float(raw.get("reliability_drop"), 0.25)))
        return {
            "profile": self._clean_text(raw.get("profile")) or "delay_cost_provider_pressure",
            "delay_minutes": round(delay_minutes, 2),
            "delay_vehicle_ids": delay_vehicle_ids,
            "unavailable_vehicle_ids": unavailable_vehicle_ids,
            "priority_order_refs": priority_order_refs[:50],
            "cost_multiplier": round(cost_multiplier, 4),
            "provider_degradation": provider_degradation,
            "reliability_drop": round(reliability_drop, 4),
        }

    def _simulate_row(self, row: Dict[str, Any], disruption: Dict[str, Any]) -> Dict[str, Any]:
        simulated = json.loads(json.dumps(row, ensure_ascii=False))
        features = simulated.get("features") or {}
        target = simulated.get("target") or {}
        truth = simulated.get("truth") or {}
        vehicle_id = self._coerce_int(simulated.get("vehicle_id"), 0)
        order_ref = str(simulated.get("order_ref") or "")
        impact_flags: List[str] = []
        original_reward = self._target_value(simulated, "reward_proxy")
        delay_vehicle_ids = set(disruption.get("delay_vehicle_ids") or [])
        unavailable_vehicle_ids = set(disruption.get("unavailable_vehicle_ids") or [])
        priority_order_refs = set(disruption.get("priority_order_refs") or [])

        delay_applies = not delay_vehicle_ids or vehicle_id in delay_vehicle_ids
        if delay_applies and disruption.get("delay_minutes", 0) > 0:
            features["duration_min"] = round(self._feature_value(simulated, "duration_min") + disruption["delay_minutes"], 4)
            impact_flags.append("delay")

        cost_multiplier = self._safe_float(disruption.get("cost_multiplier") or 1.0)
        if abs(cost_multiplier - 1.0) > 1e-9:
            features["cost"] = round(self._feature_value(simulated, "cost") * cost_multiplier, 4)
            impact_flags.append("cost_pressure")

        if disruption.get("provider_degradation"):
            reliability = max(
                0.05,
                self._feature_value(simulated, "provider_reliability_score")
                - self._safe_float(disruption.get("reliability_drop")),
            )
            features["provider_reliability_score"] = round(reliability, 4)
            truth["provider_status"] = "degraded"
            truth["fallback_reason"] = "SIMULATED_PROVIDER_DEGRADATION"
            impact_flags.append("provider_degradation")

        recommended_action = "rerank_candidate"
        if vehicle_id in unavailable_vehicle_ids:
            features["provider_reliability_score"] = 0.05
            recommended_action = "hold_for_reassignment"
            impact_flags.append("vehicle_unavailable")
        elif order_ref in priority_order_refs:
            features["ai_shadow_risk_score"] = max(0.0, self._feature_value(simulated, "ai_shadow_risk_score") - 5.0)
            recommended_action = "prioritize_in_rerank"
            impact_flags.append("priority_order")

        simulated["features"] = features
        simulated["truth"] = truth
        simulated_reward = self._reward_proxy(features, truth.get("provider_status") or "unknown")
        if vehicle_id in unavailable_vehicle_ids:
            simulated_reward["reward_proxy"] = round(simulated_reward["reward_proxy"] - 45.0, 4)
        target.update(simulated_reward)
        simulated["target"] = target
        simulated["simulation"] = {
            "original_reward_proxy": round(original_reward, 4),
            "simulated_reward_proxy": simulated_reward["reward_proxy"],
            "reward_delta": round(simulated_reward["reward_proxy"] - original_reward, 4),
            "recommended_action": recommended_action,
            "impact_flags": impact_flags,
        }
        return simulated

    def _simulation_recommendations(
        self,
        best_policy: Optional[Dict[str, Any]],
        held_rows: Sequence[Dict[str, Any]],
        impacted_rows: Sequence[Dict[str, Any]],
    ) -> List[str]:
        recommendations = [
            "Run the selected shadow policy as a candidate reranking input; keep final apply behind the dispatch solver.",
        ]
        if best_policy:
            recommendations.append(
                f"Best deployable shadow policy under disruption: {best_policy.get('name')} "
                f"({best_policy.get('policy_id')})."
            )
        if held_rows:
            recommendations.append(
                f"{len(held_rows)} assignments should be held for solver-backed reassignment because their vehicles are unavailable."
            )
        if impacted_rows:
            recommendations.append(
                f"{len(impacted_rows)} assignments changed score under the synthetic disruption; inspect lowest reward deltas first."
            )
        return recommendations

    def _episode_state_bucket(self, params: Dict[str, Any]) -> str:
        delay_minutes = self._safe_float(params.get("delay_minutes"))
        cost_multiplier = self._safe_float(params.get("cost_multiplier") or 1.0)
        provider_degradation = self._coerce_bool(params.get("provider_degradation"), False)
        unavailable_vehicle_ids = self._int_list(params.get("unavailable_vehicle_ids"))
        priority_order_refs = self._string_list(params.get("priority_order_refs"))
        delay_bucket = "delay_high" if delay_minutes >= 90 else "delay_low" if delay_minutes > 0 else "delay_none"
        cost_bucket = "cost_high" if cost_multiplier >= 1.25 else "cost_mild" if cost_multiplier > 1.01 else "cost_none"
        provider_bucket = "provider_degraded" if provider_degradation else "provider_normal"
        vehicle_bucket = "vehicle_holdout" if unavailable_vehicle_ids else "vehicle_available"
        priority_bucket = "priority_orders" if priority_order_refs else "priority_none"
        return "|".join([delay_bucket, cost_bucket, provider_bucket, vehicle_bucket, priority_bucket])

    def _q_table_summary(self, values: Dict[str, Dict[str, List[float]]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for state_bucket, action_scores in sorted(values.items()):
            action_values = [
                {
                    "action": action,
                    "q_value": self._average(scores),
                    "sample_count": len(scores),
                }
                for action, scores in sorted(action_scores.items())
            ]
            best_action = max(action_values, key=lambda item: self._safe_float(item.get("q_value"))) if action_values else None
            rows.append({
                "state_bucket": state_bucket,
                "best_action": (best_action or {}).get("action"),
                "best_q_value": (best_action or {}).get("q_value"),
                "action_values": action_values,
            })
        return rows

    def _best_rl_episode_id(self, episodes: Sequence[Dict[str, Any]]) -> Optional[str]:
        if not episodes:
            return None
        best = max(
            episodes,
            key=lambda item: self._safe_float(item.get("score_delta_vs_baseline")),
        )
        return str(best.get("episode_id") or "") or None

    def _benchmark_component(
        self,
        component_id: str,
        name: str,
        result: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        readiness = result.get("readiness") or {}
        ready = bool(readiness.get("ready") or result.get("success") and not result.get("fallback_reason"))
        return {
            "component_id": component_id,
            "name": name,
            "ready": ready,
            "status": readiness.get("status") or ("ready" if ready else "degraded"),
            "reason": readiness.get("reason") or result.get("fallback_reason"),
            "provider_status": result.get("provider_status"),
            "authenticity_level": result.get("authenticity_level"),
            "metrics": metrics,
        }

    def _shadow_benchmark_gates(
        self,
        dataset: Dict[str, Any],
        policy: Dict[str, Any],
        reward: Dict[str, Any],
        generator: Dict[str, Any],
        rl_runner: Dict[str, Any],
        fitted_q: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        dataset_summary = dataset.get("summary") or {}
        reward_metrics = reward.get("metrics") or {}
        fitted_metrics = fitted_q.get("metrics") or {}
        contracts = [
            dataset.get("truth_contract") or {},
            policy.get("truth_contract") or {},
            reward.get("truth_contract") or {},
            generator.get("truth_contract") or {},
            rl_runner.get("truth_contract") or {},
            fitted_q.get("truth_contract") or {},
        ]
        return [
            self._benchmark_gate(
                "persisted_assignment_rows",
                bool((dataset.get("readiness") or {}).get("ready")),
                "NO_READY_DISPATCH_ASSIGNMENT_ROWS",
                {"row_count": dataset_summary.get("row_count")},
            ),
            self._benchmark_gate(
                "route_truth_coverage",
                self._safe_float(dataset_summary.get("route_truth_coverage")) > 0,
                "MISSING_ROUTE_TRUTH_COVERAGE",
                {"route_truth_coverage": dataset_summary.get("route_truth_coverage")},
            ),
            self._benchmark_gate(
                "policy_shadow_ready",
                bool(policy.get("best_policy")),
                "NO_SHADOW_POLICY_SCORE",
                {"best_policy": (policy.get("best_policy") or {}).get("policy_id")},
            ),
            self._benchmark_gate(
                "reward_model_ready",
                self._safe_float((reward_metrics.get("all") or {}).get("sample_count")) >= MIN_MODEL_ROWS,
                "INSUFFICIENT_REWARD_MODEL_SAMPLES",
                {"sample_count": (reward_metrics.get("all") or {}).get("sample_count")},
            ),
            self._benchmark_gate(
                "disruption_episodes_ready",
                self._safe_float((generator.get("summary") or {}).get("generated_scenario_count")) > 0,
                "NO_GENERATED_DISRUPTION_EPISODES",
                {"episode_count": (generator.get("summary") or {}).get("generated_scenario_count")},
            ),
            self._benchmark_gate(
                "rl_shadow_runner_ready",
                bool((rl_runner.get("readiness") or {}).get("ready")),
                "RL_SHADOW_RUNNER_NOT_READY",
                {"episode_count": (rl_runner.get("summary") or {}).get("episode_count")},
            ),
            self._benchmark_gate(
                "fitted_q_shadow_ready",
                bool((fitted_q.get("readiness") or {}).get("ready")),
                "FITTED_Q_SHADOW_NOT_READY",
                {"sample_count": (fitted_q.get("summary") or {}).get("sample_count")},
            ),
            self._benchmark_gate(
                "non_mutating_shadow_contract",
                all(contract.get("mutation", "none") == "none" for contract in contracts),
                "MUTATING_SHADOW_CONTRACT_DETECTED",
                {"contract_count": len(contracts)},
            ),
        ]

    @staticmethod
    def _benchmark_gate(
        gate_id: str,
        passed: bool,
        failure_reason: str,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "gate_id": gate_id,
            "passed": bool(passed),
            "reason": None if passed else failure_reason,
            "evidence": evidence,
        }

    @staticmethod
    def _benchmark_readiness_score(gates: Sequence[Dict[str, Any]]) -> float:
        if not gates:
            return 0.0
        return round(sum(1 for gate in gates if gate.get("passed")) / len(gates), 4)

    @staticmethod
    def _first_failed_gate_reason(gates: Sequence[Dict[str, Any]]) -> Optional[str]:
        failed = next((gate for gate in gates if not gate.get("passed")), None)
        return (failed or {}).get("reason")

    @staticmethod
    def _shadow_benchmark_recommendations(gates: Sequence[Dict[str, Any]]) -> List[str]:
        failed = [gate for gate in gates if not gate.get("passed")]
        if not failed:
            return [
                "Shadow benchmark is ready for authenticated real-data smoke and snapshot comparison.",
                "Keep all RL/DQL outputs in shadow mode until solver-backed apply checks are added.",
            ]
        recommendations = []
        for gate in failed[:4]:
            gate_id = gate.get("gate_id")
            if gate_id == "persisted_assignment_rows":
                recommendations.append("Create or apply a dispatch scenario so assignment rows exist for shadow evaluation.")
            elif gate_id == "route_truth_coverage":
                recommendations.append("Backfill or preserve dispatch route_truth before comparing policies.")
            elif gate_id == "disruption_episodes_ready":
                recommendations.append("Generate anomaly-driven redispatch episodes from shipment_facts before RL benchmarking.")
            elif gate_id == "fitted_q_shadow_ready":
                recommendations.append("Increase scenario/row limits or episode diversity before fitted-Q evaluation.")
            else:
                recommendations.append(f"Resolve benchmark gate `{gate_id}` before treating the shadow report as ready.")
        return recommendations

    def _shadow_snapshot_replay_request(
        self,
        payload: Dict[str, Any],
        report: Dict[str, Any],
    ) -> Dict[str, Any]:
        filters = dict(report.get("filters") or {})
        return {
            "endpoint": "/api/dispatch/shadow-benchmark",
            "method": "POST",
            "body": {
                "scenario_ids": filters.get("scenario_ids") or self._scenario_id_filter(payload),
                "scenario_limit": filters.get("scenario_limit") or payload.get("scenario_limit") or 1,
                "row_limit": filters.get("row_limit") or payload.get("row_limit") or DEFAULT_ROW_LIMIT,
                "top_k": payload.get("top_k") or DEFAULT_SIMULATION_TOP_K,
                "test_ratio": payload.get("test_ratio") or DEFAULT_MODEL_TEST_RATIO,
                "anomaly_limit": payload.get("anomaly_limit") or DEFAULT_PROFILE_ANOMALY_LIMIT,
                "use_ml": self._coerce_bool(payload.get("use_ml"), False),
                "include_preview": filters.get("include_preview"),
                "status": filters.get("status"),
            },
        }

    @staticmethod
    def _stable_hash(value: Dict[str, Any]) -> str:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _fitted_q_sample(
        self,
        episode: Dict[str, Any],
        params: Dict[str, Any],
        simulation: Dict[str, Any],
        policy: Dict[str, Any],
    ) -> Dict[str, Any]:
        action = str(policy.get("policy_id") or "unknown")
        state_bucket = self._episode_state_bucket(params)
        features = {
            "delay_minutes": self._safe_float(params.get("delay_minutes")),
            "cost_multiplier": self._safe_float(params.get("cost_multiplier") or 1.0),
            "provider_degradation": 1.0 if self._coerce_bool(params.get("provider_degradation"), False) else 0.0,
            "reliability_drop": self._safe_float(params.get("reliability_drop")),
            "vehicle_holdout": 1.0 if self._int_list(params.get("unavailable_vehicle_ids")) else 0.0,
            "priority_order_count": float(len(self._string_list(params.get("priority_order_refs")))),
            "top_k": self._safe_float(params.get("top_k") or DEFAULT_SIMULATION_TOP_K),
            "impacted_assignments": self._safe_float((simulation.get("summary") or {}).get("impacted_assignments")),
            "held_for_reassignment": self._safe_float((simulation.get("summary") or {}).get("held_for_reassignment")),
        }
        features[f"action::{action}"] = 1.0
        return {
            "episode_id": episode.get("scenario_id"),
            "state_bucket": state_bucket,
            "action": action,
            "policy_name": policy.get("name"),
            "features": features,
            "target_q": self._safe_float(policy.get("policy_score")),
            "score_delta_vs_baseline": self._safe_float(policy.get("score_delta_vs_baseline")),
            "deployable": bool(policy.get("deployable")),
        }

    def _fitted_q_feature_names(
        self,
        samples: Sequence[Dict[str, Any]],
        action_ids: Sequence[str],
    ) -> List[str]:
        base_names = [
            "delay_minutes",
            "cost_multiplier",
            "provider_degradation",
            "reliability_drop",
            "vehicle_holdout",
            "priority_order_count",
            "top_k",
            "impacted_assignments",
            "held_for_reassignment",
        ]
        available = set()
        for sample in samples:
            features = sample.get("features") or {}
            for name in base_names:
                if name in features:
                    available.add(name)
        names = [name for name in base_names if name in available]
        names.extend(f"action::{action}" for action in action_ids)
        return names

    def _split_fitted_q_samples(
        self,
        samples: Sequence[Dict[str, Any]],
        test_ratio: float,
    ) -> Dict[str, List[Dict[str, Any]]]:
        ordered = sorted(
            samples,
            key=lambda item: (str(item.get("episode_id") or ""), str(item.get("action") or "")),
        )
        if len(ordered) <= 1:
            return {"train": list(ordered), "test": []}
        test_count = max(1, int(round(len(ordered) * test_ratio)))
        test_count = min(test_count, len(ordered) - 1)
        return {"train": ordered[:-test_count], "test": ordered[-test_count:]}

    def _fit_linear_q_model(
        self,
        samples: Sequence[Dict[str, Any]],
        feature_names: Sequence[str],
    ) -> Dict[str, Any]:
        targets = [self._safe_float(sample.get("target_q")) for sample in samples]
        intercept = self._average(targets)
        means: Dict[str, float] = {}
        scales: Dict[str, float] = {}
        coefficients: Dict[str, float] = {}

        for name in feature_names:
            values = [
                self._safe_float((sample.get("features") or {}).get(name))
                for sample in samples
            ]
            mean = self._average(values)
            variance = self._average([(value - mean) ** 2 for value in values])
            scale = math.sqrt(variance) if variance > 1e-12 else 1.0
            means[name] = mean
            scales[name] = scale
            if variance <= 1e-12:
                coefficients[name] = 0.0
                continue
            covariance = self._average([
                ((value - mean) / scale) * (target - intercept)
                for value, target in zip(values, targets)
            ])
            coefficients[name] = covariance / (1.0 + 0.05 * len(feature_names))

        return {
            "intercept": intercept,
            "means": means,
            "scales": scales,
            "coefficients": coefficients,
        }

    def _predict_fitted_q_samples(
        self,
        samples: Sequence[Dict[str, Any]],
        feature_names: Sequence[str],
        model: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        predictions: List[Dict[str, Any]] = []
        for sample in samples:
            prediction = self._safe_float(model.get("intercept"))
            features = sample.get("features") or {}
            for name in feature_names:
                value = self._safe_float(features.get(name))
                mean = self._safe_float((model.get("means") or {}).get(name))
                scale = self._safe_float((model.get("scales") or {}).get(name)) or 1.0
                coefficient = self._safe_float((model.get("coefficients") or {}).get(name))
                prediction += coefficient * ((value - mean) / scale)
            actual = self._safe_float(sample.get("target_q"))
            predictions.append({
                "episode_id": sample.get("episode_id"),
                "state_bucket": sample.get("state_bucket"),
                "action": sample.get("action"),
                "policy_name": sample.get("policy_name"),
                "actual_q": round(actual, 4),
                "predicted_q": round(prediction, 4),
                "error": round(prediction - actual, 4),
                "score_delta_vs_baseline": sample.get("score_delta_vs_baseline"),
            })
        return predictions

    def _fitted_q_recommendations(self, predictions: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for prediction in predictions:
            grouped.setdefault(str(prediction.get("episode_id") or "unknown"), []).append(prediction)

        recommendations: List[Dict[str, Any]] = []
        for episode_id, items in sorted(grouped.items()):
            predicted_best = max(items, key=lambda item: self._safe_float(item.get("predicted_q")))
            actual_best = max(items, key=lambda item: self._safe_float(item.get("actual_q")))
            recommendations.append({
                "episode_id": episode_id,
                "state_bucket": predicted_best.get("state_bucket"),
                "predicted_best_action": predicted_best.get("action"),
                "predicted_best_policy_name": predicted_best.get("policy_name"),
                "predicted_best_q": predicted_best.get("predicted_q"),
                "actual_best_action": actual_best.get("action"),
                "actual_best_q": actual_best.get("actual_q"),
                "matches_actual_best": predicted_best.get("action") == actual_best.get("action"),
            })
        return recommendations

    def _q_regression_metrics(self, predictions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        if not predictions:
            return {"sample_count": 0, "mae": None, "rmse": None, "r2": None}
        actuals = [self._safe_float(item.get("actual_q")) for item in predictions]
        errors = [self._safe_float(item.get("error")) for item in predictions]
        mae = self._average([abs(error) for error in errors])
        rmse = math.sqrt(self._average([error * error for error in errors]))
        actual_mean = self._average(actuals)
        total_ss = sum((actual - actual_mean) ** 2 for actual in actuals)
        residual_ss = sum(error * error for error in errors)
        r2 = None if total_ss <= 1e-12 else round(1.0 - residual_ss / total_ss, 4)
        return {
            "sample_count": len(predictions),
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "r2": r2,
        }

    def _q_pairwise_rank_accuracy(self, predictions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for prediction in predictions:
            grouped.setdefault(str(prediction.get("episode_id") or "unknown"), []).append(prediction)
        comparable = 0
        correct = 0
        for items in grouped.values():
            for index, left in enumerate(items):
                for right in items[index + 1:]:
                    actual_delta = self._safe_float(left.get("actual_q")) - self._safe_float(right.get("actual_q"))
                    predicted_delta = self._safe_float(left.get("predicted_q")) - self._safe_float(right.get("predicted_q"))
                    if abs(actual_delta) <= 1e-9:
                        continue
                    comparable += 1
                    if actual_delta * predicted_delta > 0:
                        correct += 1
        return {
            "pair_count": comparable,
            "correct_pairs": correct,
            "accuracy": round(correct / comparable, 4) if comparable else None,
        }

    def _feature_importance(self, coefficients: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows = [
            {
                "feature": key,
                "weight": round(self._safe_float(value), 6),
                "abs_weight": round(abs(self._safe_float(value)), 6),
            }
            for key, value in coefficients.items()
        ]
        return sorted(rows, key=lambda item: item["abs_weight"], reverse=True)

    def _generated_scenario_from_profile(
        self,
        profile: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        params = dict(profile.get("params") or {})
        params.setdefault("top_k", self._coerce_int(payload.get("top_k"), DEFAULT_SIMULATION_TOP_K))
        return {
            "scenario_id": profile.get("profile_id") or "generated_profile",
            "name": profile.get("name") or profile.get("profile_id") or "Generated Profile",
            "description": profile.get("description"),
            "source": profile.get("source") or "shipment_fact_anomaly_profile",
            "confidence": profile.get("confidence") or "low",
            "params": params,
            "evidence": profile.get("evidence") or {},
            "training_use": "dql_dqn_shadow_episode_preset",
        }

    def _vehicle_holdout_scenario(
        self,
        rows: Sequence[Dict[str, Any]],
        profiles_result: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not rows:
            return None

        vehicle_scores: Dict[int, List[float]] = {}
        for row in rows:
            vehicle_id = self._coerce_int(row.get("vehicle_id"), 0)
            if vehicle_id <= 0:
                continue
            vehicle_scores.setdefault(vehicle_id, []).append(self._target_value(row, "reward_proxy"))
        if not vehicle_scores:
            return None

        selected_vehicle = min(
            vehicle_scores,
            key=lambda vehicle_id: self._average(vehicle_scores[vehicle_id]),
        )
        anomaly_summary = profiles_result.get("anomaly_summary") or {}
        by_type = anomaly_summary.get("by_type") or {}
        pressure_count = sum(
            int(value or 0)
            for key, value in by_type.items()
            if any(token in str(key) for token in ["status", "delay", "node", "geo"])
        )
        confidence = "medium" if pressure_count else "low"

        return {
            "scenario_id": "vehicle_holdout_recovery",
            "name": "Vehicle Holdout Recovery",
            "description": (
                "Stress-tests one low-reward vehicle stream as unavailable and "
                "checks whether shadow policies surface solver-backed reassignment candidates."
            ),
            "source": "dispatch_assignment_reward_pressure + shipment_fact_anomaly_summary",
            "confidence": confidence,
            "params": {
                "delay_minutes": 45,
                "cost_multiplier": 1.08,
                "provider_degradation": pressure_count > 0,
                "reliability_drop": 0.25 if pressure_count else 0.15,
                "unavailable_vehicle_ids": [selected_vehicle],
                "top_k": 10,
            },
            "evidence": {
                "selected_vehicle_id": selected_vehicle,
                "vehicle_avg_reward_proxy": self._average(vehicle_scores[selected_vehicle]),
                "pressure_anomaly_count": pressure_count,
                "anomaly_by_type": by_type,
            },
            "training_use": "dql_dqn_shadow_episode_preset",
        }

    def _profiles_from_anomalies(
        self,
        anomalies: Sequence[Dict[str, Any]],
        rows: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        by_type = Counter(str(item.get("anomaly_type") or "unknown") for item in anomalies)
        matched_order_refs = self._matched_order_refs(anomalies, rows)
        high_delay_values = [
            self._safe_float(item.get("value"))
            for item in anomalies
            if str(item.get("task")) in {"delay", "eta"} and self._safe_float(item.get("value")) > 0
        ]
        cost_scores = [
            self._safe_float(item.get("score"))
            for item in anomalies
            if str(item.get("task")) == "cost"
        ]
        provider_pressure = any(
            str(item.get("task")) in {"geo", "status", "node_congestion"}
            or str(item.get("anomaly_type")) in {"coordinate_missing", "coordinate_out_of_bounds", "status_exception"}
            for item in anomalies
        )
        avg_delay = self._average(high_delay_values)
        avg_cost_score = self._average(cost_scores)
        delay_minutes = int(max(30, min(360, avg_delay or 60)))
        cost_multiplier = round(1.0 + min(0.8, max(0.08, avg_cost_score / 160.0 if avg_cost_score else 0.12)), 2)
        reliability_drop = round(0.35 if provider_pressure else 0.2, 2)

        profiles = [
            {
                "profile_id": "anomaly_balanced_pressure",
                "name": "Anomaly Balanced Pressure",
                "description": "Combines real delay, cost, and provider anomaly signals into a conservative shadow rerank.",
                "source": "shipment_fact_anomaly_summary",
                "confidence": "medium" if anomalies else "low",
                "params": {
                    "delay_minutes": delay_minutes,
                    "cost_multiplier": cost_multiplier,
                    "provider_degradation": provider_pressure or bool(anomalies),
                    "reliability_drop": reliability_drop,
                    "priority_order_refs": matched_order_refs[:20],
                    "top_k": 10,
                },
                "evidence": {
                    "anomaly_count": len(anomalies),
                    "by_type": dict(by_type),
                    "matched_order_refs": matched_order_refs[:20],
                },
            },
            {
                "profile_id": "delay_recovery",
                "name": "Delay Recovery",
                "description": "Emphasizes ETA/delay anomaly recovery and prioritizes delayed orders in shadow scoring.",
                "source": "shipment_fact_delay_anomalies",
                "confidence": "medium" if high_delay_values else "low",
                "params": {
                    "delay_minutes": delay_minutes,
                    "cost_multiplier": 1.05,
                    "provider_degradation": False,
                    "reliability_drop": 0.1,
                    "priority_order_refs": matched_order_refs[:20],
                    "top_k": 10,
                },
                "evidence": {
                    "delay_anomaly_count": sum(1 for item in anomalies if str(item.get("task")) in {"delay", "eta"}),
                    "avg_delay_minutes": avg_delay,
                    "matched_order_refs": matched_order_refs[:20],
                },
            },
            {
                "profile_id": "cost_guard",
                "name": "Cost Guard",
                "description": "Uses real cost outlier pressure to stress-test cost-guarded reranking.",
                "source": "shipment_fact_cost_anomalies",
                "confidence": "medium" if cost_scores else "low",
                "params": {
                    "delay_minutes": 15,
                    "cost_multiplier": cost_multiplier,
                    "provider_degradation": False,
                    "reliability_drop": 0.1,
                    "priority_order_refs": [],
                    "top_k": 10,
                },
                "evidence": {
                    "cost_anomaly_count": sum(1 for item in anomalies if str(item.get("task")) == "cost"),
                    "avg_cost_score": avg_cost_score,
                    "by_type": {key: value for key, value in by_type.items() if "cost" in key},
                },
            },
        ]
        return profiles

    def _matched_order_refs(
        self,
        anomalies: Sequence[Dict[str, Any]],
        rows: Sequence[Dict[str, Any]],
    ) -> List[str]:
        row_refs = {str(row.get("order_ref") or "") for row in rows}
        row_numbers = {str(row.get("order_number") or "") for row in rows}
        matches: List[str] = []
        for item in anomalies:
            candidates = [
                item.get("order_id"),
                item.get("shipment_id"),
                item.get("source_id"),
            ]
            for candidate in candidates:
                text = str(candidate or "")
                if text and (text in row_refs or text in row_numbers) and text not in matches:
                    matches.append(text)
        if matches:
            return matches
        return [str(row.get("order_ref")) for row in rows[:10] if row.get("order_ref")]

    def _best_generated_scenario_id(self, scenarios: Sequence[Dict[str, Any]]) -> Optional[str]:
        if not scenarios:
            return None
        best = max(
            scenarios,
            key=lambda item: self._safe_float((item.get("simulation_summary") or {}).get("best_policy_score")),
        )
        return str(best.get("scenario_id") or "") or None

    def _reward_proxy(self, features: Dict[str, Any], provider_status: str) -> Dict[str, Any]:
        utilization_score = min(1.0, max(features["load_utilization"], features["volume_utilization"]))
        cost_penalty = min(30.0, features["cost"] / 1000.0)
        duration_penalty = min(15.0, features["duration_min"] / 120.0)
        unassigned_penalty = min(20.0, features["scenario_unassigned_orders"] * 2.0)
        risk_penalty = min(15.0, features["ai_shadow_risk_score"] / 10.0)
        reliability = self._provider_reliability(provider_status)
        applied_bonus = 5.0 if features["is_applied"] else 0.0
        reward = (
            utilization_score * 45.0
            + reliability * 25.0
            + applied_bonus
            - cost_penalty
            - duration_penalty
            - unassigned_penalty
            - risk_penalty
        )
        return {
            "reward_proxy": round(reward, 4),
            "utilization_score": round(utilization_score, 4),
            "reliability_score": reliability,
            "cost_penalty": round(cost_penalty, 4),
            "duration_penalty": round(duration_penalty, 4),
            "unassigned_penalty": round(unassigned_penalty, 4),
            "risk_penalty": round(risk_penalty, 4),
            "target_type": "offline_proxy_reward",
        }

    def _score_policy_suite(self, rows: Sequence[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        if not rows:
            return []

        policies = [
            {
                "policy_id": "historical_solver_order",
                "policy_family": "baseline",
                "name": "Historical Solver Order",
                "description": "Uses the persisted assignment order as the baseline.",
                "deployable": True,
                "rows": list(rows),
            },
            {
                "policy_id": "balanced_shadow",
                "policy_family": "heuristic_shadow",
                "name": "Balanced Shadow",
                "description": "Balances proxy reward, utilization, provider reliability, cost, and risk.",
                "deployable": True,
                "rows": sorted(rows, key=self._balanced_policy_key, reverse=True),
            },
            {
                "policy_id": "utilization_first",
                "policy_family": "heuristic_shadow",
                "name": "Utilization First",
                "description": "Prioritizes load/volume utilization before cost and risk.",
                "deployable": True,
                "rows": sorted(rows, key=self._utilization_policy_key, reverse=True),
            },
            {
                "policy_id": "reliability_first",
                "policy_family": "heuristic_shadow",
                "name": "Reliability First",
                "description": "Prioritizes provider-backed route truth and fewer estimated legs.",
                "deployable": True,
                "rows": sorted(rows, key=self._reliability_policy_key, reverse=True),
            },
            {
                "policy_id": "risk_averse",
                "policy_family": "heuristic_shadow",
                "name": "Risk Averse",
                "description": "Penalizes AI shadow risk before considering reward proxy.",
                "deployable": True,
                "rows": sorted(rows, key=self._risk_averse_policy_key, reverse=True),
            },
            {
                "policy_id": "cost_guarded",
                "policy_family": "heuristic_shadow",
                "name": "Cost Guarded",
                "description": "Prefers lower cost while retaining route-truth reliability.",
                "deployable": True,
                "rows": sorted(rows, key=self._cost_guarded_policy_key, reverse=True),
            },
            {
                "policy_id": "reward_oracle_upper_bound",
                "policy_family": "offline_upper_bound",
                "name": "Reward Oracle Upper Bound",
                "description": "Sorts by known proxy reward; useful only as an offline upper bound.",
                "deployable": False,
                "rows": sorted(rows, key=lambda row: self._target_value(row, "reward_proxy"), reverse=True),
            },
        ]

        return [self._policy_summary(policy, top_k=top_k) for policy in policies]

    def _policy_summary(self, policy: Dict[str, Any], top_k: int) -> Dict[str, Any]:
        ordered_rows = list(policy.pop("rows"))
        selected = ordered_rows[: min(top_k, len(ordered_rows))]
        discounted = self._discounted_reward(ordered_rows)
        top_reward = self._average([self._target_value(row, "reward_proxy") for row in selected])
        policy_score = round(top_reward * 0.65 + discounted * 0.35, 4)

        return {
            **policy,
            "row_count": len(ordered_rows),
            "top_k": len(selected),
            "top_k_reward_proxy": top_reward,
            "discounted_reward_proxy": discounted,
            "policy_score": policy_score,
            "avg_load_utilization": self._average(
                [self._feature_value(row, "load_utilization") for row in selected]
            ),
            "avg_volume_utilization": self._average(
                [self._feature_value(row, "volume_utilization") for row in selected]
            ),
            "avg_cost": self._average([self._feature_value(row, "cost") for row in selected]),
            "avg_risk_score": self._average(
                [self._feature_value(row, "ai_shadow_risk_score") for row in selected]
            ),
            "avg_provider_reliability": self._average(
                [self._feature_value(row, "provider_reliability_score") for row in selected]
            ),
            "top_actions": [
                {
                    "rank": index + 1,
                    "scenario_id": row.get("scenario_id"),
                    "order_ref": row.get("order_ref"),
                    "vehicle_id": row.get("vehicle_id"),
                    "reward_proxy": self._target_value(row, "reward_proxy"),
                    "provider_status": (row.get("truth") or {}).get("provider_status"),
                }
                for index, row in enumerate(selected[:5])
            ],
        }

    def _balanced_policy_key(self, row: Dict[str, Any]) -> float:
        reward = self._target_value(row, "reward_proxy")
        reliability = self._feature_value(row, "provider_reliability_score")
        utilization = max(
            self._feature_value(row, "load_utilization"),
            self._feature_value(row, "volume_utilization"),
        )
        cost = self._feature_value(row, "cost")
        risk = self._feature_value(row, "ai_shadow_risk_score")
        return reward + reliability * 10.0 + utilization * 8.0 - cost / 1200.0 - risk / 10.0

    def _utilization_policy_key(self, row: Dict[str, Any]) -> float:
        utilization = max(
            self._feature_value(row, "load_utilization"),
            self._feature_value(row, "volume_utilization"),
        )
        return (
            utilization * 100.0
            + self._feature_value(row, "provider_reliability_score") * 8.0
            + self._target_value(row, "reward_proxy") / 10.0
        )

    def _reliability_policy_key(self, row: Dict[str, Any]) -> float:
        estimated_legs = self._feature_value(row, "route_estimated_leg_count")
        return (
            self._feature_value(row, "provider_reliability_score") * 100.0
            - estimated_legs * 5.0
            + self._target_value(row, "reward_proxy") / 5.0
        )

    def _risk_averse_policy_key(self, row: Dict[str, Any]) -> float:
        return (
            self._feature_value(row, "provider_reliability_score") * 30.0
            + self._target_value(row, "reward_proxy")
            - self._feature_value(row, "ai_shadow_risk_score") * 1.5
        )

    def _cost_guarded_policy_key(self, row: Dict[str, Any]) -> float:
        return (
            self._feature_value(row, "provider_reliability_score") * 30.0
            + self._target_value(row, "reward_proxy")
            - self._feature_value(row, "cost") / 150.0
            - self._feature_value(row, "duration_min") / 30.0
        )

    def _discounted_reward(self, rows: Sequence[Dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        denominator = sum(1.0 / (index + 1) for index in range(len(rows)))
        if denominator <= 0:
            return 0.0
        score = sum(
            self._target_value(row, "reward_proxy") / (index + 1)
            for index, row in enumerate(rows)
        )
        return round(score / denominator, 4)

    def _feature_value(self, row: Dict[str, Any], key: str) -> float:
        return self._safe_float((row.get("features") or {}).get(key))

    def _target_value(self, row: Dict[str, Any], key: str) -> float:
        return self._safe_float((row.get("target") or {}).get(key))

    def _model_feature_names(self, rows: Sequence[Dict[str, Any]]) -> List[str]:
        preferred = [
            "weight_tons",
            "volume_m3",
            "distance_km",
            "duration_min",
            "cost",
            "sequence_index",
            "load_utilization",
            "volume_utilization",
            "route_leg_count",
            "route_estimated_leg_count",
            "scenario_assigned_orders",
            "scenario_unassigned_orders",
            "scenario_total_distance",
            "scenario_total_cost",
            "capacity_gap_weight_kg",
            "ai_shadow_risk_score",
            "provider_reliability_score",
            "is_applied",
        ]
        available = set()
        for row in rows:
            features = row.get("features") or {}
            for name in preferred:
                value = features.get(name)
                if isinstance(value, (int, float)) and math.isfinite(float(value)):
                    available.add(name)
        return [name for name in preferred if name in available]

    def _train_test_split(
        self,
        rows: Sequence[Dict[str, Any]],
        test_ratio: float,
    ) -> Dict[str, List[Dict[str, Any]]]:
        ordered = sorted(
            rows,
            key=lambda row: (
                int(row.get("scenario_id") or 0),
                int(row.get("assignment_id") or 0),
                str(row.get("order_ref") or ""),
            ),
        )
        if len(ordered) <= 1:
            return {"train": list(ordered), "test": []}
        test_count = max(1, int(round(len(ordered) * test_ratio)))
        test_count = min(test_count, len(ordered) - 1)
        return {
            "train": ordered[:-test_count],
            "test": ordered[-test_count:],
        }

    def _fit_linear_reward_ranker(
        self,
        rows: Sequence[Dict[str, Any]],
        feature_names: Sequence[str],
    ) -> Dict[str, Any]:
        targets = [self._target_value(row, "reward_proxy") for row in rows]
        intercept = self._average(targets)
        means: Dict[str, float] = {}
        scales: Dict[str, float] = {}
        coefficients: Dict[str, float] = {}

        for name in feature_names:
            values = [self._feature_value(row, name) for row in rows]
            mean = self._average(values)
            variance = self._average([(value - mean) ** 2 for value in values])
            scale = math.sqrt(variance) if variance > 1e-12 else 1.0
            means[name] = mean
            scales[name] = scale
            if variance <= 1e-12:
                coefficients[name] = 0.0
                continue
            covariance = self._average(
                [
                    ((value - mean) / scale) * (target - intercept)
                    for value, target in zip(values, targets)
                ]
            )
            coefficients[name] = covariance / (1.0 + 0.05 * len(feature_names))

        return {
            "intercept": intercept,
            "means": means,
            "scales": scales,
            "coefficients": coefficients,
        }

    def _predict_rows(
        self,
        rows: Sequence[Dict[str, Any]],
        feature_names: Sequence[str],
        model: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        predictions: List[Dict[str, Any]] = []
        for row in rows:
            prediction = float(model["intercept"])
            for name in feature_names:
                value = self._feature_value(row, name)
                mean = model["means"].get(name, 0.0)
                scale = model["scales"].get(name, 1.0) or 1.0
                prediction += model["coefficients"].get(name, 0.0) * ((value - mean) / scale)
            actual = self._target_value(row, "reward_proxy")
            predictions.append({
                "scenario_id": row.get("scenario_id"),
                "assignment_id": row.get("assignment_id"),
                "order_ref": row.get("order_ref"),
                "vehicle_id": row.get("vehicle_id"),
                "actual_reward_proxy": round(actual, 4),
                "predicted_reward_proxy": round(prediction, 4),
                "error": round(prediction - actual, 4),
                "provider_status": (row.get("truth") or {}).get("provider_status"),
                "data_source": (row.get("truth") or {}).get("data_source"),
            })
        return predictions

    def _regression_metrics(self, predictions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        if not predictions:
            return {"sample_count": 0, "mae": None, "rmse": None, "r2": None}
        actuals = [self._safe_float(item.get("actual_reward_proxy")) for item in predictions]
        errors = [self._safe_float(item.get("error")) for item in predictions]
        mae = self._average([abs(error) for error in errors])
        rmse = math.sqrt(self._average([error * error for error in errors]))
        actual_mean = self._average(actuals)
        total_ss = sum((actual - actual_mean) ** 2 for actual in actuals)
        residual_ss = sum(error * error for error in errors)
        r2 = None if total_ss <= 1e-12 else round(1.0 - residual_ss / total_ss, 4)
        return {
            "sample_count": len(predictions),
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "r2": r2,
        }

    def _pairwise_rank_accuracy(self, predictions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        comparable = 0
        correct = 0
        for index, left in enumerate(predictions):
            for right in predictions[index + 1:]:
                actual_delta = self._safe_float(left.get("actual_reward_proxy")) - self._safe_float(
                    right.get("actual_reward_proxy")
                )
                predicted_delta = self._safe_float(left.get("predicted_reward_proxy")) - self._safe_float(
                    right.get("predicted_reward_proxy")
                )
                if abs(actual_delta) <= 1e-9:
                    continue
                comparable += 1
                if actual_delta * predicted_delta > 0:
                    correct += 1
        return {
            "pair_count": comparable,
            "correct_pairs": correct,
            "accuracy": round(correct / comparable, 4) if comparable else None,
        }

    @staticmethod
    def _target_definition() -> Dict[str, Any]:
        return {
            "task": "dispatch_policy_shadow_ranking",
            "action": "assign_order_to_vehicle_sequence",
            "target": "reward_proxy",
            "hard_constraints_note": (
                "Capacity, order uniqueness, and vehicle availability remain enforced by "
                "dispatch/OR solvers. This dataset is for offline shadow scoring only."
            ),
            "reward_proxy_formula": (
                "utilization + provider reliability + applied bonus - cost/duration/"
                "unassigned/risk penalties"
            ),
        }

    @staticmethod
    def _feature_schema() -> List[Dict[str, str]]:
        return [
            {"name": "weight_tons", "type": "number", "description": "Assigned order weight"},
            {"name": "volume_m3", "type": "number", "description": "Assigned order volume"},
            {"name": "distance_km", "type": "number", "description": "Plan-level distance proxy"},
            {"name": "duration_min", "type": "number", "description": "Plan-level duration proxy"},
            {"name": "cost", "type": "number", "description": "Plan-level cost proxy"},
            {"name": "sequence_index", "type": "integer", "description": "Order sequence in vehicle plan"},
            {"name": "load_utilization", "type": "number", "description": "Vehicle load utilization"},
            {"name": "volume_utilization", "type": "number", "description": "Vehicle volume utilization"},
            {"name": "route_leg_count", "type": "integer", "description": "Assignment truth leg count"},
            {"name": "route_estimated_leg_count", "type": "integer", "description": "Estimated/degraded legs"},
            {"name": "scenario_unassigned_orders", "type": "number", "description": "Unassigned orders"},
            {"name": "ai_shadow_risk_score", "type": "number", "description": "Existing shadow risk score"},
            {"name": "provider_reliability_score", "type": "number", "description": "Route truth reliability"},
            {"name": "is_applied", "type": "binary", "description": "Scenario has been applied"},
        ]

    @staticmethod
    def _truth_contract() -> Dict[str, Any]:
        return {
            "data_source": "dispatch_scenarios + dispatch_assignments",
            "distance_source": "assignment route_truth distance_source_counts when available",
            "path_source": "dispatch_assignment_sequence",
            "authenticity_level": "B- when rows are derived from persisted dispatch scenarios",
            "fallback_reason": "NO_DISPATCH_ASSIGNMENTS or MISSING_ROUTE_TRUTH when not ready",
        }

    @staticmethod
    def _readiness(row_count: int, scenario_count: int, route_truth_rows: int) -> Dict[str, Any]:
        if scenario_count == 0:
            return {
                "ready": False,
                "status": "no_scenarios",
                "reason": "NO_DISPATCH_SCENARIOS",
                "minimum_rows": MIN_READY_ROWS,
                "row_count": row_count,
            }
        if row_count < MIN_READY_ROWS:
            return {
                "ready": False,
                "status": "insufficient_assignments",
                "reason": "NO_DISPATCH_ASSIGNMENTS",
                "minimum_rows": MIN_READY_ROWS,
                "row_count": row_count,
            }
        if route_truth_rows == 0:
            return {
                "ready": False,
                "status": "missing_route_truth",
                "reason": "MISSING_ROUTE_TRUTH",
                "minimum_rows": MIN_READY_ROWS,
                "row_count": row_count,
            }
        return {
            "ready": True,
            "status": "ready_for_shadow_training",
            "reason": None,
            "minimum_rows": MIN_READY_ROWS,
            "row_count": row_count,
        }

    @staticmethod
    def _route_provider_status(route_truth: Dict[str, Any], fallback: Optional[str]) -> str:
        counts = route_truth.get("provider_status_counts") or {}
        if counts.get("failed"):
            return "failed"
        if counts.get("degraded"):
            return "degraded"
        if counts.get("partial"):
            return "partial"
        if counts.get("ok"):
            return "ok"
        return fallback or "unknown"

    @staticmethod
    def _provider_reliability(provider_status: str) -> float:
        return {
            "ok": 1.0,
            "partial": 0.75,
            "degraded": 0.45,
            "failed": 0.1,
        }.get(str(provider_status or "unknown"), 0.3)

    @staticmethod
    def _merge_counts(target: Counter, source: Dict[str, Any]) -> None:
        for key, value in source.items():
            try:
                target[str(key)] += int(value)
            except (TypeError, ValueError):
                continue

    @staticmethod
    def _primary_count_key(counts: Counter) -> str:
        if not counts:
            return "none"
        return counts.most_common(1)[0][0]

    @staticmethod
    def _json_loads(value: Optional[str], default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except Exception:
            return default

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _coerce_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_bool(value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y", "on"}:
                return True
            if normalized in {"0", "false", "no", "n", "off"}:
                return False
        return bool(value)

    @staticmethod
    def _clean_text(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @classmethod
    def _scenario_id_filter(cls, payload: Dict[str, Any]) -> List[int]:
        values: List[Any] = []
        if payload.get("scenario_id") is not None:
            values.append(payload.get("scenario_id"))
        raw_many = payload.get("scenario_ids")
        if isinstance(raw_many, str):
            values.extend(part.strip() for part in raw_many.split(","))
        elif isinstance(raw_many, (list, tuple, set)):
            values.extend(raw_many)
        elif raw_many is not None:
            values.append(raw_many)

        scenario_ids: List[int] = []
        for value in values:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed > 0 and parsed not in scenario_ids:
                scenario_ids.append(parsed)
        return scenario_ids[:MAX_SCENARIO_LIMIT]

    @classmethod
    def _int_list(cls, value: Any) -> List[int]:
        if value is None:
            return []
        if isinstance(value, str):
            values = [part.strip() for part in value.split(",")]
        elif isinstance(value, (list, tuple, set)):
            values = list(value)
        else:
            values = [value]
        result: List[int] = []
        for item in values:
            try:
                parsed = int(item)
            except (TypeError, ValueError):
                continue
            if parsed > 0 and parsed not in result:
                result.append(parsed)
        return result

    @staticmethod
    def _string_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            values = [part.strip() for part in value.split(",")]
        elif isinstance(value, (list, tuple, set)):
            values = [str(part).strip() for part in value]
        else:
            values = [str(value).strip()]
        result: List[str] = []
        for item in values:
            if item and item not in result:
                result.append(item)
        return result

    @staticmethod
    def _average(values: Sequence[float]) -> float:
        if not values:
            return 0.0
        return round(sum(float(value or 0.0) for value in values) / len(values), 4)


_dispatch_learning_dataset_service: Optional[DispatchLearningDatasetService] = None


def get_dispatch_learning_dataset_service() -> DispatchLearningDatasetService:
    global _dispatch_learning_dataset_service
    if _dispatch_learning_dataset_service is None:
        _dispatch_learning_dataset_service = DispatchLearningDatasetService()
    return _dispatch_learning_dataset_service
