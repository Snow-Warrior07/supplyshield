"""Reproducible synthetic data; no real supplier records or inferred geography risks."""
import json
import random
from pathlib import Path


def generate_case(seed=7):
    rng = random.Random(seed)
    suppliers = [{"id": f"S{i:02}", "name": f"Sample supplier {i:02}",
                  "location": ["Tokyo", "Osaka", "Nagoya", "Sendai"][i % 4]} for i in range(1, 21)]
    components = [{"id": f"C{i}", "name": name} for i, name in enumerate(
        ["MCU", "Power IC", "Housing", "Sensor", "PCB", "Connector", "Display", "Seal"], 1)]
    products = [{"id": "P1", "name": "Standard controller", "assembly_minutes": 8},
                {"id": "P2", "name": "Sensor module", "assembly_minutes": 10},
                {"id": "P3", "name": "Pro controller", "assembly_minutes": 12}]
    requirements = {"P1": {"C1": 2, "C2": 1, "C3": 1, "C5": 1},
                    "P2": {"C1": 1, "C4": 2, "C5": 1, "C6": 1},
                    "P3": {"C1": 2, "C2": 1, "C3": 1, "C5": 1, "C7": 1, "C8": 1}}
    bom = [{"product": p, "component": c, "units": n} for p, cs in requirements.items()
           for c, n in cs.items()]
    orders = [{"id": f"O{i:02}", "product": products[(i - 1) % 3]["id"],
               "quantity": rng.randint(3, 8), "priority": [1, 2, 4][i % 3],
               "price": [12000, 15000, 22000][(i - 1) % 3], "due_day": 7} for i in range(1, 31)]
    demand = {c["id"]: sum(o["quantity"] * requirements[o["product"]].get(c["id"], 0)
                           for o in orders) for c in components}
    stock = {c: max(1, n // 6) for c, n in demand.items()}
    offers, planned = [], {}
    for i, c in enumerate(components, 1):
        cid = c["id"]
        required = demand[cid] - stock[cid]
        cap = demand[cid] + 10
        primary = f"S{i:02}"
        offers.append({"id": f"F{i}N", "supplier": primary, "component": cid, "mode": "normal",
                       "capacity": cap, "lead_days": 2, "cost": 100 + i * 20, "approved": True})
        offers.append({"id": f"F{i}E", "supplier": primary, "component": cid, "mode": "expedited",
                       "capacity": cap, "lead_days": 1, "cost": 150 + i * 25, "approved": True})
        planned[f"F{i}N"] = required
        if i != 8:  # C8 is intentionally sole-source for the reference exercise.
            offers.append({"id": f"A{i}", "supplier": f"S{i+8:02}", "component": cid,
                           "mode": "normal", "capacity": max(1, demand[cid] * 3 // 4),
                           "lead_days": 4, "cost": 160 + i * 30, "approved": True})
    for i in range(17, 21):
        offers.append({"id": f"L{i}", "supplier": f"S{i:02}", "component": "C1", "mode": "normal",
                       "capacity": 100, "lead_days": 10, "cost": 50, "approved": True})
    base_cost = sum(planned.get(o["id"], 0) * o["cost"] for o in offers)
    return {"name": "Synthetic Japan electronics assembler", "seed": seed, "synthetic": True,
            "currency": "JPY", "money_unit": "whole yen", "horizon": 7, "assembly_reserve": 1,
            "default_budget": base_cost * 2, "assembly_capacity": 10000,
            "suppliers": suppliers, "components": components, "products": products,
            "bom": bom, "stock": stock, "offers": offers, "orders": orders, "planned": planned}


def reference_case():
    return {"name": "Hand-calculated controller case", "synthetic": True, "currency": "JPY",
            "money_unit": "whole yen", "horizon": 7, "assembly_reserve": 1,
            "default_budget": 1000, "assembly_capacity": 100,
            "suppliers": [{"id": "S1", "name": "Main", "location": "Sample"},
                          {"id": "S2", "name": "Alternative", "location": "Sample"}],
            "components": [{"id": "chip", "name": "Chip"}, {"id": "housing", "name": "Housing"}],
            "products": [{"id": "controller", "name": "Controller", "assembly_minutes": 1}],
            "bom": [{"product": "controller", "component": "chip", "units": 2},
                    {"product": "controller", "component": "housing", "units": 1}],
            "stock": {"chip": 20, "housing": 20},
            "offers": [{"id": "main", "supplier": "S1", "component": "chip", "mode": "normal",
                        "capacity": 20, "lead_days": 2, "cost": 10, "approved": True},
                       {"id": "alt", "supplier": "S2", "component": "chip", "mode": "normal",
                        "capacity": 10, "lead_days": 3, "cost": 20, "approved": True}],
            "orders": [{"id": "O1", "product": "controller", "quantity": 20, "priority": 1,
                        "price": 100, "due_day": 7}], "planned": {"main": 20}}


def save_case(path, case=None):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(case or generate_case(), indent=2) + "\n", encoding="utf-8")
