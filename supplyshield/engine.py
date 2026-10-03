"""Disruption, baselines, independent conservation checks, and metrics."""
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass
from time import perf_counter

import networkx as nx

from .validation import integer, validate_case


@dataclass(frozen=True)
class Scenario:
    supplier: str = "S01"
    kind: str = "outage"
    capacity_percent: int = 50
    delay_days: int = 8
    budget: int | None = None
    assembly_capacity: int | None = None


def requirements(case):
    result = {p["id"]: {} for p in case["products"]}
    for b in case["bom"]:
        result[b["product"]][b["component"]] = b["units"]
    return result


def apply_scenario(case, scenario):
    validate_case(case)
    if scenario.kind not in ("none", "outage", "capacity", "delay"):
        raise ValueError("Unknown disruption kind")
    if scenario.supplier not in {s["id"] for s in case["suppliers"]} and scenario.kind != "none":
        raise ValueError("Unknown supplier")
    integer(scenario.capacity_percent, "capacity_percent", 0, 100)
    integer(scenario.delay_days, "delay_days", 0, 365)
    result = deepcopy(case)
    result["budget"] = scenario.budget if scenario.budget is not None else case["default_budget"]
    result["assembly_limit"] = (scenario.assembly_capacity if scenario.assembly_capacity is not None
                                else case["assembly_capacity"])
    integer(result["budget"], "budget", 0, 1000000000)
    integer(result["assembly_limit"], "assembly limit")
    for offer in result["offers"]:
        if offer["supplier"] == scenario.supplier:
            if scenario.kind == "outage":
                offer["capacity"] = 0
            elif scenario.kind == "capacity":
                offer["capacity"] = offer["capacity"] * scenario.capacity_percent // 100
            elif scenario.kind == "delay":
                offer["lead_days"] += scenario.delay_days
        offer["eligible"] = offer["approved"] and offer["lead_days"] + case["assembly_reserve"] <= case["horizon"]
    result["scenario"] = asdict(scenario)
    return result


def dependency_graph(case):
    graph = nx.DiGraph()
    for table, prefix in [("suppliers", "supplier"), ("components", "component"), ("products", "product")]:
        for row in case[table]:
            graph.add_node(f"{prefix}:{row['id']}", kind=prefix, label=row["name"])
    for o in case["offers"]:
        graph.add_edge(f"supplier:{o['supplier']}", f"component:{o['component']}")
    for b in case["bom"]:
        graph.add_edge(f"component:{b['component']}", f"product:{b['product']}", units=b["units"])
    return graph


def impact(case, supplier):
    graph = dependency_graph(case)
    node = "supplier:" + supplier
    affected = nx.descendants(graph, node) if node in graph else set()
    return {"components": sorted(n.split(":", 1)[1] for n in affected if n.startswith("component:")),
            "products": sorted(n.split(":", 1)[1] for n in affected if n.startswith("product:"))}


def empty_plan(case, policy, status="FEASIBLE"):
    return {"policy": policy, "purchases": {o["id"]: 0 for o in case["offers"]},
            "fulfilled": {o["id"]: 0 for o in case["orders"]}, "status": status, "seconds": 0}


def greedy(case, existing=False):
    start = perf_counter()
    plan = empty_plan(case, "Existing sourcing" if existing else "Greedy recovery")
    req = requirements(case)
    offers = sorted(case["offers"], key=lambda o: (o["cost"], o["id"]))
    pools = {(o["supplier"], o["component"]): o["capacity"] for o in offers}
    inventory = dict(case["stock"])
    budget, assembly = case["budget"], case["assembly_limit"]
    minutes = {p["id"]: p["assembly_minutes"] for p in case["products"]}
    for order in sorted(case["orders"], key=lambda o: (-o["priority"], o["id"])):
        for _ in range(order["quantity"]):
            if assembly < minutes[order["product"]]:
                break
            trial_stock, trial_pools = dict(inventory), dict(pools)
            trial_buys, spent = dict(plan["purchases"]), 0
            possible = True
            for component, units in req[order["product"]].items():
                need = max(0, units - trial_stock[component])
                for offer in offers:
                    if not need:
                        break
                    if offer["component"] != component or not offer["eligible"]:
                        continue
                    pool = (offer["supplier"], component)
                    allowed = trial_pools[pool]
                    if existing:
                        allowed = min(allowed, max(0, case["planned"].get(offer["id"], 0)
                                                  - trial_buys[offer["id"]]))
                    affordable = need if offer["cost"] == 0 else max(0, (budget - spent) // offer["cost"])
                    count = min(need, allowed, affordable)
                    trial_buys[offer["id"]] += count
                    trial_pools[pool] -= count
                    trial_stock[component] += count
                    spent += count * offer["cost"]
                    need -= count
                if need:
                    possible = False
                    break
                trial_stock[component] -= units
            if not possible:
                break
            inventory, pools = trial_stock, trial_pools
            plan["purchases"] = trial_buys
            budget -= spent
            assembly -= minutes[order["product"]]
            plan["fulfilled"][order["id"]] += 1
    plan["seconds"] = perf_counter() - start
    return plan


def feasibility(case, plan):
    """Recompute conservation independently of the allocation algorithm."""
    errors, pools, purchased = [], defaultdict(int), defaultdict(int)
    cost = 0
    known_offers = {o["id"] for o in case["offers"]}
    known_orders = {o["id"] for o in case["orders"]}
    if set(plan.get("purchases", {})) - known_offers or set(plan.get("fulfilled", {})) - known_orders:
        errors.append("Unknown allocation ID")
    for o in case["offers"]:
        n = plan.get("purchases", {}).get(o["id"], 0)
        if type(n) is not int or n < 0:
            errors.append(f"Invalid purchase {o['id']}")
            continue
        if n and not o["eligible"]:
            errors.append(f"Ineligible purchase {o['id']}")
        pools[(o["supplier"], o["component"])] += n
        purchased[o["component"]] += n
        cost += n * o["cost"]
    for o in case["offers"]:
        if pools[(o["supplier"], o["component"])] > o["capacity"]:
            errors.append(f"Shared capacity exceeded {o['supplier']}/{o['component']}")
    used, assembly = defaultdict(int), 0
    req = requirements(case)
    minutes = {p["id"]: p["assembly_minutes"] for p in case["products"]}
    for o in case["orders"]:
        n = plan.get("fulfilled", {}).get(o["id"], 0)
        if type(n) is not int or not 0 <= n <= o["quantity"]:
            errors.append(f"Invalid fulfillment {o['id']}")
            continue
        assembly += n * minutes[o["product"]]
        for c, units in req[o["product"]].items():
            used[c] += n * units
    for c, n in used.items():
        if n > case["stock"][c] + purchased[c]:
            errors.append(f"Material shortage {c}")
    if cost > case["budget"]:
        errors.append("Budget exceeded")
    if assembly > case["assembly_limit"]:
        errors.append("Assembly capacity exceeded")
    return {"valid": not errors, "errors": sorted(set(errors)), "cost": cost,
            "assembly_used": assembly, "consumed": dict(used), "purchased": dict(purchased)}


def metrics(case, plan):
    check = feasibility(case, plan)
    if not check["valid"]:
        raise ValueError("Invalid plan: " + "; ".join(check["errors"]))
    fulfilled = sum(plan["fulfilled"].values())
    total = sum(o["quantity"] for o in case["orders"])
    score = sum(o["priority"] * plan["fulfilled"].get(o["id"], 0) for o in case["orders"])
    max_score = sum(o["priority"] * o["quantity"] for o in case["orders"])
    exposure = sum(o["price"] * (o["quantity"] - plan["fulfilled"].get(o["id"], 0)) for o in case["orders"])
    return {"policy": plan["policy"], "fulfilled": fulfilled, "demand": total,
            "fill_rate": fulfilled / total if total else None,
            "weighted_fill_rate": score / max_score if max_score else None, "score": score,
            "unfulfilled": total - fulfilled, "cost": check["cost"], "sales_exposure": exposure,
            "status": plan["status"], "seconds": plan["seconds"], "feasible": True}
