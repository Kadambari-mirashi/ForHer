"""
Supabase PostgreSQL client for PCOSense — patients, predictions, audit log.

Run the SQL in the project README (or PCOSense repo) in the Supabase SQL Editor.
"""

from __future__ import annotations

import logging
import os
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)


class SupabaseClient:
    """Wrapper for Supabase. Set ``SUPABASE_URL`` and ``SUPABASE_KEY`` in ``.env``."""

    def __init__(self, url: str | None = None, key: str | None = None) -> None:
        self.url = url or os.getenv("SUPABASE_URL", "")
        self.key = key or os.getenv("SUPABASE_KEY", "")
        self._client: Any = None

    @property
    def client(self) -> Any:
        if self._client is None:
            if not self.url or not self.key:
                raise ValueError(
                    "Supabase credentials missing. Set SUPABASE_URL and SUPABASE_KEY in .env "
                    "(Supabase → Project → Settings → API)."
                )
            from supabase import create_client

            self._client = create_client(self.url, self.key)
            log.info("Connected to Supabase at %s", self.url)
        return self._client

    def is_configured(self) -> bool:
        return bool(self.url and self.key)

    def store_patient(self, data: dict[str, Any]) -> str:
        patient_id = str(uuid4())
        symptoms = {
            k: data.get(k)
            for k in [
                "Weight gain(Y/N)",
                "hair growth(Y/N)",
                "Skin darkening (Y/N)",
                "Hair loss(Y/N)",
                "Pimples(Y/N)",
                "Fast food (Y/N)",
                "Reg.Exercise(Y/N)",
            ]
            if data.get(k) is not None
        }
        hormones = {
            k: data.get(k)
            for k in [
                "LH(mIU/mL)",
                "FSH(mIU/mL)",
                "TSH (mIU/L)",
                "PRL(ng/mL)",
                "Vit D3 (ng/mL)",
                "PRG(ng/mL)",
                "AMH(ng/mL)",
            ]
            if data.get(k) is not None
        }
        row = {
            "id": patient_id,
            "age": data.get(" Age (yrs)") or data.get("age"),
            "bmi": data.get("BMI") or data.get("bmi"),
            "blood_group": str(data.get("Blood Group", "")),
            "cycle_regular": data.get("Cycle(R/I)") == 1
            if data.get("Cycle(R/I)") is not None
            else None,
            "symptoms": symptoms,
            "hormones": hormones,
            "raw_input": data,
        }
        self.client.table("patients").insert(row).execute()
        self.audit_log(patient_id, "patient_created")
        log.info("Stored patient %s", patient_id)
        return patient_id

    def store_prediction(
        self,
        patient_id: str,
        risk_score: float,
        risk_label: str,
        confidence: float | None = None,
        top_factors: list[dict] | None = None,
        clinical_summary: str = "",
        recommendation: str = "",
        agent_outputs: dict | None = None,
    ) -> str:
        prediction_id = str(uuid4())
        row = {
            "id": prediction_id,
            "patient_id": patient_id,
            "risk_score": risk_score,
            "risk_label": risk_label,
            "confidence": confidence,
            "top_factors": top_factors or [],
            "clinical_summary": clinical_summary,
            "recommendation": recommendation,
            "model_version": "xgboost-v1",
            "agent_outputs": agent_outputs or {},
        }
        self.client.table("predictions").insert(row).execute()
        self.audit_log(patient_id, "prediction_created", {"prediction_id": prediction_id})
        log.info("Stored prediction %s for patient %s", prediction_id, patient_id)
        return prediction_id

    def audit_log(
        self, patient_id: str, event: str, details: dict[str, Any] | None = None
    ) -> None:
        row = {
            "id": str(uuid4()),
            "patient_id": patient_id,
            "event": event,
            "details": details or {},
        }
        try:
            self.client.table("audit_log").insert(row).execute()
        except Exception as exc:
            log.warning("Audit-log write failed: %s", exc)

    def get_patient(self, patient_id: str) -> dict[str, Any] | None:
        resp = self.client.table("patients").select("*").eq("id", patient_id).execute()
        rows = resp.data
        return rows[0] if rows else None

    def get_predictions(self, patient_id: str) -> list[dict[str, Any]]:
        resp = (
            self.client.table("predictions")
            .select("*")
            .eq("patient_id", patient_id)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data

    def get_audit_trail(self, patient_id: str) -> list[dict[str, Any]]:
        resp = (
            self.client.table("audit_log")
            .select("*")
            .eq("patient_id", patient_id)
            .order("created_at")
            .execute()
        )
        return resp.data
