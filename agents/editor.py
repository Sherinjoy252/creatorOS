from graph.state import CreatorState
from services.ai_service import AIService
import re


def _format_initial_priorities(state: CreatorState) -> str:
    priorities = state.get("revision_priorities", [])
    if not priorities:
        return "No specific initial-evaluation priorities were recorded."

    return "\n".join(f"- {priority}" for priority in priorities)


def editor_node(state: CreatorState) -> dict:
    ai = AIService()

    initial_evaluation = state.get("initial_evaluation") or {}
    initial_score = initial_evaluation.get("score", "unavailable")
    revision_priorities = _format_initial_priorities(state)

    prompt = f"""
You are a strict editor reviewing educational LinkedIn posts.

Topic: {state['topic']}
Brand voice: {state['brand_voice']}
Strategic angle: {state['strategist_angle']}

Initial self-evaluation score: {initial_score}/100

Initial evaluation revision priorities:
{revision_priorities}

Draft:
{state['draft']}

Evaluate the draft critically. Do not trust claims in the draft
without checking their correctness.

Mandatory checks:
1. Technical accuracy: Flag incorrect or misleading explanations.
2. Code correctness: Verify that the example demonstrates what
   the surrounding text claims. For resource handling, ensure the
   code actually closes resources or uses try-with-resources.
3. Practical value: Include a useful, correct example where relevant.
4. Brand voice: Follow the supplied brand voice.
5. Conciseness: Remove repetitive explanations, introductions,
   conclusions, headings, and calls to action.
6. Professional tone: Remove unnecessary emojis and generic
   motivational language.
7. Ending: Use one concise conclusion and at most one call to action.
8. Topic alignment: Verify that the example directly demonstrates
   the requested topic, not merely a related concept.
9. Independent review: Evaluate the current draft against all original
   requirements. Do not approve it simply because it addressed previous feedback.

When revising, explicitly check each initial-evaluation priority:
- Confirm whether the weakness is genuinely present in the current draft.
- Require a correction when it is valid and relevant.
- Preserve content that already performs well.
- Do not add unnecessary detail or make unrelated changes just to increase a score.

Prefer 150-300 words unless more detail is necessary.

REVISE if any mandatory check fails or a valid high-priority weakness remains.
Do not approve a draft just because it is readable, relevant, or well formatted.

For REVISE, list the specific errors and required changes.
For APPROVE, explain briefly why the draft passes the checks.

Return exactly this structure:
VERDICT: APPROVE
FEEDBACK: Explain why the draft meets the criteria.

Or:
VERDICT: REVISE
FEEDBACK: List the specific problems and required changes.
"""

    result = ai.generate_text(prompt).strip()

    # Accept plain labels, Markdown headings, and bold Markdown labels.
    # Keep the regex deliberately simple to avoid invalid nested quantifiers.
    verdict_match = re.search(
        r"^\s*#{0,6}\s*\*{0,2}\s*VERDICT\s*:\s*\*{0,2}\s*(APPROVE|REVISE)\b.*$",
        result,
        re.IGNORECASE | re.MULTILINE,
    )

    feedback_start = re.search(
        r"^\s*#{0,6}\s*\*{0,2}\s*FEEDBACK\s*:\s*\*{0,2}\s*",
        result,
        re.IGNORECASE | re.MULTILINE,
    )

    if not verdict_match or not feedback_start:
        raise ValueError(f"Editor response format invalid: {result[:300]!r}")

    verdict = verdict_match.group(1).upper()
    feedback = result[feedback_start.end():].strip()

    if not feedback:
        raise ValueError("Editor returned empty feedback.")

    approved = verdict == "APPROVE"

    return {
        "approved": approved,
        "critique": feedback,
        "audit_trail": state["audit_trail"] + [
            f"Editor verdict: {verdict}",
            f"Editor feedback: {feedback}",
        ],
    }
