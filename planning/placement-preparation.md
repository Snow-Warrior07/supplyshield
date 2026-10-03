# Placement preparation alongside each phase

These are recommended exercises based on the supplied Digital Consultant JD, not a confirmed technical-test syllabus. The JD identifies resume screening, an online technical test, and approximately two Manager/Director interviews. Follow the actual invitation if it supplies a different format.

Use about two hours daily: 45 minutes Python, 30 minutes SQL/fundamentals, 30 minutes business/project explanation, and 15 minutes mistake review. Add 15 minutes of Japanese practice. Phase exercises replace these blocks rather than adding hours. Revisit mistakes within two days.

| Phase | Preparation at the end | Concrete output |
| --- | --- | --- |
| 1: problem | Self-introduction; Why Digital Consulting, Accenture and Japan; lists/dicts/sets and complexity | 60-second introduction; three hash-map exercises; kana/greetings |
| 2: data/SQL | Joins, GROUP BY/HAVING, CTEs, windows, normalization, keys and indexes | Explain the schema; write a demand query that avoids duplicate joins |
| 3: graph/scenarios | BFS/DFS, adjacency lists, sorting and greedy; supplier-failure consulting case | Dependency-impact coding exercise; teamwork STAR answer |
| 4: optimization | Variables/constraints/objectives, feasibility versus optimality, prediction versus decisions | Draw the model; defend greedy, CP-SAT and timeout handling; timed sliding-window exercise |
| 5: interface | HTTP, APIs, client/server architecture, SQL storage and caching | Two-minute business demo; five-minute engineering explanation; disagreement STAR |
| 6: evaluation | Leakage, splits, precision/recall, calibration and imbalance; synthetic evidence limits | Timed coding and SQL mocks; failure/debugging STAR |
| 7: deployment | Compute/storage, identity/access, logging, availability and cost | Architecture from memory; 30-minute project mock; two interviewer questions |
| 8: freeze/CV | Technical mock and motivation/client-case mock; cross-cultural teamwork | 90-second pitch; defend every CV number; protect sleep |
| 9: uncertainty | Expected value, quantiles, Monte Carlo, calibration, robust decisions | Explain why correct optimization can fail with wrong inputs; advanced SQL/graph exercise |
| 10: service/daily | REST, transactions, idempotency, concurrency, authentication/authorization | Explain how ERP integration avoids duplicated orders; technical-decision STAR |
| 11: pilot | Stakeholder interviews, prioritization, change management and ROI assumptions | Five-minute client presentation; skeptical-manager questions; use actual feedback when obtained |

## Honest CV bullets

- Built SupplyShield, a Python/SQL supplier-disruption planner with 20 synthetic suppliers, eight components and three product SKUs; published a live interactive decision lab and independent feasibility checks.
- Evaluated three sourcing policies across 24 synthetic scenarios (72 verified plans), with 41 Python/UI tests, 23 live HTTP checks and 25 browser/Python parity cases; added fixed-purchase stress tests and daily inventory conservation.

Only retain these counts if you can reproduce the release evidence. The public demo's engine uses bounded enumeration; the Python engine uses CP-SAT. Explain both accurately. Do not claim live customer savings, real supplier prediction, or Accenture certification.

## 90-second project pitch

“I built SupplyShield to help a procurement manager decide what to buy when a supplier fails. The sample is deliberately synthetic: 20 suppliers, eight parts, three products and 30 orders. I compare existing sourcing, a deterministic greedy recovery policy, and constrained optimization under the same stock, capacity, deadline and budget limits. I independently verify every recommendation rather than trusting the solver alone. The public demo makes the tradeoff visible, while the Python service adds daily inventory and fixed-policy uncertainty tests. In the default outage, greedy and optimization both fulfill 138 of 149 units; that tie is useful evidence, and I do not present it as an optimizer improvement. My next validation step is a permitted procurement-user walkthrough and a shadow pilot.”

## Questions to rehearse

Why this business problem? Which assumptions change the decision? Why optimization rather than a prediction model? When does greedy fail? Why can weighted fulfillment and unit fill disagree? How is shared capacity prevented from double counting? What does UNKNOWN mean? Why are simulated results different from business savings? How would you integrate client data and measure value?

## Mock and mistake log

No candidate mock interview has been performed by the software. Complete two 30-minute rehearsals before the drive. Record question, initial approach, mistake, corrected explanation and revisit date. Add one example each for initiative, teamwork, disagreement, failure, and learning. Japanese-learning commitment and cross-cultural examples should reflect your actual experience.
