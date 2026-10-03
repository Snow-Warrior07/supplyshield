from copy import deepcopy
from itertools import product

import pytest

from supplyshield.data import generate_case, reference_case
from supplyshield.database import analyze
from supplyshield.engine import Scenario, apply_scenario, feasibility, greedy, impact, metrics
from supplyshield.optimizer import optimize
from supplyshield.reports import csv_text
from supplyshield.service import run
from supplyshield.validation import validate_case


def test_hand_calculated_outage():
    result = run(reference_case(), Scenario(supplier="S1", kind="outage"))
    assert [m["fulfilled"] for m in result["metrics"]] == [10, 15, 15]
    assert result["metrics"][-1]["fill_rate"] == .75
    assert result["metrics"][-1]["cost"] == 200


def test_undisturbed_sample_fully_fulfilled():
    result = run(generate_case(), Scenario(kind="none"))
    assert all(m["fill_rate"] == 1 for m in result["metrics"])


def test_scenario_does_not_mutate_source():
    case = generate_case()
    original = deepcopy(case)
    apply_scenario(case, Scenario(kind="delay"))
    assert case == original


@pytest.mark.parametrize("kind", ["none", "outage", "capacity", "delay"])
@pytest.mark.parametrize("budget", [0, 500, 1000000])
def test_all_policies_honor_conservation(kind, budget):
    result = run(generate_case(), Scenario(kind=kind, budget=budget), seconds=2)
    assert all(c["valid"] for c in result["checks"])
    if result["plans"][-1]["priority_status"] == "OPTIMAL":
        assert result["metrics"][-1]["score"] >= max(m["score"] for m in result["metrics"][:2])


def test_zero_budget_uses_stock():
    result = run(reference_case(), Scenario(supplier="S1", budget=0))
    assert result["metrics"][-1]["fulfilled"] == 10
    assert result["metrics"][-1]["cost"] == 0


def test_late_alternative_cannot_fulfill():
    case = reference_case()
    case["offers"][1]["lead_days"] = 7
    assert run(case, Scenario(supplier="S1"))["metrics"][-1]["fulfilled"] == 10


def test_missing_part_stops_assembly():
    case = reference_case()
    case["stock"]["housing"] = 0
    assert run(case, Scenario(supplier="S1"))["metrics"][-1]["fulfilled"] == 0


def test_shared_normal_expedited_capacity():
    case = reference_case()
    case["stock"]["chip"] = 0
    case["offers"] = [case["offers"][1], {**case["offers"][1], "id": "alt-fast", "mode": "expedited", "cost": 30}]
    case["planned"] = {"alt": 10}
    result = run(case, Scenario(supplier="S2", kind="none"))
    assert result["metrics"][-1]["fulfilled"] == 5
    assert sum(result["plans"][-1]["purchases"].values()) == 10


def test_independent_checker_rejects_corrupted_plan():
    case = apply_scenario(reference_case(), Scenario(supplier="S1", kind="none", budget=0))
    plan = greedy(case)
    plan["fulfilled"]["O1"] = 20
    assert not feasibility(case, plan)["valid"]


def test_assembly_limit():
    result = run(reference_case(), Scenario(supplier="S1", kind="none", assembly_capacity=3))
    assert result["metrics"][-1]["fulfilled"] == 3


def test_empty_orders_metrics():
    case = reference_case()
    case["orders"] = []
    result = run(case, Scenario(supplier="S1", kind="none"))
    assert result["metrics"][-1]["fill_rate"] is None
    assert result["metrics"][-1]["weighted_fill_rate"] is None


@pytest.mark.parametrize("change", ["duplicate", "negative", "unknown", "mixed-deadline", "float"])
def test_invalid_inputs(change):
    case = reference_case()
    if change == "duplicate":
        case["orders"].append(deepcopy(case["orders"][0]))
    elif change == "negative":
        case["stock"]["chip"] = -1
    elif change == "unknown":
        case["bom"][0]["component"] = "unknown"
    elif change == "mixed-deadline":
        case["orders"][0]["due_day"] = 3
    else:
        case["offers"][0]["cost"] = 1.5
    with pytest.raises(ValueError):
        validate_case(case)


def test_sql_demand_without_offer_join_duplication():
    rows = {r["component"]: r for r in analyze(reference_case())}
    assert rows["chip"]["demand"] == 40
    assert rows["housing"]["demand"] == 20


def test_dependency_impact():
    assert impact(reference_case(), "S1") == {"components": ["chip"], "products": ["controller"]}


def test_csv_formula_injection_escaped():
    assert "'=HYPERLINK" in csv_text([{"supplier": '=HYPERLINK("x")', "qty": 1}])


def test_tiny_optimizer_matches_exhaustive_enumeration():
    case = reference_case()
    case["stock"] = {"chip": 2, "housing": 3}
    case["offers"][0]["capacity"] = 2
    case["offers"][1]["capacity"] = 2
    case["orders"][0]["quantity"] = 3
    transformed = apply_scenario(case, Scenario(supplier="S1", kind="none", budget=40))
    candidates = []
    for main, alt, z in product(range(3), range(3), range(4)):
        plan = {"purchases": {"main": main, "alt": alt}, "fulfilled": {"O1": z}}
        check = feasibility(transformed, plan)
        if check["valid"]:
            candidates.append((z, -check["cost"]))
    chosen = optimize(transformed)
    m = metrics(transformed, chosen)
    assert (m["score"], -m["cost"]) == max(candidates)
    assert chosen["lexicographic_optimal"]


def test_input_hash_and_report_reproducible():
    one = run(reference_case(), Scenario(supplier="S1"))
    two = run(reference_case(), Scenario(supplier="S1"))
    assert one["input_hash"] == two["input_hash"]
    assert one["report"] == two["report"]
