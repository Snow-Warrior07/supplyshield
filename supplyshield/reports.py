"""Portable, reproducible reports with spreadsheet-safe text exports."""
import csv
import hashlib
import io
import json

from .engine import metrics


def input_hash(case):
    return hashlib.sha256(json.dumps(case, sort_keys=True).encode()).hexdigest()


def csv_text(rows):
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        writer.writerow({k: "'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r"))
                         else v for k, v in row.items()})
    return output.getvalue()


def report(case, plans):
    results = [metrics(case, p) for p in plans]
    chosen = results[-1]
    lines = ["# SupplyShield recovery recommendation", "", "Synthetic planning experiment; no actual business savings claimed.",
             "", f"Input SHA-256: `{input_hash(case)}`", f"Currency: {case['currency']} ({case['money_unit']})",
             f"Scenario: `{json.dumps(case['scenario'], sort_keys=True)}`", "",
             "| Policy | Fulfilled / demand | Purchase cost | Unfulfilled | Status |",
             "| --- | --- | --- | --- | --- |"]
    for m in results:
        lines.append(f"| {m['policy']} | {m['fulfilled']} / {m['demand']} | {m['cost']} | {m['unfulfilled']} | {m['status']} |")
    lines += ["", f"Recommended policy: {chosen['policy']}. It fulfills {chosen['fulfilled']} units "
              f"with {chosen['cost']} {case['currency']} of purchases under the declared constraints.",
              "", "Review every allocation before acting. Unknown supplier qualification, changing lead times, "
              "and incomplete data can invalidate a plan. Gross sales exposure is not profit or realized loss.",
              "", "## Recommended purchases", ""]
    offers = {o["id"]: o for o in case["offers"]}
    for oid, n in plans[-1]["purchases"].items():
        if n:
            o = offers[oid]
            lines.append(f"- {n} × {o['component']} from {o['supplier']} ({o['mode']}, {o['lead_days']} days).")
    lines += ["", "## Assumptions", "", "- Common due horizon; opening stock is usable.",
              "- Declared assembly/delivery reserve and total assembly capacity apply.",
              "- Purchases occur at the start and normal/expedited offers share physical capacity.",
              "- Partial fulfillment is permitted. Recommendations do not execute purchases."]
    return "\n".join(lines) + "\n"
