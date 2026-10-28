
from graph.state import CreatorState
from services.ai_service import AIService


def strategist_node(state: CreatorState) -> dict:
    ai = AIService()

    
    approved_lessons = state.get("approved_lessons", [])

    lessons_context = (
        "\n".join(f"- {lesson}" for lesson in approved_lessons)
        if approved_lessons
        else "No approved performance lessons are available yet."
    )

    prompt = f"""
You are the content strategist for a LinkedIn educational content creator.

Topic: {state['topic']}
Brand voice: {state['brand_voice']}

Lessons learned from previous post performance:
{lessons_context}

Choose one specific, useful angle for a LinkedIn educational post.
Explain why this angle would help the intended learner.

Use the approved lessons to guide your choice when relevant.
Do not force irrelevant lessons into the strategy.
Do not claim that a lesson proves causation.

Return exactly this format:
ANGLE: <chosen angle>
REASON: <reason for choosing it>
"""


    result = ai.generate_text(prompt)

    angle = ""
    reason = ""

    for line in result.splitlines():
        if line.startswith("ANGLE:"):
            angle = line.removeprefix("ANGLE:").strip()
        elif line.startswith("REASON:"):
            reason = line.removeprefix("REASON:").strip()

    if not angle or not reason:
        raise ValueError("Strategist did not return the required format.")

    return {
        "strategist_angle": angle,
        "strategy_reason": reason,
        "audit_trail": state["audit_trail"] + [
            f"Strategist selected angle: {angle}",
            f"Strategist rationale: {reason}",
            f"Strategist considered {len(approved_lessons)} approved learning lessons.",
        ],
    }
