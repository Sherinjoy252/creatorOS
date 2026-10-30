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


def _build_revision_priorities(evaluation: dict[str, Any]) -> list[str]:
    """Select up to three weakest criteria as focused revision targets."""
    criteria = evaluation.get("criteria", {})
    ranked = []

    for key, item in criteria.items():
        max_score = item.get("max_score", WEIGHTS.get(key, 0))
        score = item.get("score", 0)
        if max_score <= 0:
            continue
        ratio = score / max_score
        ranked.append((ratio, key, score, max_score, item.get("feedback", "")))

    ranked.sort(key=lambda entry: (entry[0], entry[1]))
    below_target = [entry for entry in ranked if entry[0] < 0.85]
    selected = (below_target or ranked)[:3]

    return [
        (
            f"{key} ({score:g}/{max_score}): {feedback or 'Improve this criterion.'} "
            "Address this weakness in the revision while preserving already-strong content."
        )
        for _, key, score, max_score, feedback in selected
    ]


def _build_comparison(
    initial: dict[str, Any] | None,
    final: dict[str, Any],
) -> dict[str, Any]:
    if not initial:
        return {
            "available": False,
            "message": "Initial evaluation is unavailable; a criterion-by-criterion comparison could not be made.",
            "improvements": [],
            "regressions": [],
            "unresolved_weaknesses": [],
            "criterion_changes": [],
        }

    initial_criteria = initial.get("criteria", {})
    final_criteria = final.get("criteria", {})
    changes = []
    improvements = []
    regressions = []
    unresolved = []

    for key, weight in WEIGHTS.items():
        before = initial_criteria.get(key, {}).get("score")
        after = final_criteria.get(key, {}).get("score")
        if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
            continue

        delta = round(after - before, 2)
        entry = {
            "criterion": key,
            "initial_score": before,
            "final_score": after,
            "max_score": weight,
            "change": delta,
        }
        changes.append(entry)

        if delta > 0:
            improvements.append(entry)
        elif delta < 0:
            regressions.append(entry)

        if after / weight < 0.85:
            unresolved.append({
                **entry,
                "feedback": final_criteria.get(key, {}).get("feedback", ""),
            })

    initial_score = initial.get("score", 0)
    final_score = final.get("score", 0)
    overall_delta = final_score - initial_score

    return {
        "available": True,
        "initial_score": initial_score,
        "final_score": final_score,
        "overall_change": overall_delta,
        "quality_warning": overall_delta < 0 or bool(regressions),
        "improvements": improvements,
        "regressions": regressions,
        "unresolved_weaknesses": unresolved,
        "criterion_changes": changes,
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

Use the same rubric and scoring standards at both evaluation stages.
Score only the draft currently supplied. Be consistent, evidence-based, and avoid rewarding
or penalizing the draft merely because it is an initial or revised version.

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

    result = _evaluate(state, "initial")
    evaluation = result["initial_evaluation"]
    priorities = _build_revision_priorities(evaluation)
    result["revision_priorities"] = priorities
    result["audit_trail"] = result["audit_trail"] + [
        f"Evaluator identified {len(priorities)} focused revision priorities."
    ]
    return result


def final_evaluator_node(state: CreatorState) -> dict:
    result = _evaluate(state, "final")
    initial_evaluation = state.get("initial_evaluation")
    final_evaluation = result["final_evaluation"]

    comparison = _build_comparison(initial_evaluation, final_evaluation)
    final_evaluation["comparison"] = comparison

    initial_score = (initial_evaluation or {}).get("score")
    final_score = final_evaluation["score"]
    delta = final_score - initial_score if isinstance(initial_score, int) else 0
    result["evaluation_score_delta"] = delta

    if comparison.get("quality_warning"):
        warning = (
            "Quality warning: final evaluation is lower than the initial evaluation "
            "or one or more criteria regressed. Review the comparison before publishing."
        )
    else:
        warning = "No overall score decrease or criterion regression detected."

    result["audit_trail"] = result["audit_trail"] + [
        f"Self-evaluation score change after editing: {delta:+d} points.",
        warning,
    ]
    return result
