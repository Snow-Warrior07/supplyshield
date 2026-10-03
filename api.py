"""Local/live API for genuine HTTP tests and future ERP integration."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from supplyshield import __version__
from supplyshield.data import generate_case, reference_case
from supplyshield.engine import Scenario
from supplyshield.service import run
from supplyshield.daily import optimize_daily
from supplyshield.stress import stress_fixed_plan

app = FastAPI(title="SupplyShield", version=__version__)


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    supplier: str = "S01"
    kind: str = "outage"
    capacity_percent: int = Field(default=50, ge=0, le=100)
    delay_days: int = Field(default=8, ge=0, le=365)
    budget: int | None = Field(default=None, ge=0, le=1000000000)
    assembly_capacity: int | None = Field(default=None, ge=0, le=10000000)


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case: dict | None = None
    scenario: ScenarioRequest = Field(default_factory=ScenarioRequest)
    seconds: float = Field(default=5, gt=0, le=10)


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__, "synthetic_demo": True}


@app.get("/sample")
def sample(reference: bool = False):
    return reference_case() if reference else generate_case()


@app.post("/simulate")
@app.post("/v1/simulate")
def simulate(request: Request):
    try:
        return run(request.case if request.case is not None else generate_case(), Scenario(**request.scenario.model_dump()), request.seconds)
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/stress")
@app.post("/v1/stress")
def stress(request: Request):
    try:
        case = request.case if request.case is not None else generate_case()
        scenario = Scenario(**request.scenario.model_dump())
        result = run(case, scenario, request.seconds)
        return stress_fixed_plan(case, scenario, result["plans"][-1])
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/daily")
@app.post("/v1/daily")
def daily(request: Request, daily_minutes: int = 500):
    try:
        return optimize_daily(request.case if request.case is not None else generate_case(), Scenario(**request.scenario.model_dump()),
                              daily_minutes=daily_minutes, seconds=request.seconds)
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
