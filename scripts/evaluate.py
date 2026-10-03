"""Generate declared scenario benchmarks and cross-engine expectations."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from supplyshield.data import generate_case, reference_case, save_case
from supplyshield.engine import Scenario
from supplyshield.reports import csv_text
from supplyshield.service import run

root = Path(__file__).resolve().parents[1]
case = generate_case()
save_case(root / "data/sample/case.json", case)
save_case(root / "docs/sample.json", case)
save_case(root / "docs/reference.json", reference_case())
rows, parity = [], []
for supplier in ["S01", "S08"]:
    for kind in ["none", "outage", "capacity", "delay"]:
        for budget in [0, case["default_budget"] // 4, case["default_budget"]]:
            scenario = Scenario(supplier=supplier, kind=kind, budget=budget)
            result = run(case, scenario)
            for m in result["metrics"]:
                rows.append({"scenario_supplier": supplier, "kind": kind, "budget": budget, **m})
            parity.append({"scenario": result["case"]["scenario"], "expected": result["metrics"]})
root.joinpath("test-results").mkdir(exist_ok=True)
root.joinpath("test-results/benchmarks.csv").write_text(csv_text(rows), encoding="utf-8")
root.joinpath("test-results/parity.json").write_text(json.dumps(parity, indent=2), encoding="utf-8")
summary = {"tested_at_utc": datetime.now(timezone.utc).isoformat(), "scenarios": len(parity),
           "policy_runs": len(rows), "valid_plans": sum(m["feasible"] for m in rows),
           "optimized_optimal": sum(m["status"] == "OPTIMAL" for m in rows if m["policy"] == "Optimized recovery"),
           "max_solve_seconds": max(m["seconds"] for m in rows), "synthetic": True,
           "note": "Actual solver timings; modeled fulfillment is not realized business savings."}
root.joinpath("test-results/benchmark-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
