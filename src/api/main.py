"""
FastAPI app: accept patient features, run the multi-agent pipeline, return JSON.

Run (from repo root):
  uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()

from src.patient_payload import patient_dict_from_flat_body

log = logging.getLogger(__name__)

app = FastAPI(
    title="PCOSense API",
    description="REST API for the PCOSense multi-agent assessment pipeline.",
    version="0.1.0",
)

_cors = os.getenv("CORS_ORIGINS", "*").strip()
_origins = [o.strip() for o in _cors.split(",") if o.strip()] or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_orch_with_db: Any = None
_orch_no_db: Any = None


def _get_orchestrator(*, use_supabase: bool) -> Any:
    """Lazy singleton — two variants so ``persist: false`` skips writes."""
    global _orch_with_db, _orch_no_db
    try:
        from src.agents import PCOSOrchestrator
    except ImportError as exc:
        log.warning("PCOSOrchestrator unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=(
                "PCOSOrchestrator not importable. Use the PCOSense repo with Phase 2 "
                "``src/agents.py`` (and ML/RAG deps), not the Zena-only agents module."
            ),
        ) from exc

    if use_supabase:
        if _orch_with_db is None:
            from src.database import SupabaseClient

            db = SupabaseClient()
            _orch_with_db = PCOSOrchestrator(db=db if db.is_configured() else None)
        return _orch_with_db

    if _orch_no_db is None:
        _orch_no_db = PCOSOrchestrator(db=None)
    return _orch_no_db


class AssessRequest(BaseModel):
    """Either use friendly fields or send a full ``patient_data`` object."""

    model_config = ConfigDict(extra="allow")

    persist: bool = Field(
        default=True,
        description="If true and Supabase is configured, persist patient + prediction.",
    )
    patient_data: dict[str, Any] | None = Field(
        default=None,
        description="Optional full feature dict (42 keys). Merged over mapped friendly fields.",
    )
    age: float | None = None
    bmi: float | None = None
    cycle_ri: int | None = Field(default=None, description="1=regular, 2=irregular")
    cycle_length_days: float | None = None
    lh: float | None = None
    fsh: float | None = None
    tsh: float | None = None
    hair_growth: int | None = Field(default=None, description="0 or 1")
    skin_darkening: int | None = None
    pimples: int | None = None
    weight_gain: int | None = None
    follicle_l: int | None = None
    follicle_r: int | None = None


def _request_to_patient_and_persist(req: AssessRequest) -> tuple[dict[str, Any], bool]:
    flat = req.model_dump(exclude_none=True)
    flat.pop("patient_data", None)
    persist = bool(flat.pop("persist", True))
    patient, persist2 = patient_dict_from_flat_body(flat)
    if req.patient_data:
        merged = dict(req.patient_data)
        merged.update(patient)
        patient = merged
    return patient, persist


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        from src.agents import PCOSOrchestrator  # noqa: F401

        orchestrator_ok = True
    except ImportError:
        orchestrator_ok = False
    try:
        from src.database import SupabaseClient

        supabase_configured = SupabaseClient().is_configured()
    except Exception:
        supabase_configured = False
    return {
        "status": "ok",
        "orchestrator_importable": orchestrator_ok,
        "supabase_configured": supabase_configured,
    }


@app.post("/api/v1/assess")
def assess(req: AssessRequest) -> dict[str, Any]:
    patient, persist = _request_to_patient_and_persist(req)
    if not patient:
        raise HTTPException(status_code=422, detail="No patient fields provided.")

    orch = _get_orchestrator(use_supabase=persist)
    result = orch.run(patient)
    return result


@app.post("/api/v1/assess/raw")
def assess_raw(body: dict[str, Any]) -> dict[str, Any]:
    """Accept a flat JSON object (e.g. from scripts); same key mapping as Shiny."""
    patient, persist = patient_dict_from_flat_body(dict(body))
    if not patient:
        raise HTTPException(status_code=422, detail="No patient fields provided.")
    orch = _get_orchestrator(use_supabase=persist)
    return orch.run(patient)
