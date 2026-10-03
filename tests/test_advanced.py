from supplyshield.daily import check_daily, optimize_daily
from supplyshield.data import reference_case
from supplyshield.engine import Scenario
from supplyshield.service import run
from supplyshield.stress import stress_fixed_plan
from supplyshield.engine import empty_plan
import supplyshield.service as service


def test_stress_fixed_plan_reproducible_without_future_information():
    case = reference_case()
    scenario = Scenario(supplier="S1", kind="none")
    plan = run(case, scenario)["plans"][-1]
    one = stress_fixed_plan(case, scenario, plan, samples=30)
    two = stress_fixed_plan(case, scenario, plan, samples=30)
    assert one == two
    assert not one["perfect_information"]
    assert one["fixed_purchases"] == plan["purchases"]
    assert one["worst_fill_rate"] <= one["mean_fill_rate"]
    assert len({o["committed_purchase_cost"] for o in one["outcomes"]}) == 1


def test_daily_cannot_use_future_arrivals_for_early_order():
    case = reference_case()
    case["stock"]["chip"] = 0
    case["orders"][0]["due_day"] = 2
    result = optimize_daily(case, Scenario(supplier="S1", kind="none"), daily_minutes=100)
    assert result["plan"]["fulfilled"]["O1"] == 0
    assert result["check"]["valid"]


def test_daily_arrivals_and_capacity_conserved():
    result = optimize_daily(reference_case(), Scenario(supplier="S1", kind="outage"), daily_minutes=3)
    assert result["plan"]["fulfilled"]["O1"] == 15
    assert all(r["assembly_minutes"] <= 3 for r in result["check"]["inventory_history"])
    assert all(n >= 0 for r in result["check"]["inventory_history"] for n in r["inventory"].values())


def test_daily_checker_detects_early_use():
    case = reference_case()
    case["stock"]["chip"] = 0
    result = optimize_daily(case, Scenario(supplier="S1", kind="none"), daily_minutes=100)
    result["plan"]["schedule"][0]["production_day"] = 1
    assert not check_daily(result["case"], result["plan"], 100)["valid"]


def test_absent_solver_incumbent_returns_verified_baseline(monkeypatch):
    def timed_out(case, seconds):
        plan = empty_plan(case, "Optimized recovery", "UNKNOWN")
        plan.update(priority_status="UNKNOWN", score_bound=20, seconds=seconds)
        return plan
    monkeypatch.setattr(service, "optimize", timed_out)
    result = service.run(reference_case(), Scenario(supplier="S1", kind="outage"))
    assert result["plans"][-1]["status"] == "FALLBACK"
    assert result["metrics"][-1]["fulfilled"] == 15
    assert all(check["valid"] for check in result["checks"])


def test_daily_checker_rejects_misreported_delivery():
    result = optimize_daily(reference_case(), Scenario(supplier="S1", kind="none"))
    result["plan"]["schedule"][0]["delivery_day"] = 1
    assert not check_daily(result["case"], result["plan"], 500)["valid"]
