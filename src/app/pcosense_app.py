"""
PCOSense — Multi-Agent System for Polycystic Ovary Syndrome Detection
======================================================================
Phase 3 Shiny UI: patient form (core + optional fields), results hero, SHAP + risk
charts, clinical evidence, recommendation, downloads, agent flip-cards, teal theme.
"""

from __future__ import annotations

import html
import json
import os
from io import StringIO
from typing import Any

import httpx
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, Session, reactive, render, ui

load_dotenv()

API_BASE = os.getenv("PCOSENSE_API_URL", "http://127.0.0.1:8000").rstrip("/")
_PASSWORD = os.getenv("PCOSENSE_APP_PASSWORD", "").strip()

# ── Teal theme (PCOS awareness) ─────────────────────────────────────────────
TEAL = "#0d9488"
TEAL_DARK = "#0f766e"
TEAL_DEEP = "#115e59"
TEAL_LIGHT = "#5eead4"
TEAL_MIST = "#ccfbf1"
TEAL_BG = "#f0fdfa"

BTN_STYLE = (
    f"background:{TEAL_DARK};border-color:{TEAL_DARK};color:#fff;width:100%;"
    "margin-top:10px;font-weight:700;border-radius:10px;padding:10px;"
)

PCOS_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');
:root {{
  --teal: {TEAL};
  --teal-dark: {TEAL_DARK};
  --teal-deep: {TEAL_DEEP};
  --teal-light: {TEAL_LIGHT};
  --teal-mist: {TEAL_MIST};
  --teal-bg: {TEAL_BG};
  --text: #134e4a;
  --muted: #5f7a78;
  --card: #ffffff;
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: 'Outfit', system-ui, sans-serif !important;
  background: var(--teal-bg) !important;
  color: var(--text) !important;
  margin: 0;
}}
.pcos-header {{
  background: linear-gradient(125deg, {TEAL_DEEP} 0%, {TEAL_DARK} 42%, {TEAL} 100%);
  color: #fff;
  padding: clamp(22px, 4vw, 38px);
  text-align: center;
  box-shadow: 0 8px 32px rgba(15, 118, 110, 0.35);
}}
.pcos-header .title {{
  margin: 0;
  font-size: clamp(1.4rem, 4vw, 1.95rem);
  font-weight: 700;
  letter-spacing: -0.02em;
}}
.pcos-header .subtitle {{
  margin: 10px auto 0;
  max-width: 760px;
  opacity: 0.95;
  font-size: clamp(0.88rem, 2.1vw, 1.05rem);
  line-height: 1.55;
}}
.pcos-header .ribbon {{
  display: inline-block;
  margin-top: 14px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: {TEAL_MIST};
  border: 1px solid rgba(255,255,255,0.35);
  padding: 4px 12px;
  border-radius: 999px;
}}
.disclaimer {{
  font-size: 12px;
  color: var(--muted);
  padding: 12px 18px;
  background: #fff;
  border-left: 4px solid var(--teal);
  margin: 0 auto;
  max-width: 1080px;
  border-radius: 0 10px 10px 0;
}}
.main-wrap {{ max-width: 1080px; margin: 0 auto; padding: 16px 18px 56px; }}
.card {{
  background: var(--card);
  border-radius: 16px;
  padding: clamp(16px, 3vw, 22px);
  margin-bottom: 16px;
  box-shadow: 0 2px 20px rgba(15, 118, 110, 0.08);
  border: 1px solid rgba(13, 148, 136, 0.12);
}}
.card h4 {{ color: var(--teal-deep); margin-top: 0; font-size: 1.08rem; }}
.card h5 {{ color: var(--teal-dark); font-size: 0.92rem; margin: 14px 0 8px; }}

/* Results hero */
.hero-results {{
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 20px;
  align-items: center;
}}
@media (max-width: 720px) {{ .hero-results {{ grid-template-columns: 1fr; }} }}
.risk-ring {{
  width: min(200px, 70vw);
  height: min(200px, 70vw);
  border-radius: 50%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: conic-gradient(
    var(--teal) calc(var(--p, 0) * 1%),
    #e2e8f0 0
  );
  position: relative;
}}
.risk-ring::before {{
  content: '';
  position: absolute;
  inset: 14px;
  border-radius: 50%;
  background: #fff;
}}
.risk-ring-inner {{
  position: relative;
  z-index: 1;
  text-align: center;
}}
.risk-ring .big {{
  font-size: 2.1rem;
  font-weight: 800;
  color: var(--teal-deep);
  line-height: 1;
}}
.risk-ring .lbl {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-top: 6px; }}
.hero-label {{
  display: inline-block;
  background: var(--teal-mist);
  color: var(--teal-deep);
  font-weight: 700;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 13px;
  margin-bottom: 10px;
}}
.hero-reco {{ font-size: 14px; line-height: 1.65; color: #27635f; }}

.risk-bar-wrap {{ background: #e2e8f0; border-radius: 12px; height: 34px; overflow: hidden; margin: 14px 0; }}
.risk-bar-fill {{
  height: 100%;
  background: linear-gradient(90deg, {TEAL_LIGHT}, {TEAL_DARK});
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 12px;
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  min-width: 52px;
}}
pre.json-out {{
  font-size: 11px;
  background: #f8fafc;
  padding: 14px;
  border-radius: 10px;
  overflow-x: auto;
  border: 1px solid #e2e8f0;
}}
.flag-warn {{ color: #b45309; }}
.flag-err {{ color: #b91c1c; }}

.agent-strip {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 14px; }}
.agent-badge {{
  background: linear-gradient(135deg, {TEAL}, {TEAL_DEEP});
  color: #fff;
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.03em;
}}
.agent-arrow {{ color: var(--teal-dark); font-weight: 800; font-size: 14px; }}

.stat-row {{ display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; margin-bottom: 8px; }}
.stat-box {{
  background: linear-gradient(180deg, #fff, var(--teal-mist));
  border: 1px solid rgba(13, 148, 136, 0.25);
  border-radius: 14px;
  padding: 14px 20px;
  min-width: 100px;
  text-align: center;
}}
.stat-num {{ font-size: 1.55rem; font-weight: 800; color: var(--teal-deep); }}
.stat-lbl {{
  font-size: 10px;
  color: var(--muted);
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

.section-tag {{
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--teal-deep);
  margin-bottom: 8px;
}}
.agent-info-card {{
  background: var(--teal-mist);
  border-left: 4px solid var(--teal);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
  font-size: 13px;
  line-height: 1.55;
  color: #1e4d48;
}}
.tool-table {{ width: 100%; font-size: 12px; border-collapse: collapse; margin-top: 8px; }}
.tool-table th, .tool-table td {{ border: 1px solid #b2dfdb; padding: 8px 10px; text-align: left; }}
.tool-table th {{ background: var(--teal-mist); color: var(--teal-deep); }}

.welcome-hero {{ text-align: center; padding: clamp(26px, 6vw, 52px) 16px; }}
.welcome-hero h1 {{ color: var(--teal-deep); font-size: clamp(1.2rem, 3.5vw, 1.55rem); margin-bottom: 12px; }}
.welcome-hero p {{ color: var(--muted); max-width: 680px; margin: 12px auto; line-height: 1.65; font-size: 14px; }}

.plot-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
@media (max-width: 800px) {{ .plot-row {{ grid-template-columns: 1fr; }} }}
.plot-card {{
  background: #fff;
  border-radius: 14px;
  padding: 12px;
  margin-bottom: 4px;
  border: 1px solid rgba(13, 148, 136, 0.15);
}}
.plot-card h5 {{ margin: 0 0 10px; color: var(--teal-deep); font-size: 13px; }}

/* Flip cards — agent highlights */
.flip-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-top: 8px;
}}
@media (max-width: 800px) {{ .flip-grid {{ grid-template-columns: 1fr; }} }}
.flip-card {{
  perspective: 1000px;
  min-height: 160px;
}}
.flip-inner {{
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 160px;
  transition: transform 0.55s ease;
  transform-style: preserve-3d;
}}
.flip-card:hover .flip-inner {{ transform: rotateY(180deg); }}
.flip-front, .flip-back {{
  position: absolute;
  width: 100%;
  height: 100%;
  min-height: 160px;
  backface-visibility: hidden;
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  box-shadow: 0 2px 12px rgba(15, 118, 110, 0.1);
}}
.flip-front {{
  background: linear-gradient(160deg, #fff, var(--teal-mist));
  border: 1px solid rgba(13, 148, 136, 0.2);
}}
.flip-back {{
  background: var(--teal-deep);
  color: #ecfeff;
  transform: rotateY(180deg);
  font-size: 12px;
  line-height: 1.5;
}}
.flip-front h5 {{ margin: 0 0 8px; color: var(--teal-deep); font-size: 14px; }}
.flip-hint {{ font-size: 11px; color: var(--muted); margin-top: auto; }}

.patient-table {{ width: 100%; font-size: 13px; border-collapse: collapse; }}
.patient-table td {{ padding: 6px 10px; border-bottom: 1px solid #e2e8f0; }}
.patient-table td:first-child {{ color: var(--muted); width: 42%; }}

.dl-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }}
</style>
"""

FLIP_CARDS_HTML = """
<div class="flip-grid">
  <div class="flip-card">
    <div class="flip-inner">
      <div class="flip-front">
        <h5>① Data Validator</h5>
        <p style="margin:0;font-size:13px;color:#27635f;">Range checks, consistency, optional LLM JSON audit.</p>
        <span class="flip-hint">Hover to flip →</span>
      </div>
      <div class="flip-back">Outputs: validation status, flags, confidence_score, validated_data for downstream agents.</div>
    </div>
  </div>
  <div class="flip-card">
    <div class="flip-inner">
      <div class="flip-front">
        <h5>② Evidence Retriever</h5>
        <p style="margin:0;font-size:13px;color:#27635f;">Chroma RAG + PubMed + Ollama synthesis.</p>
        <span class="flip-hint">Hover to flip →</span>
      </div>
      <div class="flip-back">Retrieves local papers, live PubMed abstracts, builds clinical_summary and diagnostic criteria hints.</div>
    </div>
  </div>
  <div class="flip-card">
    <div class="flip-inner">
      <div class="flip-front">
        <h5>③ Risk Assessor</h5>
        <p style="margin:0;font-size:13px;color:#27635f;">XGBoost + SHAP + NHANES + recommendation LLM.</p>
        <span class="flip-hint">Hover to flip →</span>
      </div>
      <div class="flip-back">Risk 0–1, SHAP drivers, population percentiles, follow-up tests and lifestyle JSON.</div>
    </div>
  </div>
</div>
"""


def _parse_opt_num(raw: str) -> float | None:
    t = (raw or "").strip()
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _payload_from_inputs(input: Inputs) -> dict[str, Any]:
    p: dict[str, Any] = {
        "persist": bool(input.persist()),
        "age": float(input.age()),
        "bmi": float(input.bmi()),
        "cycle_ri": int(input.cycle_ri()),
        "cycle_length_days": float(input.cycle_length()),
        "lh": float(input.lh()),
        "fsh": float(input.fsh()),
        "tsh": float(input.tsh()),
        "hair_growth": 1 if input.hair() else 0,
        "skin_darkening": 1 if input.skin() else 0,
        "pimples": 1 if input.pimples() else 0,
        "weight_gain": 1 if input.weight_gain() else 0,
        "follicle_l": int(input.follicle_l()),
        "follicle_r": int(input.follicle_r()),
    }
    for key, getter in [
        ("weight_kg", input.opt_weight),
        ("height_cm", input.opt_height),
        ("pulse_bpm", input.opt_pulse),
        ("hb", input.opt_hb),
        ("rbs", input.opt_rbs),
        ("prl", input.opt_prl),
        ("vit_d3", input.opt_vitd),
        ("endometrium_mm", input.opt_endo),
        ("avg_follicle_l_mm", input.opt_af_l),
        ("avg_follicle_r_mm", input.opt_af_r),
    ]:
        v = _parse_opt_num(getter())
        if v is not None:
            p[key] = v
    return p


app_ui = ui.page_fluid(
    ui.HTML(PCOS_CSS),
    ui.div(
        ui.p("PCOSense", class_="title"),
        ui.p("Multi-Agent System for Polycystic Ovary Syndrome Detection", class_="subtitle"),
        ui.span("Screening · Explainability · Clinical context", class_="ribbon"),
        class_="pcos-header",
    ),
    ui.div(
        "Educational decision-support only — not a diagnosis. AUROC ~0.95 XGBoost; SHAP explanations; "
        "ChromaDB + PubMed evidence; NHANES baselines; optional Supabase persistence.",
        class_="disclaimer",
    ),
    ui.layout_sidebar(
        ui.sidebar(
            ui.panel_conditional(
                "output.pcos_need_gate === '1'",
                ui.div(
                    ui.h4("Access", style=f"color:{TEAL_DEEP};"),
                    ui.p("Password-protected deployment.", style="font-size:12px;color:#666;"),
                    ui.input_password("gate_pw", "Password"),
                    ui.input_action_button("gate_submit", "Unlock", style=BTN_STYLE),
                    ui.output_text_verbatim("gate_feedback_text"),
                ),
            ),
            ui.panel_conditional(
                "output.pcos_need_gate === '0'",
                ui.div(
                    ui.h4("Patient input", style=f"color:{TEAL_DEEP};"),
                    ui.p(
                        "Core fields below; optional labs expand the 42-feature model (blank = imputed).",
                        style="font-size:11px;color:#64748b;margin-bottom:10px;",
                    ),
                    ui.h6("Core", style=f"color:{TEAL_DARK};margin:8px 0 4px;font-size:12px;"),
                    ui.input_numeric("age", "Age (years)", value=28, min=12, max=60),
                    ui.input_numeric("bmi", "BMI", value=28.6, min=10, max=65),
                    ui.input_select(
                        "cycle_ri",
                        "Cycle (R/I)",
                        {"1": "Regular (1)", "2": "Irregular (2)"},
                        selected="2",
                    ),
                    ui.input_numeric("cycle_length", "Cycle length (days)", value=35, min=15, max=90),
                    ui.input_numeric("lh", "LH (mIU/mL)", value=11.2),
                    ui.input_numeric("fsh", "FSH (mIU/mL)", value=4.5),
                    ui.input_numeric("tsh", "TSH (mIU/L)", value=3.2),
                    ui.input_checkbox("hair", "Hair growth (hirsutism)", value=True),
                    ui.input_checkbox("skin", "Skin darkening", value=True),
                    ui.input_checkbox("pimples", "Acne / pimples", value=True),
                    ui.input_checkbox("weight_gain", "Weight gain", value=True),
                    ui.input_numeric("follicle_l", "Follicle No. (L)", value=12, min=0, max=30),
                    ui.input_numeric("follicle_r", "Follicle No. (R)", value=14, min=0, max=30),
                    ui.h6("Optional vitals & labs", style=f"color:{TEAL_DARK};margin:14px 0 4px;font-size:12px;"),
                    ui.p("Numbers only; leave blank to omit.", style="font-size:10px;color:#94a3b8;margin:0 0 6px;"),
                    ui.input_text("opt_weight", "Weight (Kg)", placeholder="e.g. 75"),
                    ui.input_text("opt_height", "Height (cm)", placeholder="e.g. 162"),
                    ui.input_text("opt_pulse", "Pulse (bpm)", placeholder=""),
                    ui.input_text("opt_hb", "Hb (g/dl)", placeholder=""),
                    ui.input_text("opt_rbs", "RBS (mg/dl)", placeholder=""),
                    ui.input_text("opt_prl", "PRL (ng/mL)", placeholder=""),
                    ui.input_text("opt_vitd", "Vit D3 (ng/mL)", placeholder=""),
                    ui.input_text("opt_endo", "Endometrium (mm)", placeholder=""),
                    ui.input_text("opt_af_l", "Avg follicle size L (mm)", placeholder=""),
                    ui.input_text("opt_af_r", "Avg follicle size R (mm)", placeholder=""),
                    ui.hr(),
                    ui.input_checkbox("run_local", "Run in-process (no FastAPI)", value=False),
                    ui.input_checkbox("persist", "Persist to Supabase (if configured)", value=True),
                    ui.input_text("api_url", "API base URL", value=API_BASE),
                    ui.input_action_button("submit", "Run multi-agent assessment", style=BTN_STYLE),
                ),
            ),
            width=318,
        ),
        ui.div(
            ui.output_ui("welcome_ui"),
            ui.panel_conditional(
                "(input.submit || 0) >= 1",
                ui.div(
                    ui.span("Results", class_="section-tag"),
                    ui.h4("🩺 Your assessment at a glance"),
                    ui.output_ui("results_hero_ui"),
                    class_="card",
                ),
            ),
            ui.panel_conditional(
                "(input.submit || 0) >= 1",
                ui.div(
                    ui.span("Submitted profile", class_="section-tag"),
                    ui.h4("📋 Inputs sent to the pipeline"),
                    ui.output_ui("patient_summary_ui"),
                    class_="card",
                ),
            ),
            ui.panel_conditional(
                "(input.submit || 0) >= 1",
                ui.div(
                    ui.span("Pipeline", class_="section-tag"),
                    ui.div(
                        ui.span("① Data Validator", class_="agent-badge"),
                        ui.span("→", class_="agent-arrow"),
                        ui.span("② Evidence Retriever", class_="agent-badge"),
                        ui.span("→", class_="agent-arrow"),
                        ui.span("③ Risk Assessor", class_="agent-badge"),
                        class_="agent-strip",
                    ),
                    ui.p(
                        "Validate → RAG + PubMed → XGBoost + SHAP + NHANES + LLM recommendation.",
                        style="font-size:12px;color:#64748b;margin:0 0 12px;",
                    ),
                    ui.HTML(FLIP_CARDS_HTML),
                    class_="card",
                ),
            ),
            ui.panel_conditional(
                "(input.submit || 0) >= 1",
                ui.div(
                    ui.span("Analytics", class_="section-tag"),
                    ui.h4("📊 Risk score, validation & evidence volume"),
                    ui.output_ui("stats_row_ui"),
                    ui.output_ui("model_metrics_ui"),
                    ui.div(
                        ui.div(
                            ui.h5("SHAP — top risk drivers"),
                            ui.output_plot("shap_plot", height=270),
                            class_="plot-card",
                        ),
                        ui.div(
                            ui.h5("Risk score (0–1)"),
                            ui.output_plot("risk_donut_plot", height=270),
                            class_="plot-card",
                        ),
                        class_="plot-row",
                    ),
                    class_="card",
                ),
            ),
            ui.panel_conditional(
                "(input.submit || 0) >= 1",
                ui.div(
                    ui.span("Architecture", class_="section-tag"),
                    ui.h4("🤖 Agent roles (detail)"),
                    ui.div(
                        ui.div(
                            ui.tags.strong("Agent 1 — Data Validator"),
                            ui.p(
                                "Programmatic ranges + optional Llama 3.2 JSON validation. "
                                "Outputs: status, flags, confidence_score, validated_data.",
                                style="margin:6px 0 0;font-size:13px;color:#27635f;",
                            ),
                            class_="agent-info-card",
                        ),
                        ui.div(
                            ui.tags.strong("Agent 2 — Clinical Evidence Retriever"),
                            ui.p(
                                "ChromaDB RAG + PubMed E-utilities + Ollama JSON synthesis "
                                "(clinical_summary, diagnostic criteria, key findings, red flags).",
                                style="margin:6px 0 0;font-size:13px;color:#27635f;",
                            ),
                            class_="agent-info-card",
                        ),
                        ui.div(
                            ui.tags.strong("Agent 3 — Risk Assessor"),
                            ui.p(
                                "XGBoost probability, SHAP TreeExplainer, NHANES percentiles, "
                                "LLM recommendation with follow_up_tests and lifestyle_suggestions.",
                                style="margin:6px 0 0;font-size:13px;color:#27635f;",
                            ),
                            class_="agent-info-card",
                        ),
                    ),
                    class_="card",
                ),
            ),
            ui.panel_conditional(
                "(input.submit || 0) >= 1",
                ui.div(
                    ui.span("RAG & tool calling", class_="section-tag"),
                    ui.h4("🛠 Tools & retrieval"),
                    ui.output_ui("tools_rag_ui"),
                    class_="card",
                ),
            ),
            ui.panel_conditional(
                "(input.submit || 0) >= 1",
                ui.div(
                    ui.span("Exports", class_="section-tag"),
                    ui.h4("📥 Download report"),
                    ui.p("Save JSON or a short clinician-oriented summary.", style="font-size:13px;color:#64748b;"),
                    ui.div(
                        ui.download_button(
                            "dl_json",
                            "Download JSON",
                            style=f"background:{TEAL_DARK};color:#fff;border:none;padding:8px 16px;border-radius:8px;",
                        ),
                        ui.download_button(
                            "dl_summary",
                            "Download summary (.txt)",
                            style=f"background:{TEAL};color:#fff;border:none;padding:8px 16px;border-radius:8px;",
                        ),
                        class_="dl-row",
                    ),
                    class_="card",
                ),
            ),
            ui.output_ui("status_ui"),
            ui.output_ui("validation_ui"),
            ui.output_ui("evidence_ui"),
            ui.output_ui("assessment_ui"),
            ui.output_ui("raw_json_ui"),
            class_="main-wrap",
        ),
    ),
)


def server(input: Inputs, output: Outputs, session: Session) -> None:
    _unlocked = reactive.Value(not bool(_PASSWORD))

    @reactive.Effect
    @reactive.event(input.gate_submit)
    def _gate():
        if not _PASSWORD:
            return
        if input.gate_pw() == _PASSWORD:
            _unlocked.set(True)

    @render.text
    def pcos_need_gate():
        _unlocked()
        return "1" if _PASSWORD and not _unlocked() else "0"

    @render.text
    def gate_feedback_text():
        if not _PASSWORD:
            return ""
        if _unlocked():
            return "Unlocked — use the form below."
        if input.gate_submit() == 0:
            return ""
        return "Incorrect password."

    @render.ui
    def welcome_ui():
        if input.submit() > 0:
            return ui.div()
        return ui.div(
            ui.div(
                ui.h1("PCOS screening with transparent AI"),
                ui.div(
                    ui.markdown(
                        "Phase 3: enter **core + optional** patient data → three-agent pipeline → "
                        "**risk score**, **SHAP factors**, **clinical evidence** (RAG + PubMed), "
                        "**LLM recommendation**, downloads, optional **Supabase** persistence."
                    ),
                    style="margin-bottom:12px;",
                ),
                ui.div(
                    ui.markdown(
                        "Start **FastAPI** (`uvicorn src.api.main:app`) or **Run in-process** with "
                        "`PCOSOrchestrator` on a full PCOSense checkout."
                    ),
                ),
                class_="welcome-hero",
            ),
            class_="card",
        )

    @reactive.calc
    @reactive.event(input.submit)
    def pipeline_result() -> dict[str, Any] | None:
        flat = _payload_from_inputs(input)
        if input.run_local():
            try:
                from src.database import SupabaseClient
                from src.patient_payload import patient_dict_from_flat_body

                patient, persist = patient_dict_from_flat_body(dict(flat))
                db = None
                if persist:
                    c = SupabaseClient()
                    if c.is_configured():
                        db = c
                from src.agents import PCOSOrchestrator

                return PCOSOrchestrator(db=db).run(patient)
            except ImportError as exc:
                return {
                    "_error": (
                        "In-process run requires PCOSense Phase 2 (`PCOSOrchestrator`). "
                        f"{exc}"
                    ),
                    "_status": 0,
                }
            except Exception as exc:
                return {"_error": str(exc), "_status": 0}

        base = (input.api_url() or API_BASE).rstrip("/")
        try:
            with httpx.Client(timeout=180.0) as client:
                r = client.post(f"{base}/api/v1/assess/raw", json=flat)
                if r.status_code >= 400:
                    return {"_error": r.text, "_status": r.status_code}
                return r.json()
        except httpx.ConnectError:
            return {
                "_error": (
                    f"No API at {base}. Run: uvicorn src.api.main:app --reload "
                    "or use **Run in-process** with a full checkout."
                ),
                "_status": 0,
            }
        except Exception as exc:
            return {"_error": str(exc), "_status": 0}

    def _res() -> dict[str, Any] | None:
        if input.submit() == 0:
            return None
        return pipeline_result()

    @render.ui
    def results_hero_ui():
        if input.submit() == 0:
            return ui.div()
        r = _res()
        if not r:
            return ui.p("Running…", class_="text-muted")
        if r.get("_error"):
            return ui.p("See error card below for details.", class_="text-muted")
        a = r.get("assessment") or {}
        score = a.get("risk_score")
        label = str(a.get("risk_label", "—"))
        rec = str(a.get("recommendation", "") or "")[:420]
        pct = int(round(min(100, max(0, float(score) * 100)))) if score is not None else 0
        snippet = rec + ("…" if len(str(a.get("recommendation", ""))) > 420 else "")
        return ui.div(
            ui.div(
                ui.div(
                    ui.div(
                        ui.div(f"{float(score):.2f}" if score is not None else "—", class_="big"),
                        ui.div("Risk (0–1)", class_="lbl"),
                        class_="risk-ring-inner",
                    ),
                    class_="risk-ring",
                    style=f"--p: {pct};",
                ),
                ui.div(
                    ui.span(label, class_="hero-label"),
                    ui.p(
                        "Recommendation (excerpt):",
                        style="font-size:11px;color:#64748b;margin:0 0 4px;",
                    ),
                    ui.p(snippet or "—", class_="hero-reco"),
                ),
                class_="hero-results",
            ),
        )

    @render.ui
    def patient_summary_ui():
        if input.submit() == 0:
            return ui.div()
        rows = []
        labels: list[tuple[str, Any]] = [
            ("Age (yrs)", lambda: input.age()),
            ("BMI", lambda: input.bmi()),
            ("Cycle (R/I)", lambda: input.cycle_ri()),
            ("Cycle length (d)", lambda: input.cycle_length()),
            ("LH", lambda: input.lh()),
            ("FSH", lambda: input.fsh()),
            ("TSH", lambda: input.tsh()),
            ("Hair growth", lambda: "Y" if input.hair() else "N"),
            ("Skin darkening", lambda: "Y" if input.skin() else "N"),
            ("Pimples", lambda: "Y" if input.pimples() else "N"),
            ("Weight gain", lambda: "Y" if input.weight_gain() else "N"),
            ("Follicle L", lambda: input.follicle_l()),
            ("Follicle R", lambda: input.follicle_r()),
        ]
        for lab, fn in labels:
            try:
                v = fn()
            except Exception:
                v = "—"
            rows.append(f"<tr><td>{html.escape(lab)}</td><td>{html.escape(str(v))}</td></tr>")
        opts = [
            ("Weight (Kg)", input.opt_weight),
            ("Height (cm)", input.opt_height),
            ("Pulse", input.opt_pulse),
            ("Hb", input.opt_hb),
            ("RBS", input.opt_rbs),
            ("PRL", input.opt_prl),
            ("Vit D3", input.opt_vitd),
            ("Endometrium", input.opt_endo),
            ("Avg F L", input.opt_af_l),
            ("Avg F R", input.opt_af_r),
        ]
        for lab, fn in opts:
            t = (fn() or "").strip()
            if t:
                rows.append(f"<tr><td>{html.escape(lab)}</td><td>{html.escape(t)}</td></tr>")
        return ui.HTML(f"<table class='patient-table'>{''.join(rows)}</table>")

    @render.ui
    def stats_row_ui():
        r = _res()
        if not r or r.get("_error"):
            return ui.div()
        v = r.get("validation") or {}
        a = r.get("assessment") or {}
        e = r.get("evidence") or {}
        risk = a.get("risk_score")
        conf = v.get("confidence_score", v.get("confidence"))
        n_loc = len(e.get("retrieved_papers") or [])
        n_pub = len(e.get("pubmed_papers") or [])
        return ui.div(
            ui.div(
                ui.div(f"{float(risk):.2f}" if risk is not None else "—", class_="stat-num"),
                ui.div("Risk score", class_="stat-lbl"),
                class_="stat-box",
            ),
            ui.div(
                ui.div(str(conf) if conf is not None else "—", class_="stat-num"),
                ui.div("Validation confidence", class_="stat-lbl"),
                class_="stat-box",
            ),
            ui.div(
                ui.div(str(n_loc + n_pub), class_="stat-num"),
                ui.div("Papers retrieved", class_="stat-lbl"),
                class_="stat-box",
            ),
            class_="stat-row",
        )

    @render.ui
    def model_metrics_ui():
        r = _res()
        if not r or r.get("_error"):
            return ui.div()
        a = r.get("assessment") or {}
        if not a:
            return ui.div()
        parts = []
        if a.get("model_auroc") is not None:
            parts.append(f"Model AUROC (reported): **{a.get('model_auroc')}**")
        if a.get("threshold_used") is not None:
            parts.append(f"Threshold: **{a.get('threshold_used')}**")
        if a.get("predicted_class") is not None:
            parts.append(f"Predicted class: **{a.get('predicted_class')}**")
        if a.get("confidence") is not None:
            parts.append(f"Model confidence: **{a.get('confidence')}**")
        if a.get("confidence_assessment"):
            parts.append(f"LLM confidence note: {a.get('confidence_assessment')}")
        if not parts:
            return ui.div()
        return ui.p(
            ui.HTML(" · ".join(parts)),
            style="font-size:13px;color:#27635f;margin:0 0 12px;line-height:1.6;",
        )

    @render.plot
    def shap_plot():
        fig, ax = plt.subplots(figsize=(5, 3.3))
        if input.submit() == 0:
            ax.axis("off")
            return fig
        r = _res()
        if not r or r.get("_error"):
            ax.axis("off")
            return fig
        factors = (r.get("assessment") or {}).get("top_factors") or []
        if not factors:
            ax.text(0.5, 0.5, "No SHAP factors", ha="center", va="center", color="#64748b")
            ax.axis("off")
            return fig
        names = [str(f.get("feature", ""))[:30] for f in factors[:10]][::-1]
        vals = [float(f.get("shap_value") or 0) for f in factors[:10]][::-1]
        colors = [TEAL if v >= 0 else "#94a3b8" for v in vals]
        ax.barh(names, vals, color=colors)
        ax.axvline(0, color="#334155", linewidth=0.6)
        ax.set_xlabel("SHAP (impact on risk)")
        ax.tick_params(colors="#134e4a")
        fig.patch.set_facecolor("#fafafa")
        fig.tight_layout()
        return fig

    @render.plot
    def risk_donut_plot():
        fig, ax = plt.subplots(figsize=(4, 3.3))
        if input.submit() == 0:
            ax.axis("off")
            return fig
        r = _res()
        if not r or r.get("_error"):
            ax.axis("off")
            return fig
        score = (r.get("assessment") or {}).get("risk_score")
        if score is None:
            ax.text(0.5, 0.5, "No score", ha="center", va="center")
            ax.axis("off")
            return fig
        s = float(score)
        s = min(1.0, max(0.0, s))
        rest = 1.0 - s
        ax.pie(
            [s, rest],
            labels=[f"{s:.2f}", ""],
            colors=[TEAL, "#e2e8f0"],
            startangle=90,
            wedgeprops=dict(width=0.35, edgecolor="white"),
            textprops={"fontsize": 11, "color": TEAL_DEEP},
        )
        ax.text(0, 0, "risk", ha="center", va="center", fontsize=10, color="#64748b")
        fig.patch.set_facecolor("#fafafa")
        fig.tight_layout()
        return fig

    @render.ui
    def tools_rag_ui():
        if input.submit() == 0:
            return ui.div()
        r = _res()
        e = (r or {}).get("evidence") or {}
        q = e.get("query_used", "—")
        rows = """
<tr><td>ChromaDB RAG</td><td>Vector search over local PCOS paper index (~27 curated sources).</td></tr>
<tr><td>PubMed API</td><td>E-utilities: phenotype query from validated profile.</td></tr>
<tr><td>NHANES</td><td>Population percentiles for labs (Agent 3 context).</td></tr>
<tr><td>XGBoost + SHAP</td><td>Trained classifier + TreeExplainer.</td></tr>
<tr><td>Ollama Llama 3.2</td><td>Structured JSON for validation, evidence, recommendations.</td></tr>
<tr><td>Supabase</td><td>Optional persist: patients, predictions, audit_log (when configured).</td></tr>
"""
        q_safe = html.escape(str(q))
        return ui.HTML(
            f"<p style='font-size:13px;color:#27635f;margin:0 0 6px;'><b>Evidence query:</b> "
            f"<code style='background:{TEAL_MIST};padding:2px 8px;border-radius:6px;'>{q_safe}</code></p>"
            f"<table class='tool-table'><thead><tr><th>Tool / store</th><th>Role</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    @render.download(filename="pcosense_report.json")
    def dl_json():
        r = _res()
        if not r or r.get("_error"):
            yield "{}"
            return
        yield json.dumps(r, indent=2, default=str)

    @render.download(filename="pcosense_summary.txt")
    def dl_summary():
        r = _res()
        buf = StringIO()
        if not r or r.get("_error"):
            buf.write("PCOSense — error\n" + str(r.get("_error", "")))
            yield buf.getvalue()
            return
        a = r.get("assessment") or {}
        v = r.get("validation") or {}
        e = r.get("evidence") or {}
        buf.write("PCOSense — Clinical summary (educational)\n")
        buf.write("=" * 48 + "\n\n")
        buf.write(f"Validation: {v.get('status')} (confidence {v.get('confidence_score')})\n\n")
        buf.write(f"Risk score: {a.get('risk_score')}  Label: {a.get('risk_label')}\n\n")
        buf.write("Top factors (SHAP):\n")
        for tf in (a.get("top_factors") or [])[:8]:
            buf.write(f"  - {tf.get('feature')}: {tf.get('shap_value')}\n")
        buf.write("\nClinical evidence summary:\n")
        buf.write(str(e.get("clinical_summary", ""))[:2000] + "\n\n")
        buf.write("Recommendation:\n")
        buf.write(str(a.get("recommendation", "")) + "\n")
        yield buf.getvalue()

    @render.ui
    def status_ui():
        if input.submit() == 0:
            return ui.div()
        res = _res()
        if res is None:
            return ui.div()
        if res.get("_error"):
            return ui.div(
                ui.h4("Run error"),
                ui.p(f"Code: {res.get('_status')}", class_="fw-bold"),
                ui.pre(res["_error"][:8000], class_="json-out"),
                class_="card",
            )
        meta = res.get("metadata") or {}
        line = f"Status: **{meta.get('status', '')}** · {meta.get('elapsed_sec', '')}s"
        if meta.get("patient_id"):
            line += f" · Supabase `patient_id`: `{meta['patient_id']}`"
        return ui.div(
            ui.h4("Pipeline status"),
            ui.p(ui.markdown(line)),
            class_="card",
        )

    @render.ui
    def validation_ui():
        if input.submit() == 0:
            return ui.div()
        res = _res()
        if not res or res.get("_error"):
            return ui.div()
        v = res.get("validation") or {}
        if not v:
            return ui.div()
        flags = v.get("flags") or []
        flag_items = []
        for f in flags[:18]:
            sev = f.get("severity", "")
            cls = "flag-err" if sev == "error" else "flag-warn"
            flag_items.append(
                ui.p(
                    ui.span(f"{f.get('field', '')}: ", class_=cls),
                    f.get("issue", ""),
                    class_="small",
                )
            )
        conf = v.get("confidence_score", v.get("confidence"))
        llm = v.get("llm_analysis")
        llm_block = ui.div()
        if llm and isinstance(llm, dict) and llm:
            llm_block = ui.div(
                ui.h5("LLM validation JSON"),
                ui.pre(json.dumps(llm, indent=2)[:4000], class_="json-out"),
            )
        return ui.div(
            ui.h4("① Data Validator"),
            ui.p(ui.strong("Status: "), str(v.get("status", ""))),
            ui.p(ui.strong("Confidence: "), str(conf)),
            ui.div(*flag_items) if flag_items else ui.p("No flags.", class_="text-muted"),
            llm_block,
            class_="card",
        )

    @render.ui
    def evidence_ui():
        if input.submit() == 0:
            return ui.div()
        res = _res()
        if not res or res.get("_error"):
            return ui.div()
        e = res.get("evidence") or {}
        if not e:
            return ui.div(ui.p("No evidence block."), class_="card")

        local_n = len(e.get("retrieved_papers") or [])
        pub_n = len(e.get("pubmed_papers") or [])
        summary = e.get("clinical_summary") or ""
        criteria = e.get("diagnostic_criteria") or []
        findings = e.get("key_findings") or []
        red = e.get("red_flags") or []

        paper_bits = []
        for p in (e.get("retrieved_papers") or [])[:8]:
            paper_bits.append(
                ui.tags.li(
                    f"{p.get('title', '')} ({p.get('year', '')}) — {str(p.get('excerpt', ''))[:220]}…"
                )
            )
        pub_bits = []
        for p in (e.get("pubmed_papers") or [])[:6]:
            pub_bits.append(
                ui.tags.li(f"PMID {p.get('pmid', '')}: {p.get('title', '')}")
            )

        return ui.div(
            ui.h4("② Clinical evidence — RAG + PubMed"),
            ui.p(f"Chroma: {local_n} · PubMed: {pub_n}", style="font-size:13px;color:#64748b;"),
            ui.h5("Clinical summary"),
            ui.p(summary[:2800] or "—"),
            ui.h5("Diagnostic criteria hints"),
            ui.tags.ul(*[ui.tags.li(str(c)) for c in criteria])
            if criteria
            else ui.p("—", class_="text-muted"),
            ui.h5("Key findings"),
            ui.tags.ul(*[ui.tags.li(str(c)) for c in findings])
            if findings
            else ui.p("—", class_="text-muted"),
            ui.h5("Red flags"),
            ui.tags.ul(*[ui.tags.li(str(c)) for c in red])
            if red
            else ui.p("—", class_="text-muted"),
            ui.h5("RAG excerpts"),
            ui.tags.ul(*paper_bits) if paper_bits else ui.p("—", class_="text-muted"),
            ui.h5("PubMed"),
            ui.tags.ul(*pub_bits) if pub_bits else ui.p("—", class_="text-muted"),
            class_="card",
        )

    @render.ui
    def assessment_ui():
        if input.submit() == 0:
            return ui.div()
        res = _res()
        if not res or res.get("_error"):
            return ui.div()
        a = res.get("assessment") or {}
        if not a:
            return ui.div(ui.p("No assessment."), class_="card")

        score = float(a.get("risk_score") or 0)
        pct = min(100, max(0, score * 100))
        label = a.get("risk_label", "")
        top = a.get("top_factors") or []
        factor_lines = []
        for tf in top[:12]:
            factor_lines.append(
                ui.tags.li(
                    f"{tf.get('feature', '')}: SHAP {tf.get('shap_value', 0):+.4f} "
                    f"(value={tf.get('raw_value')}, {tf.get('direction', '')})"
                )
            )
        pop = a.get("population_context") or []
        pop_lines = [
            ui.tags.li(f"{p.get('hormone', '')}: {p.get('interpretation', '')}") for p in pop[:10]
        ]

        rec = a.get("recommendation") or ""
        follow = a.get("follow_up_tests") or []
        life = a.get("lifestyle_suggestions") or []
        expl = a.get("explanation_text") or ""

        extras = []
        if expl:
            extras.append(ui.h5("Model explanation"))
            extras.append(ui.p(str(expl)[:2500], style="font-size:13px;line-height:1.6;"))

        return ui.div(
            ui.h4("③ Risk assessment — score, factors, recommendation"),
            ui.p(ui.strong("Risk label: "), str(label)),
            ui.div(
                ui.div(f"{score:.2f}", class_="risk-bar-fill", style=f"width: {pct}%;"),
                class_="risk-bar-wrap",
            ),
            ui.h5("Top contributing factors (SHAP)"),
            ui.tags.ul(*factor_lines) if factor_lines else ui.p("—", class_="text-muted"),
            *extras,
            ui.h5("NHANES population context"),
            ui.tags.ul(*pop_lines) if pop_lines else ui.p("—", class_="text-muted"),
            ui.h5("Clinical recommendation"),
            ui.p(rec or "—", style="font-size:14px;line-height:1.65;"),
            ui.p(ui.strong("Follow-up tests: "), ", ".join(str(x) for x in follow) if follow else "—"),
            ui.p(ui.strong("Lifestyle: "), "; ".join(str(x) for x in life) if life else "—"),
            class_="card",
        )

    @render.ui
    def raw_json_ui():
        if input.submit() == 0:
            return ui.div()
        res = _res()
        if not res or res.get("_error"):
            return ui.div()
        return ui.div(
            ui.h4("Raw JSON (debug)"),
            ui.pre(json.dumps(res, indent=2, default=str)[:16000], class_="json-out"),
            class_="card",
        )


app = App(app_ui, server)
