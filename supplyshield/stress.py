"""Evaluate a fixed, preselected policy under declared uncertainty assumptions."""
import random
from copy import deepcopy

from .engine import Scenario, apply_scenario, greedy, metrics


def stress_fixed_plan(source, scenario, plan, samples=50, seed=41):
    if not 1 <= samples <= 500:
        raise ValueError("Stress sample count must be 1..500")
    rng = random.Random(seed)
    committed = sum(o["cost"] * plan["purchases"].get(o["id"], 0) for o in source["offers"])
    outcomes = []
    for i in range(samples):
        severity = rng.choice([0, 50, 100])
        delay = rng.choice([0, 3, 8])
        demand_percent = rng.choice([80, 100, 120])
        sampled = apply_scenario(source, Scenario(supplier=scenario.supplier, kind="capacity",
                                                  capacity_percent=severity, budget=scenario.budget,
                                                  assembly_capacity=scenario.assembly_capacity))
        pools = {(o["supplier"], o["component"]): o["capacity"] for o in sampled["offers"]}
        received, missing = 0, 0
        inventory = dict(source["stock"])
        for offer in sampled["offers"]:
            requested = plan["purchases"].get(offer["id"], 0)
            late = offer["lead_days"] + (delay if offer["supplier"] == scenario.supplier else 0)
            pool = (offer["supplier"], offer["component"])
            delivered = min(requested, pools[pool]) if offer["approved"] and late + source["assembly_reserve"] <= source["horizon"] else 0
            pools[pool] -= delivered
            inventory[offer["component"]] += delivered
            received += delivered
            missing += requested - delivered
        realized = deepcopy(sampled)
        realized.update({"stock": inventory, "offers": [], "planned": {}, "budget": 0})
        for order in realized["orders"]:
            order["quantity"] = max(1, (order["quantity"] * demand_percent + 99) // 100)
        allocation = greedy(realized)
        m = metrics(realized, allocation)
        outcomes.append({"sample": i + 1, "capacity_percent": severity, "additional_delay": delay,
                         "demand_percent": demand_percent,
                         "fulfilled": m["fulfilled"], "fill_rate": m["fill_rate"], "score": m["score"],
                         "committed_purchase_cost": committed, "received_units": received,
                         "late_or_unavailable_units": missing})
    rates = sorted(o["fill_rate"] for o in outcomes if o["fill_rate"] is not None)
    return {"seed": seed, "samples": samples, "policy": plan["policy"], "fixed_purchases": plan["purchases"],
            "assumptions": "Independent uniform choices: 0/50/100% capacity, 0/3/8 days extra delay, 80/100/120% demand (rounded up per order). These are assumptions, not estimated probabilities.",
            "mean_fill_rate": sum(rates) / len(rates) if rates else None,
            "worst_fill_rate": min(rates) if rates else None,
            "p10_fill_rate": rates[int((len(rates)-1)*.1)] if rates else None,
            "outcomes": outcomes, "perfect_information": False}
