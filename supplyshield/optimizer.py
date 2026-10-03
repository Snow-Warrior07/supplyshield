"""Lexicographic priority fulfillment / purchase cost with honest solver statuses."""
from collections import defaultdict
from time import perf_counter

from ortools.sat.python import cp_model

from .engine import empty_plan, feasibility, requirements


def optimize(case, seconds=5):
    if not 0 < seconds <= 30:
        raise ValueError("Solver time limit must be between 0 and 30 seconds")
    start = perf_counter()
    model = cp_model.CpModel()
    buys = {o["id"]: model.new_int_var(0, o["capacity"] if o["eligible"] else 0, o["id"])
            for o in case["offers"]}
    fulfill = {o["id"]: model.new_int_var(0, o["quantity"], o["id"]) for o in case["orders"]}
    pools = defaultdict(list)
    for o in case["offers"]:
        pools[(o["supplier"], o["component"])].append(o)
    for group in pools.values():
        model.add(sum(buys[o["id"]] for o in group) <= group[0]["capacity"])
    req = requirements(case)
    for component in case["components"]:
        cid = component["id"]
        consumption = sum(req[o["product"]].get(cid, 0) * fulfill[o["id"]] for o in case["orders"])
        arrivals = sum(buys[o["id"]] for o in case["offers"] if o["component"] == cid)
        model.add(consumption <= case["stock"][cid] + arrivals)
    minutes = {p["id"]: p["assembly_minutes"] for p in case["products"]}
    model.add(sum(minutes[o["product"]] * fulfill[o["id"]] for o in case["orders"])
              <= case["assembly_limit"])
    cost = sum(o["cost"] * buys[o["id"]] for o in case["offers"])
    model.add(cost <= case["budget"])
    score = sum(o["priority"] * fulfill[o["id"]] for o in case["orders"])
    model.maximize(score)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds / 2
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 7
    first = solver.solve(model)
    plan = empty_plan(case, "Optimized recovery", solver.status_name(first))
    plan.update({"priority_status": solver.status_name(first), "cost_status": "NOT_RUN",
                 "score_bound": solver.best_objective_bound, "lexicographic_optimal": False})
    if first not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        plan["seconds"] = perf_counter() - start
        return plan

    def extract():
        return ({k: solver.value(v) for k, v in buys.items()},
                {k: solver.value(v) for k, v in fulfill.items()})

    plan["purchases"], plan["fulfilled"] = extract()
    if first == cp_model.OPTIMAL:
        best = solver.value(score) if case["orders"] else 0
        model.add(score == best)
        model.minimize(cost)
        second = solver.solve(model)
        plan["cost_status"] = solver.status_name(second)
        if second in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            plan["purchases"], plan["fulfilled"] = extract()
            plan["lexicographic_optimal"] = second == cp_model.OPTIMAL
        plan["status"] = "OPTIMAL" if plan["lexicographic_optimal"] else "FEASIBLE"
    plan["seconds"] = perf_counter() - start
    check = feasibility(case, plan)
    if not check["valid"]:
        raise RuntimeError("Solver failed independent verification: " + str(check["errors"]))
    return plan
