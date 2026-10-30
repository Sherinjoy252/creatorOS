from graph.state import CreatorState
from services.ai_service import AIService


def _build_revision_context(state: CreatorState) -> str:
    initial_evaluation = state.get("initial_evaluation") or {}
    priorities = state.get("revision_priorities", [])

    if not initial_evaluation and not priorities:
        return "No initial self-evaluation priorities are available."

    lines = []
    if initial_evaluation.get("score") is not None:
        lines.append(f"Initial draft score: {initial_evaluation['score']}/100")

    if priorities:
        lines.append("Priorities identified by the initial evaluator:")
        lines.extend(f"- {priority}" for priority in priorities)

    criteria = initial_evaluation.get("criteria", {})
    strong = []
    for key, item in criteria.items():
        max_score = item.get("max_score", 0)
        score = item.get("score", 0)
        if max_score and score / max_score >= 0.9:
            strong.append(key)

    if strong:
        lines.append(
            "Preserve these already-strong areas unless a factual or editorial issue requires a change: "
            + ", ".join(strong)
        )

    return "\n".join(lines)


def writer_node(state: CreatorState) -> dict:
    ai = AIService()

    approved_lessons = state.get("approved_lessons", [])

    lessons_context = (
        "\n".join(f"- {lesson}" for lesson in approved_lessons)
        if approved_lessons
        else "No approved performance lessons are available yet."
    )

    revision_context = _build_revision_context(state)

    common_instructions = f"""
Create an educational LinkedIn post about: {state['topic']}

Chosen angle: {state['strategist_angle']}
Strategic rationale: {state['strategy_reason']}

Brand voice profile:
{state['brand_voice']}

Lessons learned from previous post performance:
{lessons_context}

Use relevant approved lessons to improve the post's structure,
clarity, examples, and engagement potential.

Apply these lessons naturally. Do not force irrelevant advice
into the post or claim that engagement improvements are guaranteed.

Requirements:
- Follow the supplied brand voice instead of generic AI writing habits.
- Explain the topic accurately and use a practical example when useful.
- Prefer 150-300 words unless the topic needs more detail.
- Use clear paragraphs and purposeful Markdown.
- Avoid repetitive explanations, duplicate conclusions, and filler.
- Avoid excessive emojis, clickbait, and generic motivational phrases.
- End with one clear conclusion.
- Return only the LinkedIn post, without commentary about your task.
"""

    if state["critique"]:
        task = f"""
Revise the previous post using the editor's feedback.

Treat each specific correction as a requirement unless it conflicts
with technical accuracy.

Editor feedback:
{state['critique']}

Initial self-evaluation and revision priorities:
{revision_context}

Previous draft:
{state['draft']}

{common_instructions}

Revision requirements:
- Address the valid initial-evaluation priorities, not just the latest editor comments.
- Preserve correct information, useful examples, and sections that already work well.
- Do not make unrelated changes merely to increase a numerical score.
- Make meaningful improvements rather than merely changing a few words.
- Ensure all code examples are technically correct and demonstrate
  what the explanation claims. Prefer try-with-resources for Java
  resource management when appropriate.
- Avoid repetitive headings, multiple conclusions, excessive emojis,
  and repeated calls to action.
- Ensure the content and examples directly address the requested topic.
"""
    else:
        task = common_instructions

    draft = ai.generate_text(task).strip()

    if not draft:
        raise ValueError("Writer returned an empty draft.")

    revision_count = state["revision_count"] + (
        1 if state["critique"] else 0
    )

    action = (
        "revised the draft"
        if state["critique"]
        else "created initial draft"
    )

    return {
        "draft": draft,
        "revision_count": revision_count,
        "audit_trail": state["audit_trail"] + [
            f"Writer {action} ({len(draft)} characters).",
            f"Writer considered {len(approved_lessons)} approved learning lessons.",
            (
                f"Writer considered {len(state.get('revision_priorities', []))} "
                "initial-evaluation revision priorities."
            ),
        ],
    }
