"""
Multi-agent orchestration for Zena V2: profile → recommendations → cultural guidance.
Uses MyHealthFinder-derived recs, optional Ollama, and RAG cultural snippets.
"""

from __future__ import annotations

import hashlib
from typing import Any

from src.ai_insights import _call_ollama, personalized_summary
from src.rag import retrieve_chunks_for_country

_FALLBACK_PLAN = (
    "Based on your profile, prioritize staying current on recommended vaccines, scheduling an "
    "annual well-woman visit if appropriate for your age, and following screening guidance "
    "your clinician gives you. Ask your campus or community clinic what is covered under your plan."
)
_FALLBACK_CULTURAL = (
    "In the U.S., preventive care is encouraged even when you feel healthy. This can differ "
    "from systems where people mainly see doctors when sick. Campus health and primary care "
    "can help you build a routine that fits your needs."
)

_ERROR_MARKERS = ("error:", "unavailable", "not found", "unable to generate", "api error:")


def _usable(text: str | None) -> bool:
    if not text or not str(text).strip():
        return False
    lower = str(text).lower()
    return not any(m in lower for m in _ERROR_MARKERS)


def _recs_to_summary_input(raw: list[dict[str, Any]], max_items: int = 8) -> str:
    lines = []
    for r in raw[:max_items]:
        title = r.get("title", "")
        cat = r.get("category", "")
        pri = r.get("priority", "")
        lines.append(f"- {title} ({cat}, priority: {pri})")
    return "\n".join(lines)


def orchestrate_health_plan(
    *,
    age: int,
    country: str,
    vaccines: list[str],
    insurance: str,
    unsure: bool,
    raw_recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Agent 1: structured profile.
    Agent 2: action plan from recommendations + demographics (LLM).
    Agent 3: cultural guidance using country + RAG retrieval (LLM).
    """
    vax_list = list(vaccines) if vaccines else []
    profile: dict[str, Any] = {
        "age": age,
        "country_of_origin": country,
        "vaccines_completed": vax_list if vax_list else ["none specified"],
        "insurance": insurance,
        "unsure_about_vaccines": unsure,
        "recommendation_count": len(raw_recommendations),
    }

    rec_text = _recs_to_summary_input(raw_recommendations)
    if not rec_text.strip():
        rec_text = (
            "(No API items after filtering—suggest annual preventive visit and vaccine review.)"
        )

    # Agent 2 — reuse personalized_summary; extended via cache key with country/insurance
    cache_extra = f"{country}|{insurance}|{unsure}|{rec_text[:400]}"
    summary_key = hashlib.md5(
        f"{age}|{vax_list}|{cache_extra}".encode()
    ).hexdigest()
    plan_prompt = f"""You are a preventive-care educator (not a doctor). Write a short, encouraging
action plan for a {age}-year-old female international or first-gen student in the U.S.

Country of origin: {country}. Insurance: {insurance}. Vaccines completed: {", ".join(vax_list) or "none specified"}.
Unsure about some vaccine history: {"yes" if unsure else "no"}.

Use ONLY these recommendation lines from a trusted U.S. API (MyHealthFinder):
{rec_text}

Rules: 3-6 short bullet lines starting with "• ". Plain English. No diagnosis. Mention seeing a
clinician for personal decisions. Reference their situation (age, country, vaccines) where natural.
"""
    action_plan = _call_ollama(plan_prompt, f"zena_plan_{summary_key}")
    if not _usable(action_plan):
        action_plan = personalized_summary(rec_text, vax_list, age)
    if not _usable(action_plan):
        action_plan = _FALLBACK_PLAN

    # Agent 3 — RAG + country-specific cultural navigator
    rag_chunks = retrieve_chunks_for_country(country, limit=6)
    rag_context = "\n\n".join(rag_chunks)
    cult_key = hashlib.md5(f"{country}|{rag_context[:500]}".encode()).hexdigest()
    cultural_prompt = f"""You are a supportive cultural navigator for health (not medical advice).

Student is from: {country}. Age {age}. They are learning U.S. preventive care.

Use this knowledge-base context about U.S. care and common adjustment points:
---
{rag_context}
---

Write 2-4 short paragraphs (plain text, blank line between paragraphs). Help them understand
how U.S. preventive care might feel different from norms they grew up with, without stereotyping.
Be warm and practical. Do not give diagnoses or medication advice.
"""
    cultural_guidance = _call_ollama(cultural_prompt, f"zena_cult_{cult_key}")
    if not _usable(cultural_guidance):
        cultural_guidance = _FALLBACK_CULTURAL

    return {
        "profile": profile,
        "action_plan": action_plan.strip(),
        "cultural_guidance": cultural_guidance.strip(),
        "rag_snippets_used": rag_context[:800],
        "rag_chunks": rag_chunks,
        "pipeline_meta": {
            "agents": [
                {
                    "id": 1,
                    "name": "Profile Analyst",
                    "role": "Structures age, country, vaccines, insurance, and API metadata into a single profile object for downstream agents.",
                },
                {
                    "id": 2,
                    "name": "Recommendation Curator",
                    "role": "Turns MyHealthfinder recommendation lines into a concise bullet action plan using the LLM; falls back to rule-based text if needed.",
                },
                {
                    "id": 3,
                    "name": "Cultural Navigator",
                    "role": "Retrieves country-specific context from the local knowledge base (RAG), then asks the LLM to explain U.S. preventive care norms without stereotyping.",
                },
            ],
            "tools": [
                {
                    "name": "fetch_myhealthfinder",
                    "purpose": "HTTP GET to U.S. HHS MyHealthfinder — age/sex-specific preventive care topics.",
                    "endpoint": "https://odphp.health.gov/myhealthfinder/api/v4/myhealthfinder.json",
                    "parameters": {
                        "age": age,
                        "sex": "female",
                        "pregnant": "no",
                        "sexually_active": "yes",
                        "tobacco_use": "no",
                    },
                    "recommendations_after_filter": len(raw_recommendations),
                }
            ],
            "rag": {
                "store": "SQLite (data/zena_rag.db, table chunks)",
                "search": f"country = '{country}' OR General snippets",
                "chunks_returned": len(rag_chunks),
            },
        },
    }
