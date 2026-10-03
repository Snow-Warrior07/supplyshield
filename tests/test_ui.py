from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_streamlit_default_and_zero_budget():
    app = AppTest.from_file(APP, default_timeout=20).run()
    assert not app.exception
    assert len(app.metric) == 4
    app.number_input(key="budget").set_value(0)
    app.button(key="compare").click().run()
    assert not app.exception
    assert app.metric[2].value == "¥0"
    assert app.session_state["result"]["metrics"][-1]["cost"] == 0


def test_streamlit_no_disruption():
    app = AppTest.from_file(APP, default_timeout=20).run()
    app.selectbox[1].select("none")
    app.button(key="compare").click().run()
    assert not app.exception
    assert app.metric[0].value == "100.0%"


def test_streamlit_advanced_experiments():
    app = AppTest.from_file(APP, default_timeout=20).run()
    app.button(key="advanced").click().run()
    assert not app.exception
    results = app.session_state["advanced_results"]
    assert results["stress"]["samples"] == 50
    assert results["daily"]["check"]["valid"]
    assert len(results["budget_sensitivity"]) == 5
