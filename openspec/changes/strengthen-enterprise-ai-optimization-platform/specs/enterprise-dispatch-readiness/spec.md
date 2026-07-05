## Purpose

Ensure the enterprise demo path can prove real PostgreSQL data, dispatch usability, and provider truth metadata without relying on hidden state.

## Requirements

### Requirement: Vue dispatch page is usable

The system SHALL keep the Vue `/dispatch` page importable, renderable, and able to call wave, preview, smart dispatch, solver comparison, and policy job actions.

#### Scenario: Dispatch view loads

- GIVEN the Vue dev server or production build is running
- WHEN the user navigates to `/dispatch`
- THEN the route SHALL load `DispatchView.vue` without a dynamic import error
- AND primary buttons SHALL be enabled whenever the page has enough wave/vehicle data.

#### Scenario: Dispatch preview and smart dispatch return explainable results

- GIVEN authenticated API access and a PostgreSQL-backed backend
- WHEN `/api/dispatch/preview` or `/api/dispatch/smart` is called
- THEN the response SHALL include `success`, `summary`, `plans`, `unassigned_orders`, `diagnostics`, `solver`, and truth metadata
- AND unassigned orders SHALL include reasons instead of unexplained zero allocation.

### Requirement: Real PostgreSQL readiness is visible

The system SHALL expose whether the backend is using PostgreSQL or a fallback database.

#### Scenario: Real facts connected

- GIVEN the backend is started with the correct PostgreSQL connection
- WHEN `/api/ready` is requested
- THEN the response SHALL include `database_runtime.backend=postgresql`
- AND `database_runtime.shipment_facts` SHALL report the real fact count.

#### Scenario: Fallback database connected

- GIVEN PostgreSQL is not configured
- WHEN `/api/ready` is requested
- THEN the response SHALL include a visible warning that real `shipment_facts` require PostgreSQL configuration.

### Requirement: Provider degradation is explainable

The system SHALL report provider key configuration and degradation reasons without exposing secret values.

#### Scenario: Map provider lacks key

- GIVEN map provider keys are not configured
- WHEN provider health is requested
- THEN the response SHALL report configured booleans and source names only
- AND include a fallback reason explaining the degraded state.
