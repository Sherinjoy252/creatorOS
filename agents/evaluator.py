import json
import re
from typing import Any

from graph.state import CreatorState
from services.ai_service import AIService


WEIGHTS = {
    "technical_accuracy": 25,
    "practical_value": 20,
    "brand_voice_alignment": 15,
    "readability": 15,
    "conciseness": 10,
    "topic_relevance": 10,
    "engagement_potential": 5,
}


def _parse_evaluation(raw: str) -> dict[str, Any]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Evaluator returned invalid JSON.") from exc

    if not isinstance(data, dict) or not isinstance(data.get("criteria"), dict):
        raise ValueError("Evaluator response must contain a criteria object.")

    criteria = {}
    weighted_total = 0.0
    for key, weight in WEIGHTS.items():
        item = data["criteria"].get(key)
        if not isinstance(item, dict):
            raise ValueError(f"Evaluator response is missing criterion: {key}")
        score = item.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= weight:
            raise ValueError(f"Invalid score for {key}; expected 0 to {weight}.")
        criteria[key] = {
            "score": round(score, 2),
            "max_score": weight,
            "feedback": str(item.get("feedback", "")).strip(),
        }
        weighted_total += score

    return {
        "score": round(weighted_total),
        "max_score": 100,
        "criteria": criteria,
        "strengths": data.get("strengths", []) if isinstance(data.get("strengths", []), list) else [],
        "improvements": data.get("improvements", []) if isinstance(data.get("improvements", []), list) else [],
        "summary": str(data.get("summary", "")).strip(),
    }


def _evaluate(state: CreatorState, stage: str) -> dict:
    prompt = f"""You are an independent quality evaluator for educational LinkedIn posts.
Evaluate the supplied draft, not the editor's approval decision. Do not rewrite it.
Do not assume factual claims or code are correct merely because they look plausible.

Stage: {stage}
Topic: {state['topic']}
Brand voice: {state['brand_voice']}
Strategic angle: {state['strategist_angle']}
Approved learning lessons: {state.get('approved_lessons', [])}

Draft:
{state['draft']}

Score each criterion using its maximum points:
- technical_accuracy: 25
- practical_value: 20
- brand_voice_alignment: 15
- readability: 15
- conciseness: 10
- topic_relevance: 10
- engagement_potential: 5

Return ONLY valid JSON. Every criterion must have a numeric score within its maximum and concise feedback.
Use this exact structure:
{{
  "criteria": {{
    "technical_accuracy": {{"score": 0, "feedback": "..."}},
    "practical_value": {{"score": 0, "feedback": "..."}},
    "brand_voice_alignment": {{"score": 0, "feedback": "..."}},
    "readability": {{"score": 0, "feedback": "..."}},
    "conciseness": {{"score": 0, "feedback": "..."}},
    "topic_relevance": {{"score": 0, "feedback": "..."}},
    "engagement_potential": {{"score": 0, "feedback": "..."}}
  }},
  "strengths": ["..."],
  "improvements": ["..."],
  "summary": "..."
}}
"""
    raw = AIService().generate_text(prompt)
    evaluation = _parse_evaluation(raw)
    audit = state.get("audit_trail", [])
    label = "Initial" if stage == "initial" else "Final"
    return {
        f"{stage}_evaluation": evaluation,
        "audit_trail": audit + [f"{label} self-evaluation score: {evaluation['score']}/100."],
    }


def initial_evaluator_node(state: CreatorState) -> dict:
    # The writer runs again during revisions; preserve the original baseline score.
    if state.get("initial_evaluation") is not None:
        return {}
    return _evaluate(state, "initial")


def final_evaluator_node(state: CreatorState) -> dict:
    result = _evaluate(state, "final")
    initial_score = (state.get("initial_evaluation") or {}).get("score")
    final_score = result["final_evaluation"]["score"]
    delta = final_score - initial_score if isinstance(initial_score, int) else 0
    result["evaluation_score_delta"] = delta
    result["audit_trail"] = result["audit_trail"] + [
        f"Self-evaluation score change after editing: {delta:+d} points."
    ]
    return result
