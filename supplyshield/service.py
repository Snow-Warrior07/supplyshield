"""One verified orchestration path shared by the UI, API, and evaluation."""
from .engine import Scenario, apply_scenario, feasibility, greedy, impact, metrics
from .optimizer import optimize
from .reports import input_hash, report


def run(case, scenario=None, seconds=5):
    transformed = apply_scenario(case, scenario or Scenario())
    plans = [greedy(transformed, existing=True), greedy(transformed), optimize(transformed, seconds)]
    return {"case": transformed, "plans": plans, "metrics": [metrics(transformed, p) for p in plans],
            "checks": [feasibility(transformed, p) for p in plans],
            "impact": impact(case, (scenario or Scenario()).supplier),
            "input_hash": input_hash(transformed), "report": report(transformed, plans)}
