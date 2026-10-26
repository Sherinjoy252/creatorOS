
from graph.state import CreatorState
from services.ai_service import AIService


def strategist_node(state: CreatorState) -> dict:
    ai = AIService()

    prompt = f"""
You are the content strategist for a LinkedIn educational content creator.

Topic: {state['topic']}
Brand voice: {state['brand_voice']}

Choose one specific, useful angle for a LinkedIn educational post.
Explain why this angle would help the intended learner.

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
        ],
    }
