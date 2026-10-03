"""SupplyShield: reviewable procurement decisions with reproducible evidence."""
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from supplyshield.data import generate_case
from supplyshield.database import analyze
from supplyshield.engine import Scenario, dependency_graph
from supplyshield.reports import csv_text
from supplyshield.service import run
from supplyshield.stress import stress_fixed_plan
from supplyshield.daily import optimize_daily

st.set_page_config(page_title="SupplyShield", page_icon="◈", layout="wide")
st.markdown("""<style>.block-container{padding-top:2rem;max-width:1400px}
    [data-testid='stMetric']{border:1px solid #dce4ea;padding:18px;border-radius:10px}
    h1{letter-spacing:-1.5px}</style>""", unsafe_allow_html=True)
st.caption("SUPPLYSHIELD / PROCUREMENT DECISION LAB")
st.title("A disruption is a decision.")
st.write("See the exposure. Compare feasible recovery plans. Protect priority orders within your budget.")
st.info("Synthetic electronics supply chain • JPY, whole yen • All results are simulated • Human review required")
case = generate_case()
with st.sidebar:
    st.header("Build a scenario")
    supplier = st.selectbox("Affected supplier", [s["id"] for s in case["suppliers"]])
    kind = st.selectbox("Disruption", ["outage", "capacity", "delay", "none"])
    percent = st.slider("Remaining capacity (%)", 0, 100, 50)
    delay = st.slider("Additional delay (days)", 0, 14, 8)
    budget = st.number_input("Procurement budget (JPY)", min_value=0, max_value=1000000000,
                             value=case["default_budget"], step=1000, key="budget")
    assembly = st.number_input("Available assembly minutes", min_value=0, max_value=10000000,
                               value=case["assembly_capacity"], step=100)
    clicked = st.button("Compare recovery plans", type="primary", width="stretch", key="compare")
    st.caption("One plant · 20 suppliers · 8 components · 3 SKUs · 30 orders")
if clicked or "result" not in st.session_state:
    st.session_state.pop("advanced_results", None)
    with st.spinner("Solving and independently checking each plan…"):
        st.session_state.result = run(case, Scenario(supplier, kind, percent, delay, budget, assembly))
result = st.session_state.result
st.caption("Displayed scenario: " + json.dumps(result["case"]["scenario"]))
best = result["metrics"][-1]
cols = st.columns(4)
for col, label, value in zip(cols, ["On-time unit fill", "Priority fulfillment", "Recovery purchases", "Unfulfilled units"],
                              [f"{best['fill_rate']:.1%}" if best['fill_rate'] is not None else "N/A",
                               f"{best['weighted_fill_rate']:.1%}" if best['weighted_fill_rate'] is not None else "N/A",
                               f"¥{best['cost']:,}", best["unfulfilled"]]):
    col.metric(label, value)
network, comparison, recommendation, evidence, advanced = st.tabs(["Supply network", "Policy comparison", "Recommendation", "Evidence", "Advanced planning"])
with network:
    graph = dependency_graph(case)
    affected = {"supplier:" + result["case"]["scenario"]["supplier"]}
    affected |= {"component:" + c for c in result["impact"]["components"]}
    affected |= {"product:" + p for p in result["impact"]["products"]}
    positions = {}
    for level, kind_name in enumerate(["supplier", "component", "product"]):
        nodes = [n for n, d in graph.nodes(data=True) if d["kind"] == kind_name]
        for i, n in enumerate(nodes):
            positions[n] = (level, 1 - (i + .5) / len(nodes))
    edges_x, edges_y = [], []
    for a, b in graph.edges:
        edges_x.extend([positions[a][0], positions[b][0], None])
        edges_y.extend([positions[a][1], positions[b][1], None])
    fig = go.Figure(go.Scatter(x=edges_x, y=edges_y, mode="lines", line={"color": "#dce4ea", "width": 1}, hoverinfo="skip"))
    nodes = list(graph.nodes)
    fig.add_trace(go.Scatter(x=[positions[n][0] for n in nodes], y=[positions[n][1] for n in nodes],
                            mode="markers+text", text=[n.split(":")[1] for n in nodes], textposition="middle right",
                            hovertext=[graph.nodes[n]["label"] for n in nodes], hoverinfo="text",
                            marker={"size": 13, "color": ["#d87143" if n in affected else "#16786c" for n in nodes]}))
    fig.update_layout(height=530, showlegend=False, xaxis={"visible": False}, yaxis={"visible": False},
                      margin={"l": 20, "r": 30, "t": 20, "b": 20})
    st.plotly_chart(fig, width="stretch")
    st.caption("Reachability shows potential exposure. The material model determines actual shortages.")
    st.dataframe(pd.DataFrame(analyze(case)), hide_index=True, width="stretch")
with comparison:
    st.dataframe(pd.DataFrame(result["metrics"]), hide_index=True, width="stretch")
    st.bar_chart(pd.DataFrame(result["metrics"]).set_index("policy")[["fulfilled", "unfulfilled"]])
    if all(check["valid"] for check in result["checks"]):
        st.success("All three policies passed independent material, shared capacity, budget, and assembly checks.")
    else:
        st.error("A policy failed verification. Review the evidence before using this result.")
with recommendation:
    st.markdown(result["report"])
    purchases = [{"offer": oid, "units": qty} for oid, qty in result["plans"][-1]["purchases"].items() if qty]
    st.download_button("Download purchase recommendation", csv_text(purchases), "recommendation.csv", "text/csv")
    st.download_button("Download management report", result["report"], "recovery-report.md", "text/markdown")
with evidence:
    st.write("Input SHA-256", result["input_hash"])
    st.json(result["checks"])
    st.download_button("Download full scenario and results", json.dumps(result, indent=2), "scenario.json", "application/json")
    st.caption("Capacity and lead times are assumed, not predicted. Sales exposure is not realized loss. "
               "The static planner uses a common due date and a declared assembly/delivery reserve.")
with advanced:
    st.subheader("Test the decision under uncertainty")
    st.write("Keep today's purchases fixed and evaluate 50 seeded capacity, delay, and demand outcomes. "
             "Then inspect a daily production plan and the service purchased at different budgets.")
    daily_minutes = st.number_input("Daily assembly minutes", min_value=0, max_value=100000, value=500, step=50)
    if st.button("Run advanced experiments", key="advanced"):
        scenario = Scenario(**result["case"]["scenario"])
        with st.spinner("Evaluating fixed purchases, budget sensitivity, and daily inventory…"):
            stress = stress_fixed_plan(case, scenario, result["plans"][-1])
            daily = optimize_daily(case, scenario, daily_minutes=daily_minutes)
            curve = []
            for amount in [0, case["default_budget"] // 4, case["default_budget"] // 2,
                           case["default_budget"], case["default_budget"] * 2]:
                inputs = {**result["case"]["scenario"], "budget": amount}
                measured = run(case, Scenario(**inputs))["metrics"][-1]
                curve.append({"budget": amount, "fill_rate": measured["fill_rate"], "cost": measured["cost"]})
            st.session_state.advanced_results = {"stress": stress, "daily": daily, "budget_sensitivity": curve}
    if "advanced_results" in st.session_state:
        experiments = st.session_state.advanced_results
        stress = experiments["stress"]
        st.caption(stress["assumptions"])
        st.metric("Worst observed unit fill", f"{stress['worst_fill_rate']:.1%}")
        st.line_chart(pd.DataFrame(stress["outcomes"]).set_index("sample")[["fill_rate"]])
        st.line_chart(pd.DataFrame(experiments["budget_sensitivity"]).set_index("budget")[["fill_rate"]])
        st.write("Daily production schedule")
        st.dataframe(pd.DataFrame(experiments["daily"]["plan"]["schedule"]), hide_index=True)
        st.json(experiments["daily"]["check"])
        st.download_button("Download advanced evidence", json.dumps(experiments, indent=2), "advanced-evidence.json")
