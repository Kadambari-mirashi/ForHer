"""
Lightweight RAG store: SQLite cultural health context by country of origin.
Educational snippets only—not medical advice.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "zena_rag.db"

# Curated notes (U.S. system vs norms students may know). General + per-country.
_GENERAL = [
    (
        "General",
        "In the U.S., preventive care—screenings and vaccines before symptoms—is standard "
        "and often fully covered when you use in-network providers and meet ACA rules.",
    ),
    (
        "General",
        "Campus health centers and student insurance usually emphasize confidentiality; "
        "ask what stays on your record and what requires parental notification if you are under 18.",
    ),
    (
        "General",
        "If English is not your first language, you can request an interpreter at many "
        "clinics and hospitals at no cost to you.",
    ),
]

_COUNTRY_SNIPPETS: dict[str, list[str]] = {
    "India": [
        "Family involvement in health decisions is common in India; in the U.S. you typically "
        "consent for your own care as an adult student—clinicians may ask you privately what you want.",
        "Ayurvedic or home remedies are widely used at home; tell your U.S. clinician everything "
        "you take so they can check interactions with prescriptions.",
    ],
    "China": [
        "In China, hospital-based care is common; in the U.S. many students first see a primary "
        "care or campus clinician for referrals—this gatekeeping can feel slow but is normal.",
    ],
    "Mexico": [
        "Preventive visits may have been less routine than in the U.S.; annual well-woman visits "
        "and covered screenings are a key way to stay on track here.",
    ],
    "South Korea": [
        "Korea has strong screening culture in some settings; still align with U.S. guidelines "
        "(ages and intervals) since your student plan follows local rules.",
    ],
    "Vietnam": [
        "Traditional medicine may be part of wellness at home; disclose herbs and teas to U.S. "
        "providers because some affect blood pressure or bleeding risk.",
    ],
    "Nigeria": [
        "Religious and community norms may shape health discussions; U.S. clinicians are trained "
        "to offer non-judgmental care—ask questions if something feels unclear.",
    ],
    "Brazil": [
        "Public SUS vs. private care differs from U.S. insurance tiers; learn your plan’s "
        "deductible, copay, and in-network list early in the semester.",
    ],
    "Philippines": [
        "Extended family often supports health choices; as an adult in the U.S., you choose "
        "whether to involve relatives in appointments.",
    ],
    "Pakistan": [
        "Modesty and gender of the clinician may matter; you can request a female provider when "
        "scheduling—availability varies by clinic.",
    ],
    "Bangladesh": [
        "Cash pay at home vs. insurance billing in the U.S. is different; keep insurance cards "
        "and know the campus health fee vs. what insurance covers.",
    ],
    "United States": [
        "U.S. students often use campus health first; for specialty care you may need a referral "
        "depending on your plan.",
    ],
}


def init_rag_db() -> None:
    """Create SQLite DB and seed rows if empty."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT NOT NULL,
                content TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chunks_country ON chunks(country)"
        )
        (n,) = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
        if n == 0:
            rows: list[tuple[str, str]] = list(_GENERAL)
            for country, snippets in _COUNTRY_SNIPPETS.items():
                for text in snippets:
                    rows.append((country, text))
            conn.executemany(
                "INSERT INTO chunks (country, content) VALUES (?, ?)", rows
            )
            conn.commit()
    finally:
        conn.close()


def retrieve_chunks_for_country(country: str, limit: int = 6) -> list[str]:
    """Return ordered snippet texts used as RAG context (for UI + prompting)."""
    init_rag_db()
    conn = sqlite3.connect(_DB_PATH)
    try:
        cur = conn.execute(
            """
            SELECT content FROM chunks
            WHERE country = ? OR country = 'General'
            ORDER BY CASE WHEN country = ? THEN 0 ELSE 1 END, id
            LIMIT ?
            """,
            (country, country, limit),
        )
        parts = [row[0] for row in cur.fetchall()]
    finally:
        conn.close()
    if not parts and country not in _COUNTRY_SNIPPETS:
        parts = [
            f"Students from {country} may find U.S. emphasis on preventive visits and insurance "
            "paperwork unfamiliar—campus international student offices often run workshops on this."
        ]
    return parts


def retrieve_for_country(country: str, limit: int = 6) -> str:
    """Return concatenated context snippets for RAG-style prompting."""
    return "\n\n".join(retrieve_chunks_for_country(country, limit))
