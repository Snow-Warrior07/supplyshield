# Client brief

A fictional small electronics assembler serving customers in Japan needs to review qualified sourcing alternatives when a supplier is unavailable, late, or operating below capacity. The procurement manager must choose purchases and priority orders within component, budget, delivery, and assembly limits.

The prototype supports a human decision. It does not execute purchases, qualify real suppliers, predict supplier failures, or represent actual client data. The included seven-day case has 20 fictional suppliers, eight components, three SKUs, and 30 orders. Currency is JPY in whole yen. Location is a label, not a risk estimate.

The current-process comparator is restricted to the case's planned sourcing. Greedy recovery can use qualified timely alternatives. The optimizer first maximizes priority-weighted fulfillment and then minimizes purchase cost where optimality is proven. All three share the same inputs and independent checks. A tie is a valid outcome.

The manual correctness fixture demands 20 controllers, each requiring two chips and one housing. Opening stock contains 20 chips and 20 housings. After the primary supplier outage, ten timely alternative chips at JPY 20 each allow 15 controllers. Expected fill: 75%; purchase cost: JPY 200. This fixture verifies conservation rather than commercial value.

Success means an inspectable comparison, feasible quantities, accurate status, reproducible evidence, and a useful export. Real operational value must be measured separately against an agreed pilot baseline.
