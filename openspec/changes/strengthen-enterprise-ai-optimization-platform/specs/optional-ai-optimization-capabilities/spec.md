## Purpose

Expose installed optimization, ML, RL, and geospatial runtimes as optional capabilities that can strengthen solver and shadow workflows without blocking normal startup.

## Requirements

### Requirement: Optional runtimes are safely probed

The system SHALL provide a safe capability endpoint for optimization, AI, RL, and geospatial libraries.

#### Scenario: Runtime is installed

- GIVEN a runtime such as Gurobi, CPLEX, OR-Tools, pymoo, Torch, SB3, Optuna, LightGBM, Transformers, or a geospatial package is importable
- WHEN capability health is requested
- THEN the response SHALL mark it available
- AND include a safe version string when available.

#### Scenario: Runtime is missing or not configured

- GIVEN a runtime is not importable or lacks a license/configuration
- WHEN capability health is requested
- THEN the response SHALL stay HTTP 200
- AND mark the row degraded with `fallback_reason` and `fallback_to`.

### Requirement: Solver hard constraints remain solver-owned

The system SHALL keep exact/heuristic solvers responsible for capacity, uniqueness, time windows, and feasibility validation.

#### Scenario: RL capability is available

- GIVEN Torch or Stable-Baselines3 is available
- WHEN dispatch policy or decision console status is computed
- THEN the response SHALL describe RL as shadow/rerank only
- AND SHALL NOT mark RL output as deployable without solver validation.

### Requirement: Multi-objective capability uses pymoo

The system SHALL expose pymoo availability and keep NSGA-II/NSGA-III paths as bounded multi-objective capabilities.

#### Scenario: pymoo is available

- GIVEN `pymoo` can be imported
- WHEN solver capabilities are listed
- THEN NSGA-II/NSGA-III SHALL be marked available for multi-objective analysis.
