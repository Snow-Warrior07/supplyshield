"""Day-indexed conservation with per-order deadlines and daily assembly limits."""
from collections import defaultdict
from copy import deepcopy
from time import perf_counter

from ortools.sat.python import cp_model

from .engine import Scenario, apply_scenario, empty_plan, requirements
from .validation import integer, validate_case


def daily_scenario(source, scenario):
    common = deepcopy(source)
    for o in source["orders"]:
        integer(o.get("due_day"), "due_day", 1, source["horizon"])
    for o in common["orders"]:
        o["due_day"] = common["horizon"]
    validate_case(common)
    transformed = apply_scenario(common, scenario)
    transformed["orders"] = deepcopy(source["orders"])
    return transformed


def check_daily(case, plan, daily_minutes):
    errors, used_daily, used_material = [], defaultdict(int), defaultdict(lambda: defaultdict(int))
    fulfilled, cost, pool_units = defaultdict(int), 0, defaultdict(int)
    offers = {o["id"]: o for o in case["offers"]}
    orders = {o["id"]: o for o in case["orders"]}
    req = requirements(case)
    minutes = {p["id"]: p["assembly_minutes"] for p in case["products"]}
    arrivals = defaultdict(lambda: defaultdict(int))
    for oid, n in plan["purchases"].items():
        if oid not in offers or type(n) is not int or n < 0:
            errors.append("Invalid purchase")
            continue
        o = offers[oid]
        if n and not o["eligible"]:
            errors.append("Ineligible purchase")
        cost += n * o["cost"]
        pool_units[(o["supplier"], o["component"])] += n
        arrivals[max(1, o["lead_days"])][o["component"]] += n
    for o in case["offers"]:
        if pool_units[(o["supplier"], o["component"])] > o["capacity"]:
            errors.append("Shared capacity exceeded")
    for row in plan["schedule"]:
        o = orders.get(row["order"])
        d, n = row["production_day"], row["quantity"]
        if o is None or type(d) is not int or not 1 <= d <= case["horizon"] or type(n) is not int or n < 0:
            errors.append("Invalid schedule")
            continue
        if d + case["assembly_reserve"] > o["due_day"]:
            errors.append("Order deadline missed")
        fulfilled[o["id"]] += n
        used_daily[d] += n * minutes[o["product"]]
        for c, units in req[o["product"]].items():
            used_material[d][c] += n * units
    inventory, history = dict(case["stock"]), []
    for d in range(1, case["horizon"] + 1):
        if used_daily[d] > daily_minutes:
            errors.append("Daily assembly exceeded")
        for component in inventory:
            inventory[component] += arrivals[d][component] - used_material[d][component]
            if inventory[component] < 0:
                errors.append("Future arrival used early")
        history.append({"day": d, "inventory": dict(inventory), "assembly_minutes": used_daily[d]})
    for o in case["orders"]:
        if fulfilled[o["id"]] > o["quantity"] or fulfilled[o["id"]] != plan["fulfilled"].get(o["id"], 0):
            errors.append("Order allocation mismatch")
    if cost > case["budget"]:
        errors.append("Budget exceeded")
    return {"valid": not errors, "errors": sorted(set(errors)), "inventory_history": history, "cost": cost}


def optimize_daily(source, scenario=None, daily_minutes=500, seconds=5):
    integer(daily_minutes, "daily_minutes", 0, 100000)
    if not 0 < seconds <= 10:
        raise ValueError("Daily solve time must be 0..10 seconds")
    c = daily_scenario(source, scenario or Scenario())
    start = perf_counter()
    model = cp_model.CpModel()
    x = {o["id"]: model.new_int_var(0, o["capacity"] if o["eligible"] else 0, "purchase_" + o["id"])
         for o in c["offers"]}
    production = {(o["id"], d): model.new_int_var(0, o["quantity"], f"produce_{o['id']}_{d}")
                  for o in c["orders"] for d in range(1, o["due_day"] - c["assembly_reserve"] + 1)}
    for o in c["orders"]:
        model.add(sum(v for (oid, _), v in production.items() if oid == o["id"]) <= o["quantity"])
    pools = defaultdict(list)
    for o in c["offers"]:
        pools[(o["supplier"], o["component"])].append(o)
    for group in pools.values():
        model.add(sum(x[o["id"]] for o in group) <= group[0]["capacity"])
    req = requirements(c)
    order_map = {o["id"]: o for o in c["orders"]}
    minutes = {p["id"]: p["assembly_minutes"] for p in c["products"]}
    for d in range(1, c["horizon"] + 1):
        model.add(sum(minutes[order_map[oid]["product"]] * v for (oid, day), v in production.items() if day == d) <= daily_minutes)
        for component in c["components"]:
            cid = component["id"]
            consumed = sum(req[order_map[oid]["product"]].get(cid, 0) * v
                           for (oid, day), v in production.items() if day <= d)
            arrived = sum(x[o["id"]] for o in c["offers"]
                          if o["component"] == cid and max(1, o["lead_days"]) <= d)
            model.add(consumed <= c["stock"][cid] + arrived)
    model.add(sum(minutes[order_map[oid]["product"]] * v for (oid, _), v in production.items()) <= c["assembly_limit"])
    cost = sum(o["cost"] * x[o["id"]] for o in c["offers"])
    model.add(cost <= c["budget"])
    score = sum(order_map[oid]["priority"] * v for (oid, _), v in production.items())
    model.maximize(score)
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.max_time_in_seconds = seconds / 2
    status = solver.solve(model)
    plan = empty_plan(c, "Daily optimized recovery", solver.status_name(status))
    plan.update({"schedule": [], "daily_minutes": daily_minutes})

    def extract():
        plan["purchases"] = {k: solver.value(v) for k, v in x.items()}
        plan["schedule"] = [{"order": oid, "product": order_map[oid]["product"], "production_day": d,
                             "delivery_day": d + c["assembly_reserve"], "quantity": solver.value(v)}
                            for (oid, d), v in production.items() if solver.value(v)]
        plan["fulfilled"] = {o["id"]: sum(r["quantity"] for r in plan["schedule"] if r["order"] == o["id"])
                             for o in c["orders"]}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        extract()
        if status == cp_model.OPTIMAL:
            model.add(score == solver.value(score))
            model.minimize(cost)
            second = solver.solve(model)
            if second in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                extract()
            plan["status"] = "OPTIMAL" if second == cp_model.OPTIMAL else "FEASIBLE"
    plan["seconds"] = perf_counter() - start
    checked = check_daily(c, plan, daily_minutes)
    if not checked["valid"]:
        raise RuntimeError(str(checked["errors"]))
    return {"case": c, "plan": plan, "check": checked}
