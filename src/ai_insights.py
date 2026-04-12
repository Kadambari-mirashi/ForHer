"""
Ollama LLM Integration - Text simplification, cultural context, summaries.
Uses Ollama Cloud (gpt-oss:120b) or local. Caches outputs for efficiency.
"""

import hashlib
import os
import re
import requests

# Simple in-memory cache (per session)
_llm_cache: dict[str, str] = {}


def _call_ollama(prompt: str, cache_key: str | None = None) -> str:
    """Call Ollama API with low temperature. Uses cache if key provided."""
    if cache_key and cache_key in _llm_cache:
        return _llm_cache[cache_key]

    api_key = os.getenv("OLLAMA_API_KEY")
    model = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")  # Cloud model default
    if api_key:
        base_url = os.getenv("OLLAMA_HOST", "https://ollama.com")
        headers = {"Authorization": f"Bearer {api_key}"}
    else:
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        headers = {}
        model = os.getenv("OLLAMA_MODEL", "llama3.2")

    try:
        r = requests.post(
            f"{base_url.rstrip('/')}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.4, "num_predict": 350},
            },
            headers=headers,
            timeout=90,
        )
        r.raise_for_status()
        data = r.json()
        content = data.get("message", {}).get("content", "").strip() or "Unable to generate."
        # Remove hyphen-like chars and bullet dashes (e.g. " - item" -> " item")
        content = content.replace("\u2011", "").replace("\u2013", " ").replace("\u2014", " ")
        content = re.sub(r"\n\s*[-–—]\s*", "\n• ", content)  # line-start dashes to bullet
        content = re.sub(r"^\s*[-–—]\s*", "• ", content)
        if cache_key:
            _llm_cache[cache_key] = content
        return content
    except requests.exceptions.ConnectionError:
        return "Ollama unavailable. Start local Ollama or set OLLAMA_API_KEY for cloud."
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 404:
            return "Model not found. For Ollama Cloud, set OLLAMA_MODEL=gpt-oss:120b in .env"
        return f"API error: {e}"
    except Exception as e:
        return f"Error: {e}"


def simplify_text(recommendation_text: str) -> str:
    """Rewrite in plain language at 8th-grade level. Bullet points, under 3 sentences."""
    prompt = f"""Rewrite the following preventive health recommendation in plain language at an 8th-grade reading level. Use bullet points. Keep under 3 sentences. Remove medical jargon.

{recommendation_text}"""
    key = f"simplify_{hashlib.md5(recommendation_text[:200].encode()).hexdigest()}"
    return _call_ollama(prompt, key)


def why_this_matters(title: str, age: int) -> str:
    """Explain in 1-2 sentences why this matters for the user."""
    prompt = f"""Explain in 1-2 simple sentences why this preventive recommendation is important for a {age}-year-old international student in the U.S.

Recommendation: {title}"""
    key = f"why_{hashlib.md5(f"{title}{age}".encode()).hexdigest()}"
    return _call_ollama(prompt, key)


def cultural_context() -> str:
    """How U.S. preventive care differs from countries where people only visit when sick."""
    prompt = """Briefly explain how preventive care in the U.S. may differ from other countries where people only visit doctors when sick. 2-3 sentences for international students."""
    return _call_ollama(prompt, "cultural")


def personalized_summary(recommendations_text: str, vaccination_status: list[str], age: int) -> str:
    """Short encouraging summary highlighting top priorities. Complete sentences only."""
    if not recommendations_text or not recommendations_text.strip():
        return "Based on your profile, focus on routine screenings and preventive visits. Talk to your doctor about what's right for you."
    vax = ", ".join(vaccination_status) if vaccination_status else "None specified"
    prompt = f"""Based on these preventive recommendations and vaccination status ({vax}), generate a short encouraging summary for a {age}-year-old international student. 

CRITICAL: Write ONLY complete, grammatically correct sentences. Do NOT truncate or cut off mid-sentence. Each sentence must be fully finished. Keep under 100 words. Do not use bullet points or dashes.

Recommendations:
{recommendations_text}"""
    key = f"summary_{hashlib.md5(f"{recommendations_text}{vax}{age}".encode()).hexdigest()}"
    result = _call_ollama(prompt, key)
    # Fallback if AI returns error message
    if result and ("error" in result.lower() or "unavailable" in result.lower() or "not found" in result.lower()):
        return f"Based on your age ({age}) and vaccination status, prioritize cervical cancer screening, blood pressure checks, and annual well-woman visits. These are key preventive steps for your health."
    return result


def myth_vs_fact() -> str:
    """Generate 3 myth vs fact pairs about preventive healthcare for young women in the U.S."""
    prompt = """Generate exactly 3 myth vs fact pairs about preventive healthcare for young women in the U.S. Format each as:
Myth: [myth]
Fact: [fact]

Keep each brief (1 sentence each)."""
    return _call_ollama(prompt, "mythfact")


# Predefined quiz items for reliable Myth vs Fact game (statement, is_fact)
MYTH_FACT_QUIZ = [
    ("You only need to see a doctor when you're sick.", False),
    ("Cervical cancer screening (Pap/HPV test) is recommended for women starting at age 21.", True),
    ("The flu shot can give you the flu.", False),
    ("Annual well-woman visits are recommended for preventive care.", True),
    ("HPV vaccine is only for people who are sexually active.", False),
    ("Blood pressure should be checked regularly starting at age 18.", True),
    ("You can skip vaccines if you had them as a child.", False),
    ("Mental health check-ins are part of preventive care.", True),
]
