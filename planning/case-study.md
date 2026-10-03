# SupplyShield: a reviewable recovery decision

**Client situation.** A fictional small electronics assembler serving Japanese customers faces a primary chip-supplier outage. Procurement must protect priority orders while respecting qualified supply, arrival deadlines, budget and assembly limits. The sample has 20 suppliers, eight components, three SKUs and 30 orders; no real manufacturer data is used.

**Current decision.** Continue the planned sourcing policy with reduced availability. This intentionally restricted baseline makes the existing sourcing assumption explicit. It is not presented as the universal behavior of a real procurement team.

**Proposed workflow.** Select a disruption; trace potentially affected parts and SKUs; compare existing sourcing, greedy recovery and constrained optimization; independently check the allocations; review shortfalls, status and costs; export the inputs and recommendation for human approval. No purchase is executed.

**Observed synthetic result.** In the default chip outage, existing sourcing fulfills 41/149 units (27.5%). Both recovery policies fulfill 138/149 (92.6%) using JPY 119,420 in purchases. The optimizer ties greedy in this case. The comparison improves service against restricted existing sourcing by 65.1 percentage points, while requiring additional modeled procurement. No profit or realized savings is inferred.

**Implementation evidence.** 24 declared scenarios produce 72 feasible policy plans; the Python/UI suite passes 41 tests; 23 checks exercise a live HTTP server; 25 fixtures match browser and CP-SAT objectives/costs. A hand case independently verifies 15 controllers from 30 chips at JPY 200 alternative procurement. Daily tests prevent future arrivals from satisfying early orders. Fixed-purchase stress runs preserve adverse outcomes and state their probability assumptions.

**Adoption considerations.** Supplier qualification, usable stock, lead-time definitions, component substitution and priority ownership would need business review. A private-data service would require access controls, durable versioned history and integration review. Begin with permitted sample-user feedback, then read-only shadow planning against an agreed baseline.

**Business validation.** Measure decision-review time, feasibility, service and spend in a disclosed pilot. Distinguish synthetic outcomes, measured usability and operational results. External user review and actual savings are pending; see the [pilot protocol](pilot-proposal.md).
