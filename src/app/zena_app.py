"""
Zena 💗 V2 – Preventive Healthcare for First-Gen & International Female Students
Multi-Agent System with Tool Calling + RAG Cultural Knowledge Base

Fixes from V1 feedback:
  ✓ Readiness score now tracks checkbox selections (was always 0%)
  ✓ AI summary is truly dynamic per age / country / vaccines
  ✓ Country drives Agent 3 + RAG retrieval (was ignored in V1)
  ✓ Multi-agent pipeline: Profile Analyst → Recommendation Curator → Cultural Navigator
"""

from __future__ import annotations

import os
import random
from io import StringIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, Session, reactive, render, ui

load_dotenv()

_PASSWORD = os.getenv("ZENA_APP_PASSWORD", "").strip()

from src.agents import orchestrate_health_plan
from src.api_client import fetch_myhealthfinder
from src.data_processing import process_recommendations
from src.rag import init_rag_db

# Pre-warm the RAG SQLite database
init_rag_db()

# Hard-coded quiz questions (static, no AI needed)
MYTH_FACT_QUIZ: list[tuple[str, bool]] = [
    ("You should only see a doctor when you feel sick.", False),
    ("The HPV vaccine can prevent certain cancers.", True),
    ("Pap smears are only recommended for sexually active women.", False),
    ("Annual well-woman visits are often 100% covered by insurance under the ACA.", True),
    ("You need a parent's permission to receive confidential reproductive health care at a US university clinic.", False),
    ("Depression screening is a standard part of preventive care in the US.", True),
    ("The flu vaccine gives you the flu.", False),
    ("Blood pressure checks are recommended annually starting at age 18.", True),
    ("Mental health counseling at universities is typically free for enrolled students.", True),
    ("Vaccines weaken your immune system.", False),
]

COUNTRIES: list[str] = [
    "United States", "India", "China", "Mexico", "South Korea", "Vietnam",
    "Nigeria", "Brazil", "Canada", "Philippines", "Colombia", "Pakistan",
    "Bangladesh", "Egypt", "Ethiopia", "Iran", "Germany", "Turkey",
    "Indonesia", "Thailand", "Kenya",
]

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
PINK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
:root {
  --primary-pink: #F48FB1;
  --light-bg: #FFF0F5;
  --accent-rose: #EC407A;
  --text: #444;
  --white: #ffffff;
  --high: #EC407A;
  --routine: #F48FB1;
  --info: #aaa;
}
* { box-sizing: border-box; }
body { font-family: 'Poppins', sans-serif !important; background: var(--light-bg) !important; color: var(--text); margin: 0; }
.zena-header {
  background: linear-gradient(135deg, var(--primary-pink), var(--accent-rose));
  color: #fff; padding: clamp(20px, 4vw, 32px); text-align: center;
  box-shadow: 0 4px 20px rgba(244,143,177,.35); margin-bottom: 0;
}
.zena-header h2 { margin: 0; font-size: clamp(22px,5vw,30px); }
.zena-header p  { margin: 6px 0 0; opacity: .92; font-size: clamp(13px,2vw,15px); }
.main-content { max-width: min(1020px,96vw); margin: 0 auto; padding: clamp(12px,2.5vw,22px); }
.disclaimer {
  font-size: 12px; color: #888; padding: 10px 14px; background: #fafafa;
  border-left: 4px solid var(--accent-rose); border-radius: 8px; margin-bottom: 18px;
}
.zena-card {
  background: #fff; border-radius: 16px;
  padding: clamp(14px,3vw,20px); margin-bottom: 16px;
  box-shadow: 0 2px 14px rgba(0,0,0,.07);
  transition: box-shadow .2s;
}
.zena-card:hover { box-shadow: 0 4px 22px rgba(244,143,177,.22); }
.zena-card h4 { margin: 0 0 14px; color: var(--accent-rose); font-size: 16px; }

/* Agent pipeline badge strip */
.agent-strip {
  display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; align-items: center;
}
.agent-badge {
  background: linear-gradient(135deg, var(--primary-pink), var(--accent-rose));
  color: #fff; border-radius: 20px; padding: 4px 14px; font-size: 12px; font-weight: 600;
}
.agent-arrow { color: var(--accent-rose); font-weight: 700; font-size: 16px; }

/* Checklist items */
.check-item {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 10px 12px; border-radius: 10px; margin-bottom: 8px;
  border-left: 4px solid transparent; background: #fafafa;
  transition: background .15s;
}
.check-item:hover { background: #fff0f5; }
.check-item.priority-High   { border-color: var(--high); }
.check-item.priority-Routine{ border-color: var(--routine); }
.check-item.priority-Informational { border-color: #ccc; }
.check-item label { cursor: pointer; }
.check-item .item-title { font-weight: 500; font-size: 14px; }
.check-item .item-cat   { font-size: 12px; color: #999; margin-top: 2px; }
.badge {
  display: inline-block; border-radius: 20px; padding: 2px 10px; font-size: 11px;
  font-weight: 600; margin-left: auto; white-space: nowrap; align-self: center;
}
.badge-High   { background: var(--high);    color: #fff; }
.badge-Routine{ background: var(--routine); color: #fff; }
.badge-Informational { background: #e0e0e0; color: #666; }

/* Score circle */
.score-wrap  { text-align: center; margin-bottom: 14px; }
.score-circle {
  width: clamp(64px,12vw,80px); height: clamp(64px,12vw,80px);
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-pink), var(--accent-rose));
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: clamp(18px,4vw,24px); font-weight: 700; margin: 0 auto 6px;
}
.score-label { font-size: 13px; color: #888; }

/* Quiz */
.quiz-card {
  background: linear-gradient(135deg,#fff5f8,#ffe4ec);
  border: 2px solid var(--primary-pink); border-radius: 16px; padding: 22px;
}
.quiz-statement { font-size: 17px; font-weight: 500; margin-bottom: 16px; line-height: 1.5; }
.quiz-buttons   { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; margin-bottom: 12px; }
.quiz-result { font-weight: 600; padding: 8px 14px; border-radius: 8px; text-align: center; }
.quiz-correct { background: #c8e6c9; color: #2e7d32; }
.quiz-wrong   { background: #ffcdd2; color: #c62828; }

/* Profile JSON preview */
.profile-preview {
  background: #fff8fb; border-radius: 10px; padding: 12px 16px;
  font-size: 12px; color: #666; font-family: monospace;
  border-left: 3px solid var(--primary-pink); margin-top: 10px; overflow-x: auto;
}

/* Welcome */
.welcome-section { text-align: center; padding: clamp(36px,7vw,72px) 20px; }
.welcome-section h1 { color: var(--accent-rose); font-size: clamp(22px,5vw,30px); }
.welcome-section p  { color: #666; max-width: 600px; margin: 12px auto; line-height: 1.65; }

@media (max-width: 640px) {
  .quiz-buttons { flex-direction: column; }
  .agent-strip  { gap: 6px; }
}

/* App V2 — stats, analytics, transparency panels */
.stat-row {
  display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 18px; justify-content: center;
}
.stat-box {
  background: linear-gradient(145deg, #fff, #fff8fc);
  border: 1px solid #f8bbd0; border-radius: 14px;
  padding: 16px 22px; min-width: 120px; text-align: center;
  box-shadow: 0 2px 10px rgba(236,64,122,0.08);
}
.stat-num { font-size: 1.75rem; font-weight: 700; color: var(--accent-rose); }
.stat-lbl { font-size: 12px; color: #888; margin-top: 4px; }

.plot-row {
  display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;
}
@media (max-width: 768px) { .plot-row { grid-template-columns: 1fr; } }
.plot-card {
  background: #fff; border-radius: 14px; padding: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.plot-card h5 { margin: 0 0 8px; color: var(--accent-rose); font-size: 14px; }

.agent-info-card {
  background: #fff8fb; border-left: 4px solid var(--primary-pink);
  border-radius: 10px; padding: 12px 14px; margin-bottom: 10px;
}
.tool-table { width: 100%; font-size: 13px; border-collapse: collapse; margin-top: 8px; }
.tool-table th, .tool-table td { border: 1px solid #f0d0e0; padding: 8px 10px; text-align: left; }
.tool-table th { background: #fff0f5; color: var(--accent-rose); }
.snippet-card {
  font-size: 13px; line-height: 1.55; color: #555;
  background: #fafafa; border-radius: 10px; padding: 12px 14px; margin-bottom: 10px;
  border-left: 3px solid var(--routine);
}
.section-tag {
  display: inline-block; font-size: 11px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.04em; color: #ad1457; margin-bottom: 8px;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────
app_ui = ui.page_fluid(
    ui.HTML(PINK_CSS),
    # Header
    ui.div(
        ui.h2("💗 Zena 💗"),
        ui.p("Preventive healthcare in the U.S.—explained without the confusion."),
        class_="zena-header",
    ),
    ui.div(
        ui.div(
            "Educational guidance based on U.S. preventive care recommendations. Not medical advice.",
            class_="disclaimer",
        ),
        class_="main-content",
    ),
    ui.layout_sidebar(
        ui.sidebar(
            ui.panel_conditional(
                "output.zena_need_gate === '1'",
                ui.div(
                    ui.h4("Access", style="color: var(--accent-rose);"),
                    ui.p(
                        "Hosted deployments can require a password (set by your team in .env).",
                        style="font-size:12px;color:#666;",
                    ),
                    ui.input_password("gate_pw", "App password"),
                    ui.input_action_button(
                        "gate_submit",
                        "Unlock",
                        style=(
                            "background: var(--accent-rose); border-color: var(--accent-rose);"
                            "color:#fff;margin-top:10px;width:100%;font-weight:600;border-radius:8px;"
                        ),
                    ),
                    ui.output_text_verbatim("gate_feedback_text"),
                ),
            ),
            ui.panel_conditional(
                "output.zena_need_gate === '0'",
                ui.div(
                    ui.h4("Your Profile", style="color: var(--accent-rose); margin-bottom:14px;"),
                    ui.input_numeric("age", "Age", 22, min=16, max=60),
                    ui.input_select(
                        "country",
                        "Country of Origin",
                        {c: c for c in COUNTRIES},
                        selected="United States",
                    ),
                    ui.hr(style="border-color:#f8bbd0;"),
                    ui.h5("Vaccination Status", style="color:#555; margin-bottom:6px;"),
                    ui.input_checkbox_group(
                        "vaccines",
                        "Vaccines Completed",
                        choices=["HPV", "Tdap", "Flu", "MMR"],
                        selected=[],
                    ),
                    ui.input_checkbox("unsure", "Unsure about some vaccines", False),
                    ui.hr(style="border-color:#f8bbd0;"),
                    ui.input_radio_buttons(
                        "insurance",
                        "Do you have health insurance?",
                        {"yes": "Yes", "no": "No"},
                        selected="yes",
                    ),
                    ui.input_action_button(
                        "generate",
                        "💗 Generate My Preventive Plan",
                        style=(
                            "background: var(--accent-rose); border-color: var(--accent-rose);"
                            "color:#fff; margin-top:14px; width:100%; font-weight:600;"
                            "border-radius:10px; padding:10px;"
                        ),
                    ),
                ),
            ),
            width=300,
        ),
        ui.div(
            # ── Welcome (before first click) ──────────────────────────────
            ui.panel_conditional(
                "input.generate === 0",
                ui.div(
                    ui.h1("💗 Welcome to Zena 💗"),
                    ui.p(
                        "We're here to help first-generation and international female students "
                        "navigate preventive healthcare in the United States."
                    ),
                    ui.h3("How it works", style="color:var(--accent-rose); margin-top:28px;"),
                    ui.p(
                        "Zena uses a three-agent AI pipeline: a Profile Analyst, a "
                        "Recommendation Curator (with real-time tool calls), and a "
                        "Cultural Navigator backed by a knowledge base of country-specific "
                        "health context."
                    ),
                    ui.p(
                        "Fill in your profile on the left, then click "
                        "\"Generate My Preventive Plan\" to get your personalized "
                        "checklist, action plan, and culturally-aware guidance."
                    ),
                    ui.output_ui("welcome_gate_hint"),
                    class_="welcome-section",
                ),
            ),
            # ── Results (after click) ─────────────────────────────────────
            ui.panel_conditional(
                "input.generate > 0",

                # Agent pipeline indicator
                ui.div(
                    ui.h4("💗 AI Agent Pipeline"),
                    ui.div(
                        ui.span("🔍 Agent 1: Profile Analyst", class_="agent-badge"),
                        ui.span("→", class_="agent-arrow"),
                        ui.span("🛠 Agent 2: Recommendation Curator", class_="agent-badge"),
                        ui.span("→", class_="agent-arrow"),
                        ui.span("🌍 Agent 3: Cultural Navigator", class_="agent-badge"),
                        class_="agent-strip",
                    ),
                    ui.output_ui("profile_preview_ui"),
                    class_="zena-card",
                ),

                # Value metrics + charts (App V1 analytics, enhanced)
                ui.div(
                    ui.span("Analytics", class_="section-tag"),
                    ui.h4("📊 Your recommendation snapshot"),
                    ui.output_ui("stats_row_ui"),
                    ui.div(
                        ui.div(
                            ui.h5("By category"),
                            ui.output_plot("category_plot", height=260),
                            class_="plot-card",
                        ),
                        ui.div(
                            ui.h5("By priority"),
                            ui.output_plot("priority_plot", height=260),
                            class_="plot-card",
                        ),
                        class_="plot-row",
                    ),
                    class_="zena-card",
                ),

                # Rubric: explicit agent + tool + RAG transparency
                ui.div(
                    ui.span("Agentic orchestration", class_="section-tag"),
                    ui.h4("🤖 Multi-agent workflow"),
                    ui.p(
                        "Three coordinated agents run in sequence. Outputs below are woven into "
                        "your checklist, action plan, and cultural guidance.",
                        style="font-size:13px;color:#666;margin-bottom:12px;",
                    ),
                    ui.output_ui("agent_roles_ui"),
                    class_="zena-card",
                ),
                ui.div(
                    ui.span("Tool calling", class_="section-tag"),
                    ui.h4("🛠 External tool: MyHealthfinder API"),
                    ui.output_ui("tools_detail_ui"),
                    class_="zena-card",
                ),
                ui.div(
                    ui.span("RAG", class_="section-tag"),
                    ui.h4("📚 Retrieved knowledge-base context"),
                    ui.p(
                        "Snippets come from a curated SQLite store (data/zena_rag.db), filtered by "
                        "your country plus general U.S. system notes. They are passed to the LLM as "
                        "context for Agent 3.",
                        style="font-size:13px;color:#666;margin-bottom:10px;",
                    ),
                    ui.output_ui("rag_chunks_ui"),
                    class_="zena-card",
                ),

                # Checklist (FIX: checkboxes replace DataTable selection)
                ui.div(
                    ui.h4("💗 Your Preventive Checklist"),
                    ui.div(
                        ui.div(ui.output_text("readiness_score"), class_="score-circle"),
                        ui.div("Preventive Readiness Score", class_="score-label"),
                        class_="score-wrap",
                    ),
                    ui.p(
                        "Check off items as you complete them to track your score.",
                        style="font-size:13px; color:#999; margin-bottom:10px;",
                    ),
                    ui.output_ui("checklist_ui"),
                    ui.download_button(
                        "download_btn", "📥 Download Checklist",
                        style="margin-top:12px;",
                    ),
                    class_="zena-card",
                ),

                # Action plan + cultural guidance
                ui.div(
                    ui.h4("💗 Your Personalized Action Plan"),
                    ui.output_ui("action_plan_ui"),
                    class_="zena-card",
                ),
                ui.div(
                    ui.h4("🌍 Cultural Health Guidance"),
                    ui.output_ui("cultural_guidance_ui"),
                    class_="zena-card",
                ),

                # Myth vs Fact quiz
                ui.div(
                    ui.h4("💗 Myth vs Fact Quiz"),
                    ui.p("Test your knowledge!", style="font-size:14px; color:#666; margin-bottom:10px;"),
                    ui.div(
                        ui.output_ui("quiz_statement_ui"),
                        ui.div(
                            ui.input_action_button(
                                "quiz_myth", "❌ Myth",
                                style="background:#ffcdd2; border-color:#ef9a9a;",
                            ),
                            ui.input_action_button(
                                "quiz_fact", "✅ Fact",
                                style="background:#c8e6c9; border-color:#a5d6a7;",
                            ),
                            ui.input_action_button(
                                "quiz_next", "➡️ Next",
                                style="background:var(--primary-pink); border-color:var(--primary-pink); color:#fff;",
                            ),
                            class_="quiz-buttons",
                        ),
                        ui.output_ui("quiz_feedback"),
                        class_="quiz-card",
                    ),
                    class_="zena-card",
                ),
            ),
            class_="main-content",
        ),
    ),
)


# ─────────────────────────────────────────────────────────────────────────────
# Server
# ─────────────────────────────────────────────────────────────────────────────
def server(input: Inputs, output: Outputs, session: Session) -> None:

    _unlocked = reactive.Value(not bool(_PASSWORD))

    @reactive.Effect
    @reactive.event(input.gate_submit)
    def _gate_unlock():
        if not _PASSWORD:
            return
        if input.gate_pw() == _PASSWORD:
            _unlocked.set(True)

    @render.text
    def zena_need_gate():
        _unlocked()
        return "1" if _PASSWORD and not _unlocked() else "0"

    @render.text
    def gate_feedback_text():
        if not _PASSWORD:
            return ""
        if _unlocked():
            return "✓ Unlocked. Use your profile below."
        if input.gate_submit() == 0:
            return ""
        return "Incorrect password — try again."

    @render.ui
    def welcome_gate_hint():
        if not _PASSWORD:
            return ui.div()
        return ui.p(
            "If the sidebar shows an Access form, enter the team password there first.",
            style="font-size:13px;color:#888;margin-top:12px;",
        )

    # ── Fetch API data + run agent pipeline on Generate click ─────────────

    @reactive.calc
    @reactive.event(input.generate)
    def api_df() -> pd.DataFrame | None:
        """Fetch MyHealthFinder data and convert to DataFrame."""
        try:
            data = fetch_myhealthfinder(
                age=int(input.age()),
                sex="female",
                pregnant="no",
                sexually_active="yes",
                tobacco_use="no",
            )
        except Exception:
            return None
        if not data or "Result" not in data:
            return None
        recs = (
            data["Result"]
            .get("Resources", {})
            .get("All", {})
            .get("Resource")
        )
        if not recs:
            return None
        if isinstance(recs, dict):
            recs = [recs]
        completed = list(input.vaccines()) if input.vaccines() else []
        unsure_list = ["unsure"] if input.unsure() else []
        try:
            return process_recommendations(recs, completed, unsure_list)
        except Exception:
            return None

    @reactive.calc
    @reactive.event(input.generate)
    def agent_results() -> dict:
        """Run the three-agent pipeline. Returns unified results dict."""
        df = api_df()
        raw = []
        if df is not None and not df.empty:
            raw = df[["title", "category", "priority"]].to_dict("records")

        return orchestrate_health_plan(
            age=int(input.age()),
            country=str(input.country()),
            vaccines=list(input.vaccines()) if input.vaccines() else [],
            insurance=str(input.insurance()),
            unsure=bool(input.unsure()),
            raw_recommendations=raw,
        )

    # ── Analytics + AI transparency (App V2) ────────────────────────────────

    @render.ui
    def stats_row_ui():
        if input.generate() == 0:
            return ui.div()
        df = api_df()
        if df is None or df.empty:
            return ui.div()
        n = len(df)
        high = int((df["priority"] == "High").sum()) if "priority" in df.columns else 0
        n_cat = int(df["category"].nunique()) if "category" in df.columns else 0
        return ui.div(
            ui.div(
                ui.div(str(n), class_="stat-num"),
                ui.div("Filtered recommendations", class_="stat-lbl"),
                class_="stat-box",
            ),
            ui.div(
                ui.div(str(n_cat), class_="stat-num"),
                ui.div("Topic categories", class_="stat-lbl"),
                class_="stat-box",
            ),
            ui.div(
                ui.div(str(high), class_="stat-num"),
                ui.div("High priority items", class_="stat-lbl"),
                class_="stat-box",
            ),
            class_="stat-row",
        )

    @render.plot
    def category_plot():
        if input.generate() == 0:
            fig, ax = plt.subplots(figsize=(4.2, 3))
            ax.axis("off")
            return fig
        df = api_df()
        fig, ax = plt.subplots(figsize=(4.2, 3))
        if df is None or df.empty or "category" not in df.columns:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=12)
            ax.axis("off")
            return fig
        counts = df.groupby("category").size().sort_values(ascending=True)
        colors = plt.cm.RdPu(0.35 + 0.45 * (counts / max(counts.max(), 1)))
        counts.plot(kind="barh", ax=ax, color=colors)
        ax.set_xlabel("Count")
        ax.set_ylabel("")
        fig.tight_layout()
        return fig

    @render.plot
    def priority_plot():
        if input.generate() == 0:
            fig, ax = plt.subplots(figsize=(4.2, 3))
            ax.axis("off")
            return fig
        df = api_df()
        fig, ax = plt.subplots(figsize=(4.2, 3))
        if df is None or df.empty or "priority" not in df.columns:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=12)
            ax.axis("off")
            return fig
        pr = df.groupby("priority").size()
        order = ["High", "Routine", "Informational"]
        pr = pr.reindex([x for x in order if x in pr.index] + [x for x in pr.index if x not in order])
        palette = {"High": "#EC407A", "Routine": "#F48FB1", "Informational": "#e0e0e0"}
        colors = [palette.get(i, "#ce93d8") for i in pr.index]
        ax.pie(pr.values, labels=pr.index, autopct="%1.0f%%", colors=colors, startangle=90)
        ax.axis("equal")
        fig.tight_layout()
        return fig

    @render.ui
    def agent_roles_ui():
        if input.generate() == 0:
            return ui.div()
        res = agent_results()
        meta = res.get("pipeline_meta") or {}
        blocks = []
        for a in meta.get("agents", []):
            blocks.append(
                ui.div(
                    ui.tags.strong(f"Agent {a.get('id')}: {a.get('name')}"),
                    ui.p(a.get("role", ""), style="font-size:13px;margin:8px 0 0;color:#555;"),
                    class_="agent-info-card",
                )
            )
        return ui.div(*blocks) if blocks else ui.p("—", class_="text-muted")

    @render.ui
    def tools_detail_ui():
        if input.generate() == 0:
            return ui.div()
        res = agent_results()
        tools = (res.get("pipeline_meta") or {}).get("tools", [])
        if not tools:
            return ui.p("No tool metadata.", class_="text-muted")
        t = tools[0]
        params = t.get("parameters") or {}
        param_rows = "".join(
            f"<tr><td><code>{k}</code></td><td>{v}</td></tr>" for k, v in params.items()
        )
        return ui.HTML(
            f"<p style='font-size:13px;color:#555;margin:0 0 8px;'>"
            f"<b>{t.get('name', 'tool')}</b> — {t.get('purpose', '')}</p>"
            f"<p style='font-size:12px;'><b>Endpoint:</b> <code style='word-break:break-all;'>"
            f"{t.get('endpoint', '')}</code></p>"
            f"<p style='font-size:13px;'><b>Recommendations after filtering:</b> "
            f"{t.get('recommendations_after_filter', '—')}</p>"
            f"<table class='tool-table'><thead><tr><th>Parameter</th><th>Value</th></tr></thead>"
            f"<tbody>{param_rows}</tbody></table>"
        )

    @render.ui
    def rag_chunks_ui():
        if input.generate() == 0:
            return ui.div()
        res = agent_results()
        chunks = res.get("rag_chunks") or []
        if not chunks:
            return ui.p("No RAG chunks returned.", class_="text-muted")
        return ui.div(
            *[
                ui.div(
                    ui.tags.small(f"Snippet {i + 1}", style="color:#999;display:block;margin-bottom:6px;"),
                    c[:1200] + ("…" if len(c) > 1200 else ""),
                    class_="snippet-card",
                )
                for i, c in enumerate(chunks)
            ]
        )

    # ── Checkbox tracking (FIX for readiness score) ───────────────────────

    _checked: reactive.Value[set[str]] = reactive.Value(set())

    @reactive.Effect
    @reactive.event(input.generate)
    def _reset_checked():
        _checked.set(set())

    # ── Render: profile preview ───────────────────────────────────────────

    @render.ui
    def profile_preview_ui():
        res = agent_results()
        profile = res.get("profile", {})
        lines = []
        for k, v in profile.items():
            val = ", ".join(v) if isinstance(v, list) else str(v)
            lines.append(f"<b>{k}:</b> {val}")
        return ui.HTML(
            "<div class='profile-preview'>"
            + "<br>".join(lines)
            + "</div>"
        )

    # ── Render: checklist (checkbox cards) ───────────────────────────────

    @render.ui
    def checklist_ui():
        df = api_df()
        if df is None or df.empty:
            return ui.p(
                "Could not load recommendations. Please try again.",
                style="color:#999; text-align:center; padding:24px;",
            )
        checked = _checked()
        items = []
        for i, row in df.iterrows():
            key = f"chk_{i}"
            priority = row.get("priority", "Informational")
            is_checked = key in checked
            item = ui.div(
                ui.input_checkbox(key, "", value=is_checked),
                ui.div(
                    ui.div(row["title"], class_="item-title"),
                    ui.div(row.get("category", ""), class_="item-cat"),
                ),
                ui.span(priority, class_=f"badge badge-{priority}"),
                class_=f"check-item priority-{priority}",
            )
            items.append(item)
        return ui.div(*items)

    # Listen for any checkbox changes
    @reactive.Effect
    def _watch_checkboxes():
        df = api_df()
        if df is None or df.empty:
            return
        for i in range(len(df)):
            key = f"chk_{i}"
            val = input[key]()
            cur = set(_checked())
            if val and key not in cur:
                cur.add(key)
                _checked.set(cur)
            elif not val and key in cur:
                cur.discard(key)
                _checked.set(cur)

    # ── Render: readiness score ───────────────────────────────────────────

    @render.text
    def readiness_score():
        df = api_df()
        if df is None or df.empty:
            return "0%"
        total = len(df)
        checked = len(_checked())
        return f"{int(checked / total * 100)}%" if total else "0%"

    # ── Render: action plan ───────────────────────────────────────────────

    @render.ui
    def action_plan_ui():
        res = agent_results()
        plan = res.get("action_plan", "")
        if not plan:
            return ui.p("Generating your plan…", style="color:#aaa;")
        # Split on bullet lines if present, otherwise show as paragraph
        lines = [l.strip() for l in plan.split("\n") if l.strip()]
        paras = [ui.p(l, style="margin-bottom:8px;") for l in lines]
        return ui.div(*paras)

    # ── Render: cultural guidance ─────────────────────────────────────────

    @render.ui
    def cultural_guidance_ui():
        res = agent_results()
        guidance = res.get("cultural_guidance", "")
        if not guidance:
            return ui.p("Generating cultural guidance…", style="color:#aaa;")
        paras = [
            ui.p(p.strip(), style="margin-bottom:10px; line-height:1.65;")
            for p in guidance.split("\n\n")
            if p.strip()
        ]
        return ui.div(*paras)

    # ── Quiz ──────────────────────────────────────────────────────────────

    _quiz_q: reactive.Value[tuple[str, bool]] = reactive.Value(
        random.choice(MYTH_FACT_QUIZ)
    )
    _user_ans: reactive.Value[bool | None] = reactive.Value(None)

    @reactive.Effect
    @reactive.event(input.generate)
    def _init_quiz():
        _quiz_q.set(random.choice(MYTH_FACT_QUIZ))
        _user_ans.set(None)

    @reactive.Effect
    @reactive.event(input.quiz_myth)
    def _myth():
        _user_ans.set(False)

    @reactive.Effect
    @reactive.event(input.quiz_fact)
    def _fact():
        _user_ans.set(True)

    @reactive.Effect
    @reactive.event(input.quiz_next)
    def _next():
        _user_ans.set(None)
        _quiz_q.set(random.choice(MYTH_FACT_QUIZ))

    @render.ui
    def quiz_statement_ui():
        statement, _ = _quiz_q()
        return ui.div(statement, class_="quiz-statement")

    @render.ui
    def quiz_feedback():
        ans = _user_ans()
        if ans is None:
            return ui.div()
        _, is_fact = _quiz_q()
        correct = ans == is_fact
        msg = "Correct! 💗" if correct else f"Not quite — it's a {'Fact ✅' if is_fact else 'Myth ❌'}."
        return ui.div(
            msg,
            class_=f"quiz-result {'quiz-correct' if correct else 'quiz-wrong'}",
        )

    # ── Download ──────────────────────────────────────────────────────────

    @render.download(filename="zena_checklist.csv")
    def download_btn():
        df = api_df()
        if df is None or df.empty:
            yield "Recommendation,Category,Priority\nNo data yet.\n"
            return
        buf = StringIO()
        df[["title", "category", "priority"]].to_csv(
            buf, index=False, header=["Recommendation", "Category", "Priority"]
        )
        yield buf.getvalue()


app = App(app_ui, server)
