"""One verified orchestration path shared by the UI, API, and evaluation."""
from . import __version__
from .engine import Scenario, apply_scenario, feasibility, greedy, impact, metrics
from .optimizer import optimize
from .reports import input_hash, report
from copy import deepcopy


def run(case, scenario=None, seconds=5):
    transformed = apply_scenario(case, scenario or Scenario())
    plans = [greedy(transformed, existing=True), greedy(transformed), optimize(transformed, seconds)]
    if plans[-1]["status"] not in ("OPTIMAL", "FEASIBLE"):
        solver_result = plans[-1]
        fallback = deepcopy(max(plans[:2], key=lambda p: metrics(transformed, p)["score"]))
        fallback.update({"policy": "Verified baseline fallback", "status": "FALLBACK",
                         "priority_status": solver_result["priority_status"],
                         "cost_status": "NOT_RUN", "lexicographic_optimal": False,
                         "score_bound": solver_result["score_bound"], "seconds": solver_result["seconds"]})
        plans[-1] = fallback
    return {"case": transformed, "plans": plans, "metrics": [metrics(transformed, p) for p in plans],
            "model_version": __version__, "solver_limit_seconds": seconds,
            "checks": [feasibility(transformed, p) for p in plans],
            "impact": impact(case, (scenario or Scenario()).supplier),
            "input_hash": input_hash(transformed), "report": report(transformed, plans)}
