# Model, data, and architecture

## Data dictionary

| Collection | Fields and meaning |
| --- | --- |
| suppliers | `id`, `name`, display-only location |
| components | `id`, `name` |
| products | `id`, `name`, assembly minutes per finished unit |
| bom | product, component, positive units per product |
| offers | supplier, component, normal/expedited mode, approved flag, shared capacity, integer unit cost, lead days |
| stock | usable opening quantity by component |
| orders | product, whole-unit demand, priority weight, selling price, due day |
| planned | offer quantities restricting the existing sourcing policy |
| case settings | horizon, assembly/delivery reserve, default procurement budget, total assembly capacity |

`supplyshield/data.py` generates all records with seed 7. It includes shared BOM components, a sole-source component, timely alternatives, and a late alternative. `validation.py` checks identifiers, references, row limits, quantities, shipping modes, and shared-capacity agreement before modeling. There is no scraped or confidential supplier data.

`database.py` uses a normalized in-memory SQLite database. Demand is aggregated through orders and the BOM before joining sourcing counts; this prevents offer multiplicity from inflating demand. The graph shows supplier → component → product reachability. Material quantities determine actual shortages.

## Static decisions

Purchase units `x_offer` and fulfilled order units `z_order` are nonnegative integers. Each fulfillment is bounded by demand. Shared supplier/component purchases are bounded by capacity across shipping modes. BOM consumption is bounded by stock plus eligible arrivals. Cost is bounded by budget; assembly usage is bounded by available minutes. Unapproved and late offers are ineligible.

Stage one maximizes priority-weighted fulfilled units. Only if proven optimal does stage two hold that score and minimize procurement cost. An incumbent without proof is labeled FEASIBLE. An absent incumbent returns a verified baseline fallback in the static orchestration path. The independent checker recomputes conservation, cost, capacity, and assembly from allocations.

The static model has one common deadline and purchases at the start of the horizon. Lead days plus the assembly/delivery reserve must fit the horizon. It is not a detailed factory schedule. Cost is procurement spend; gross sales exposure is not profit or realized loss.

## Daily and uncertainty extensions

The daily planner places purchases at the start, receives them no earlier than day one, conserves inventory each day, imposes per-day and total assembly limits, and enforces each order's production-plus-reserve deadline. It does not allow rolling purchase placement or ERP writeback. Its exported result carries model version, input hash, solve limit, schedule, status, and independent inventory history.

Stress testing commits purchases before observing each sample. It then evaluates received inventory and demand without new procurement. Capacity, added delay, and demand choices are independent uniform assumptions, not fitted probabilities. Seeds 41 and 97 provide distinct reproducible evaluation sets. There is no future-aware reoptimization in the samples.

## Deployment boundary

The public Pages demo runs bounded exact enumeration for the included three-SKU fixture entirely in the browser. Python uses CP-SAT and supports the validated input limits. Metrics/objectives/costs are compared across 24 common scenarios plus the hand fixture. Enumeration is deliberately bounded to five seconds and cannot claim optimality after timeout.

Streamlit exposes the Python workflow and advanced experiments locally. FastAPI offers `/v1/simulate`, `/v1/stress`, `/v1/daily` and matching convenience routes, plus sample/health endpoints. JSON exports provide scenario history for a prototype; they are not a durable audit service. The Dockerfile describes an API container but a container build has not been verified on this machine.

A private-data pilot would require authenticated roles, TLS, durable storage, retention policy, operational monitoring, and reviewed integration. The shipped public-sample demo does not claim these production controls or any Accenture certification.
