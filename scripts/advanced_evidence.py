"Publish repeatable extension results, without claims of estimated probabilities."
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from supplyshield.data import generate_case, reference_case
from supplyshield.engine import Scenario
from supplyshield.service import run
from supplyshield.stress import stress_fixed_plan
from supplyshield.daily import optimize_daily

root = Path(__file__).resolve().parents[1]
case = generate_case()
scenario = Scenario(kind="none")
selected = run(case, scenario)
stress = [stress_fixed_plan(case, scenario, selected["plans"][-1], seed=seed) for seed in [41, 97]]
curve = []
for budget in [0, 20000, 50000, 100000, case["default_budget"]]:
    result = run(case, Scenario(budget=budget))
    curve.append({"budget": budget, "metrics": result["metrics"], "checks": result["checks"]})
daily = optimize_daily(reference_case(), Scenario(supplier="S1", kind="outage"), daily_minutes=3)
evidence = {"tested_at_utc": datetime.now(timezone.utc).isoformat(),
            "stress_selection": "Plan chosen before samples using the undisturbed sample; fixed purchases throughout.",
            "stress": stress, "budget_sensitivity": curve, "daily_reference": daily,
            "external_user_validation": "Not performed; pilot protocol is provided.",
            "synthetic": True}
root.joinpath("test-results/advanced.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
print(json.dumps({"stress_samples": sum(s["samples"] for s in stress),
                  "stress_seeds": [s["seed"] for s in stress],
                  "worst_fill": [s["worst_fill_rate"] for s in stress],
                  "budget_points": len(curve), "daily_fulfilled": daily["plan"]["fulfilled"],
                  "daily_valid": daily["check"]["valid"]}, indent=2))
