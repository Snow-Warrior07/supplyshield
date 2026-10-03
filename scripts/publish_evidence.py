"""Combine measured results for the public evidence link; never invent passes."""
import json
import platform
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
results = root / "test-results"
suite = ET.parse(results / "unit.xml").getroot().find("testsuite")
unit = {key: int(suite.attrib[key]) for key in ["tests", "failures", "errors", "skipped"]}
unit["seconds"] = float(suite.attrib["time"])
data = {"published_at_utc": datetime.now(timezone.utc).isoformat(), "unit_and_ui": unit,
        "environment": {"os": platform.system(), "python": platform.python_version()},
        "synthetic": True, "business_savings_claimed": False}
for name in ["benchmark-summary", "browser-parity", "live-http"]:
    data[name] = json.loads((results / (name + ".json")).read_text(encoding="utf-8"))
browser = results / "public-browser.json"
if browser.exists():
    data["public-browser"] = json.loads(browser.read_text(encoding="utf-8"))
(root / "docs/test-results.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
print(json.dumps({"python_tests": unit, "live_http": data["live-http"]["passed"],
                  "cross_engine": data["browser-parity"]["passed"]}, indent=2))
