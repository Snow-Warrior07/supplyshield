"""Exercise an actual running HTTP server. Never replaces this with TestClient."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8765")
parser.add_argument("--out", default="test-results/live-http.json")
args = parser.parse_args()
checks = []


def record(name, function):
    start = perf_counter()
    try:
        function()
        checks.append({"name": name, "passed": True, "seconds": perf_counter() - start})
    except Exception as error:
        checks.append({"name": name, "passed": False, "error": str(error), "seconds": perf_counter() - start})


with httpx.Client(base_url=args.url, timeout=20, trust_env=False) as client:
    def health():
        response = client.get("/health")
        response.raise_for_status()
        assert response.json()["status"] == "ok"
    record("GET /health", health)
    reference = client.get("/sample?reference=true").json()

    def reference_test():
        response = client.post("/simulate", json={"case": reference, "scenario": {"supplier": "S1", "kind": "outage"}})
        response.raise_for_status()
        result = response.json()
        assert result["metrics"][-1]["fulfilled"] == 15
        assert result["metrics"][-1]["cost"] == 200
        assert all(c["valid"] for c in result["checks"])
    record("POST reference outage: 15/20, JPY 200", reference_test)
    for kind in ["none", "outage", "capacity", "delay"]:
        for budget in [0, 20000, 500000]:
            def scenario_test(k=kind, b=budget):
                response = client.post("/simulate", json={"scenario": {"supplier": "S01", "kind": k, "budget": b}})
                response.raise_for_status()
                result = response.json()
                assert all(c["valid"] for c in result["checks"])
                assert all(m["cost"] <= b for m in result["metrics"])
            record(f"POST {kind}, budget {budget}", scenario_test)
    for payload, name in [({"scenario": {"budget": -1}}, "Negative budget rejected"),
                          ({"scenario": {"kind": "unknown"}}, "Unknown disruption rejected"),
                          ({"seconds": 100}, "Unbounded solver time rejected"),
                          ({"scenario": {"supplier": "unknown"}}, "Unknown supplier rejected")]:
        def invalid_test(p=payload):
            assert client.post("/simulate", json=p).status_code == 422
        record(name, invalid_test)
    def stress_test():
        response = client.post("/stress", json={"case": reference, "scenario": {"supplier": "S1", "kind": "none"}})
        response.raise_for_status()
        assert response.json()["samples"] == 50
        assert not response.json()["perfect_information"]
    record("POST fixed-policy stress: 50 outcomes", stress_test)
    def daily_test():
        sample = json.loads(json.dumps(reference))
        sample["stock"]["chip"] = 0
        sample["orders"][0]["due_day"] = 2
        response = client.post("/daily", json={"case": sample, "scenario": {"supplier": "S1", "kind": "none"}})
        response.raise_for_status()
        assert response.json()["plan"]["fulfilled"]["O1"] == 0
        assert response.json()["check"]["valid"]
    record("POST daily: future arrivals cannot fulfill early deadline", daily_test)
    def malformed_bom():
        sample = json.loads(json.dumps(reference))
        sample["bom"] = [None]
        assert client.post("/simulate", json={"case": sample, "scenario": {"supplier": "S1"}}).status_code == 422
    record("Malformed nested BOM rejected", malformed_bom)
    def empty_case():
        assert client.post("/simulate", json={"case": {}}).status_code == 422
    record("Empty case rejected instead of replacing it with sample", empty_case)
    def versioned_api():
        response = client.post("/v1/simulate", json={"scenario": {"kind": "none"}})
        response.raise_for_status()
        result = response.json()
        assert result["model_version"] == "0.1.0" and len(result["input_hash"]) == 64
    record("Versioned API exposes model version and input hash", versioned_api)
summary = {"tested_at_utc": datetime.now(timezone.utc).isoformat(), "server": args.url,
           "passed": sum(c["passed"] for c in checks), "total": len(checks), "checks": checks,
           "test_type": "Real HTTP requests to a separately running server"}
Path(args.out).parent.mkdir(parents=True, exist_ok=True)
Path(args.out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
raise SystemExit(0 if all(c["passed"] for c in checks) else 1)
