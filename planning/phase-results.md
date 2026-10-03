# Results by phase

Release evidence: 3 October 2026. All supplier data and fulfillment outcomes are synthetic. Tests below were actually executed locally, against a running HTTP server, and through a real browser. GitHub Actions badges are supplementary and are not used as the completion gate.

| Phase | Delivered result | Validation / status |
| --- | --- | --- |
| 1: business decision | Procurement brief, KPI definitions, manual reference fixture and repository | Outage reference produces 15/20 controllers at JPY 200; complete |
| 2: data and SQL | Seeded 20-supplier, eight-component, three-SKU, 30-order case; normalized SQLite analysis and input validation | Broken IDs, negative values, duplicate records and malformed BOM are rejected; complete |
| 3: disruptions and baselines | Dependency graph; outage, capacity and delay transformations; existing and greedy sourcing | Independent material/capacity/budget/assembly checks; immutable inputs; complete |
| 4: optimization | Two-stage CP-SAT; status reporting; verified fallback; purchase allocations | Tiny exhaustive fixtures, shared-capacity adversarial tests and solver-fallback test pass; complete |
| 5: user workflow | Streamlit interface, public browser decision lab, presets, comparison, network, report and scenario exports | Streamlit tests cover default, zero budget, no disruption and advanced workflow; complete |
| 6: evaluation | 41 Python/UI tests, 24 scenarios / 72 policy plans, 25 browser/Python parity cases and 23 real HTTP checks | Latest recorded executions all pass; all 72 plans feasible; complete |
| 7: deployment/package | Public GitHub repository and Pages demo, README, screenshot, case study, walkthrough and reproducibility commands | Public deployment verification is recorded separately in `test-results/public-browser.json`; Pages replaces the planned Community Cloud host for the sample browser demo |
| 8: CV/interview package | Evidence-based CV bullets, 90-second pitch, question bank and two-mock protocol | Preparation materials ready; your actual rehearsal remains a personal task |
| 9: uncertainty | Fixed-purchase capacity/delay/demand experiments, two seeds / 100 sampled outcomes, five budget sensitivity points | Seeded reproducibility and no-future-information checks pass; worst outcomes are retained; complete for synthetic experiments |
| 10: daily/service extension | Daily material conservation, individual deadlines, daily/total assembly limits, versioned API and scenario exports | Early-deadline, inventory and corrupted-schedule tests pass; actual HTTP endpoints pass; Docker build and durable authenticated audit service remain unverified/unimplemented |
| 11: client validation | Pilot proposal, stakeholder tasks, blank consent/feedback log and adoption process | External review, user study and real operational pilot remain pending; not claimed complete |

The full [phase plan](phase-plan.md) retains each phase's schedule, deliverables, exit criteria and placement preparation. The [preparation pack](placement-preparation.md) adds concrete exercises and final interview materials.

## Measured evidence

- `test-results/unit.xml`: 41 tests, zero failures/errors/skips; latest suite duration 4.823 seconds.
- `test-results/benchmark-summary.json` and `benchmarks.csv`: 24 declared scenarios, three policies each, 72 independently feasible plans; all 24 optimized cases proven OPTIMAL. Largest recorded policy solve time was approximately 0.0133 seconds on this machine. Timing is not a service guarantee.
- `test-results/browser-parity.json`: 25 cases matching Python priority objective and procurement cost, with feasible browser allocations.
- `test-results/live-http.json`: 23 genuine HTTP checks against a separately running Uvicorn server; includes adverse input rejection, stress and daily endpoints.
- `test-results/advanced.json`: two fixed-policy stress evaluations (seeds 41 and 97), five budget points and a valid daily reference plan. Worst observed fill was approximately 21.4% under the declared adverse capacity/delay/demand assumptions; these are not calibrated real-world risk probabilities.
- `docs/test-results.json`: consolidated evidence for public inspection.

## Default outage interpretation

For the generated S01-outage sample, existing sourcing fulfills 41/149 units (27.5%), while greedy and optimization both fulfill 138/149 (92.6%) at JPY 119,420 in purchases. Optimization ties greedy here. The 65.1 percentage-point difference is a synthetic comparison with restricted existing sourcing, not an optimizer-versus-greedy improvement or realized business benefit.

## Resolved issues and remaining limits

During implementation, UI tests initially referenced the wrong app path. After adding the advanced view, index-based selectors targeted the new controls rather than the sidebar; stable widget keys corrected the harness and the full suite was rerun. Malformed nested BOM rows and empty cases were hardened to produce a clear validation error. No unresolved test failure is hidden in the latest results.

The live public demo runs bounded enumeration of the built-in fixture; it does not host the Python API. Advanced CP-SAT, SQL, daily and stress functionality runs in the Python app/API. Real ERP integration, authenticated private-data hosting, durable multi-user history, external stakeholder review and actual savings measurement are outside the verified release. Docker configuration is provided but not labeled as a tested container build.
