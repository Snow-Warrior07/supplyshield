"""Validate public demo inputs before queries, graphs, or optimization."""


def integer(value, label, minimum=0, maximum=10_000_000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer between {minimum} and {maximum}")


def validate_case(case):
    if not isinstance(case, dict):
        raise ValueError("Case must be an object")
    refs = {}
    for table, limit in [("suppliers", 100), ("components", 50), ("products", 6),
                         ("offers", 500), ("orders", 500)]:
        rows = case.get(table)
        if not isinstance(rows, list) or len(rows) > limit:
            raise ValueError(f"Invalid {table} table or row limit exceeded")
        ids = [r.get("id") for r in rows if isinstance(r, dict)]
        if len(ids) != len(rows) or any(not isinstance(v, str) or not v or len(v) > 80 for v in ids):
            raise ValueError(f"Invalid IDs in {table}")
        if len(set(ids)) != len(ids):
            raise ValueError(f"Duplicate ID in {table}")
        refs[table] = set(ids)
    integer(case.get("horizon"), "horizon", 1, 365)
    integer(case.get("assembly_reserve"), "assembly_reserve", 0, case["horizon"])
    integer(case.get("default_budget"), "default_budget", 0, 1_000_000_000)
    integer(case.get("assembly_capacity"), "assembly_capacity")
    if not isinstance(case.get("stock"), dict) or set(case["stock"]) != refs["components"]:
        raise ValueError("Stock must contain exactly the known component IDs")
    for c, n in case["stock"].items():
        integer(n, f"stock {c}")
    for p in case["products"]:
        integer(p.get("assembly_minutes"), "assembly_minutes", 1, 100000)
    bom = case.get("bom")
    if not isinstance(bom, list) or len(bom) > 300:
        raise ValueError("Invalid BOM")
    seen = set()
    for b in bom:
        if not isinstance(b, dict):
            raise ValueError("BOM rows must be objects")
        if b.get("product") not in refs["products"] or b.get("component") not in refs["components"]:
            raise ValueError("Unknown BOM reference")
        key = (b["product"], b["component"])
        if key in seen:
            raise ValueError("Duplicate BOM entry")
        seen.add(key)
        integer(b.get("units"), "BOM units", 1, 10000)
    if {b["product"] for b in bom} != refs["products"]:
        raise ValueError("Every product needs a BOM")
    capacities = {}
    for o in case["offers"]:
        if o.get("supplier") not in refs["suppliers"] or o.get("component") not in refs["components"]:
            raise ValueError("Unknown offer reference")
        if o.get("mode") not in ("normal", "expedited") or type(o.get("approved")) is not bool:
            raise ValueError("Invalid offer mode/approval")
        for field in ["capacity", "lead_days", "cost"]:
            integer(o.get(field), field)
        pool = (o["supplier"], o["component"])
        if pool in capacities and capacities[pool] != o["capacity"]:
            raise ValueError("Modes must declare the same shared physical capacity")
        capacities[pool] = o["capacity"]
    for o in case["orders"]:
        if o.get("product") not in refs["products"]:
            raise ValueError("Unknown order product")
        integer(o.get("quantity"), "quantity", 1, 10000)
        integer(o.get("priority"), "priority", 1, 1000)
        integer(o.get("price"), "price", 0, 100000000)
        if o.get("due_day") != case["horizon"]:
            raise ValueError("Static planner requires a common due horizon; use daily planner for mixed dates")
    if not isinstance(case.get("planned"), dict) or not set(case["planned"]) <= refs["offers"]:
        raise ValueError("Invalid planned purchase references")
    for n in case["planned"].values():
        integer(n, "planned units")
    return case
