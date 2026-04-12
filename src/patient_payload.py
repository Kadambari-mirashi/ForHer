"""
Map user-facing / JSON form fields to Kaggle PCOS model feature names (PCOSense).
Missing values are omitted so the ML pipeline can impute.
"""

from __future__ import annotations

from typing import Any

# Friendly API / Shiny keys → exact keys expected by DataValidatorAgent & PCOSPredictor
FORM_TO_MODEL: dict[str, str] = {
    "age": " Age (yrs)",
    "bmi": "BMI",
    "cycle_ri": "Cycle(R/I)",
    "cycle_length_days": "Cycle length(days)",
    "lh": "LH(mIU/mL)",
    "fsh": "FSH(mIU/mL)",
    "tsh": "TSH (mIU/L)",
    "hair_growth": "hair growth(Y/N)",
    "skin_darkening": "Skin darkening (Y/N)",
    "pimples": "Pimples(Y/N)",
    "weight_gain": "Weight gain(Y/N)",
    "follicle_l": "Follicle No. (L)",
    "follicle_r": "Follicle No. (R)",
    # Optional extended fields (leave blank in API / omit from JSON to impute)
    "weight_kg": "Weight (Kg)",
    "height_cm": "Height(Cm) ",
    "pulse_bpm": "Pulse rate(bpm) ",
    "hb": "Hb(g/dl)",
    "rbs": "RBS(mg/dl)",
    "prl": "PRL(ng/mL)",
    "vit_d3": "Vit D3 (ng/mL)",
    "endometrium_mm": "Endometrium (mm)",
    "avg_follicle_l_mm": "Avg. F size (L) (mm)",
    "avg_follicle_r_mm": "Avg. F size (R) (mm)",
}


def patient_dict_from_flat_body(body: dict[str, Any]) -> dict[str, Any]:
    """
    Build *patient_data* for ``PCOSOrchestrator.run``.

    - Pops and returns ``persist`` if present (bool).
    - Maps friendly keys via ``FORM_TO_MODEL``.
    - Passes through any other keys unchanged (full 42-feature payloads).
    """
    data = {k: v for k, v in body.items() if v is not None}
    persist = bool(data.pop("persist", False))

    patient: dict[str, Any] = {}
    for friendly, model_key in FORM_TO_MODEL.items():
        if friendly in data:
            patient[model_key] = data.pop(friendly)

    for k, v in data.items():
        patient[k] = v

    return patient, persist
