# Interactive website release

Released on 4 October 2026. [Public website](https://snow-warrior07.github.io/supplyshield/) · [Recorded website checks](../docs/website-test-results.json)

SupplyShield now presents the project as a complete, responsive website. A live recovery snapshot, four-step tour, case explanation, source evidence, and FAQ introduce the procurement decision. The decision lab provides six scenario presets, automatic updates, and six views of the resulting plan.

## Interactive workflow

1. Choose a supplier outage, sole-source failure, delivery delay, reduced capacity, tight budget, or no disruption.
2. Adjust the supplier, budget, assembly time, and sample demand. Background workers keep the controls responsive while optimization runs. Changing inputs cancels obsolete work and disables exports until the new plan is checked.
3. Compare existing sourcing, greedy recovery, and optimized recovery. Selecting a policy updates order fulfillment, purchases, material balances, and feasibility evidence.
4. Inspect a supplier, component, or SKU in the network. Search customer orders and filter by shortfall.
5. Run six independent budget comparisons and 50 seeded futures with the selected policy's purchase quantities fixed. Apply a measured budget point to the scenario.
6. Save sample inputs on the device, reproduce them through a shared URL, or download orders, purchases, a full scenario, experiment evidence, and a management report.

## Verification

- 10/10 Node model tests passed: fixture agreement, demand conservation, feasible allocation, zero budget, shared inputs, input bounds, reproducible fixed-policy stress, no new procurement in stress outcomes, budget points, and CSV escaping.
- 30/30 local browser checks passed, covering all six presets, automatic/manual runs, policy selection, order filtering/search, network inspection, saving/restoring, shared URL loading, demand scaling, rapid changes, budget experiments, live checks, tour completion, and keyboard interaction.
- 5/5 downloaded-file checks passed. The actual JSON/CSV/Markdown downloads contain the displayed quantities and costs. Experiment evidence contains six budget points and 50 fixed-purchase outcomes.
- Mobile tested at a 390 × 844 viewport: landing page and network had no document-level horizontal overflow, and a preset recomputed successfully. Tables and tabs intentionally scroll within their own containers.
- The website's six built-in correctness checks passed in the browser.

Evidence is recorded in `test-results/website-unit.json`, `website-browser.json`, and `website-exports.json`, and combined in `docs/website-test-results.json`. Mobile screenshots accompany the browser evidence. These are executed checks, not a claim of a complete accessibility audit or production certification.

## Sample outcomes

| Scenario | Optimized units fulfilled | Demand |
| --- | ---: | ---: |
| Main supplier outage | 138 | 149 |
| No disruption | 149 | 149 |
| Sole-source seal outage | 105 | 149 |
| Main supplier at 50% capacity | 149 | 149 |
| Main supplier delayed by eight days | 138 | 149 |
| Budget squeeze, JPY 29,870 | 53 | 149 |
| Zero budget | 24 | 149 |

The default outage uses JPY 119,420 in modeled purchases. Greedy and optimized recovery tie in priority score and cost; the interface states that tie explicitly.

## Scope and assumptions

All records and outcomes are synthetic. The browser supports the included three-SKU model, a common seven-day horizon, and one day reserved for assembly/delivery. The search has a five-second limit; a completed search can prove OPTIMAL, while a time-limited result is FEASIBLE. Higher-demand cases may reach that limit.

The budget curve uses separate optimized reruns and displays each point's status. Stress outcomes assume independent uniform supplier capacity, extra delay, and demand variations; the assumptions are stated beside the chart. Purchases remain fixed and no new sourcing occurs after observing a future. These results do not estimate actual supplier failure probabilities.

The public website runs entirely on static GitHub Pages. Python daily planning, FastAPI, and CP-SAT remain available in the repository and run separately. Local storage saves only seven synthetic settings; shared URLs carry those settings. No purchase is executed and no private ERP data is loaded.

The linked two-minute walkthrough shows the earlier release. The current website and screenshots show the redesigned interface.
